<svelte:head>
	<title>MySQL Interpreter</title>
	<meta
		name="description"
		content="Frontend shell for the MySQL interpreter project built with SvelteKit."
	/>
</svelte:head>

<script>
	import { onMount } from 'svelte';

	const backendBaseUrl = (import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:8000').replace(/\/$/, '');

	/**
	 * @typedef {{ name: string, type: string, nullable: boolean, isPrimaryKey: boolean, isForeignKey: boolean }} ColumnMetadata
	 * @typedef {{ name: string, columns: ColumnMetadata[], primaryKey: string[] }} TableMetadata
	 * @typedef {{ fromColumn: string, toColumn: string }} ColumnMapping
	 * @typedef {{ name: string, fromTable: string, toTable: string, columnMapping: ColumnMapping[] }} ForeignKeyMetadata
	 * @typedef {{ database: string, tables: TableMetadata[], foreignKeys: ForeignKeyMetadata[] }} SchemaMetadata
	 * @typedef {{ table: TableMetadata, x: number, y: number, width: number, height: number }} DiagramTable
	 * @typedef {{ path: string }} DiagramLine
	 * @typedef {{ kind: 'statement', message: string, affectedRows: number, note?: string, rewrittenQuery?: string }} StatementResult
	 * @typedef {{ kind: 'result_set', columns: string[], rows: Record<string, unknown>[], rowCount: number, note?: string, rewrittenQuery?: string }} ResultSetResult
	 * @typedef {StatementResult | ResultSetResult} QueryResult
	 */

	const TABLE_WIDTH = 270;
	const HEADER_HEIGHT = 54;
	const ROW_HEIGHT = 34;
	const TABLE_BODY_TOP = HEADER_HEIGHT + 18;
	const LINE_Y_OFFSET = -12;
	const TABLE_GAP_X = 116;
	const TABLE_GAP_Y = 34;
	const DIAGRAM_PADDING = 32;
	const DIAGRAM_COLUMNS = 3;
	const HEARTBEAT_INTERVAL_MS = 30000;

	let databaseName = '';
	let sessionTtlSeconds = 0;
	/** @type {SchemaMetadata | null} */
	let schema = null;
	let queryText = '';
	/** @type {QueryResult | null} */
	let queryResult = null;
	let queryLoading = false;
	let queryError = '';
	let loading = false;
	let error = '';
	/** @type {number | null} */
	let heartbeatTimer;

	async function ensureSession() {
		const response = await fetch(`${backendBaseUrl}/api/session`, { method: 'POST' });
		const payload = await response.json();

		if (!response.ok) {
			throw new Error(payload.detail || 'Failed to initialize practice database session.');
		}

		databaseName = payload.database;
		sessionTtlSeconds = payload.ttlSeconds;
	}

	async function heartbeatSession() {
		try {
			const response = await fetch(`${backendBaseUrl}/api/session/heartbeat`, { method: 'POST' });
			const payload = await response.json();

			if (!response.ok) {
				throw new Error(payload.detail || 'Failed to renew practice database session.');
			}

			databaseName = payload.database;
			sessionTtlSeconds = payload.ttlSeconds;
		} catch {
			// Keep UI responsive; the next explicit action will surface errors.
		}
	}

	function releaseSession() {
		fetch(`${backendBaseUrl}/api/session/release`, {
			method: 'POST',
			keepalive: true
		}).catch(() => {});
	}

	async function loadSchemaMetadata() {
		loading = true;
		error = '';

		try {
			const response = await fetch(`${backendBaseUrl}/api/schema-metadata`);
			/** @type {SchemaMetadata | { detail?: string }} */
			const payload = await response.json();

			if (!response.ok) {
				const detail = 'detail' in payload ? payload.detail : undefined;
				throw new Error(detail || 'Failed to load schema metadata.');
			}

			schema = /** @type {SchemaMetadata} */ (payload);
		} catch (err) {
			schema = null;
			error = err instanceof Error ? err.message : 'Failed to load schema metadata.';
		} finally {
			loading = false;
		}
	}

	async function executeQuery() {
		queryLoading = true;
		queryError = '';
		queryResult = null;

		try {
			const response = await fetch(`${backendBaseUrl}/api/query`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					query: queryText
				})
			});

			const payload = await response.json();

			if (!response.ok) {
				throw new Error(payload.detail || 'Failed to execute query.');
			}

			queryResult = /** @type {QueryResult} */ (payload);
			await loadSchemaMetadata();
		} catch (err) {
			queryError = err instanceof Error ? err.message : 'Failed to execute query.';
		} finally {
			queryLoading = false;
		}
	}

	/**
	 * @param {TableMetadata[]} tables
	 * @returns {DiagramTable[]}
	 */
	function buildDiagramTables(tables) {
		return tables.map((table, index) => {
			const column = index % DIAGRAM_COLUMNS;
			const row = Math.floor(index / DIAGRAM_COLUMNS);
			const height = HEADER_HEIGHT + Math.max(table.columns.length, 1) * ROW_HEIGHT + 22;

			return {
				table,
				x: DIAGRAM_PADDING + column * (TABLE_WIDTH + TABLE_GAP_X),
				y: DIAGRAM_PADDING + row * (height + TABLE_GAP_Y),
				width: TABLE_WIDTH,
				height
			};
		});
	}

	/**
	 * @param {DiagramTable[]} tables
	 * @param {ForeignKeyMetadata[]} foreignKeys
	 * @returns {DiagramLine[]}
	 */
	function buildDiagramLines(tables, foreignKeys) {
		/** @type {Map<string, DiagramTable>} */
		const tableMap = new Map(tables.map((entry) => [entry.table.name, entry]));
		/** @type {DiagramLine[]} */
		const lines = [];

		for (const relation of foreignKeys) {
			const from = tableMap.get(relation.fromTable);
			const to = tableMap.get(relation.toTable);

			if (!from || !to) {
				continue;
			}

			for (const [index, mapping] of relation.columnMapping.entries()) {
				const fromIndex = from.table.columns.findIndex((column) => column.name === mapping.fromColumn);
				const toIndex = to.table.columns.findIndex((column) => column.name === mapping.toColumn);

				if (fromIndex === -1 || toIndex === -1) {
					continue;
				}

				const fromCenterX = from.x + from.width / 2;
				const toCenterX = to.x + to.width / 2;
				const fromOnLeft = fromCenterX < toCenterX;
				const startX = fromOnLeft ? from.x + from.width : from.x;
				const endX = fromOnLeft ? to.x : to.x + to.width;
				const startY = from.y + TABLE_BODY_TOP + fromIndex * ROW_HEIGHT + ROW_HEIGHT / 2 + LINE_Y_OFFSET;
				const endY = to.y + TABLE_BODY_TOP + toIndex * ROW_HEIGHT + ROW_HEIGHT / 2 + LINE_Y_OFFSET;
				const spread = 42 + index * 18;
				const middleX = fromOnLeft
					? Math.min(startX + spread, endX - 28)
					: Math.max(startX - spread, endX + 28);
				lines.push({
					path: `M ${startX} ${startY} L ${middleX} ${startY} L ${middleX} ${endY} L ${endX} ${endY}`
				});
			}
		}

		return lines;
	}

	/** @returns {number} */
	function getDiagramWidth() {
		if (!schema?.tables.length) {
			return TABLE_WIDTH + DIAGRAM_PADDING * 2;
		}

		const columnCount = Math.min(schema.tables.length, DIAGRAM_COLUMNS);
		return DIAGRAM_PADDING * 2 + columnCount * TABLE_WIDTH + Math.max(columnCount - 1, 0) * TABLE_GAP_X;
	}

	/**
	 * @param {DiagramTable[]} tables
	 * @returns {number}
	 */
	function getDiagramHeight(tables) {
		if (!tables.length) {
			return 260;
		}

		return Math.max(...tables.map((table) => table.y + table.height)) + DIAGRAM_PADDING;
	}

	onMount(() => {
		let disposed = false;

		(async () => {
			try {
				await ensureSession();
				if (!disposed) {
					await loadSchemaMetadata();
					heartbeatTimer = window.setInterval(heartbeatSession, HEARTBEAT_INTERVAL_MS);
				}
			} catch (err) {
				error = err instanceof Error ? err.message : 'Failed to initialize practice database session.';
			}
		})();

		window.addEventListener('beforeunload', releaseSession);

		return () => {
			disposed = true;
			if (heartbeatTimer) {
				window.clearInterval(heartbeatTimer);
			}
			window.removeEventListener('beforeunload', releaseSession);
			releaseSession();
		};
	});

	/** @type {DiagramTable[]} */
	$: diagramTables = schema ? buildDiagramTables(schema.tables) : [];
	/** @type {DiagramLine[]} */
	$: diagramLines = schema ? buildDiagramLines(diagramTables, schema.foreignKeys) : [];
	$: diagramWidth = getDiagramWidth();
	$: diagramHeight = getDiagramHeight(diagramTables);
</script>

<div class="page">
	<section class="hero">
		<p class="eyebrow">CSE4110 : Database Systems</p>
		<h1>MySQL Interpreter</h1>
		<p class="intro">
			This online SQL interpreter was built for Sogang University's CSE4110 Database Systems
			course, giving students a dedicated space to practice SQL queries while addressing
			limitations in existing interpreters that could not reliably support operations such as
			intersection.
		</p>
	</section>

	<section class="card controls">
		<div class="controls-header">
			<div>
				<h2>Schema Diagram</h2>
				<p>Render the current relational schema for this IP-scoped practice database.</p>
			</div>
			<button on:click={loadSchemaMetadata} disabled={loading}>
				{#if loading}Loading...{:else}Refresh{/if}
			</button>
		</div>

		{#if error}
			<p class="error">{error}</p>
		{/if}

		{#if schema}
			<div class="diagram-meta">
				<span><strong>Database:</strong> {databaseName || schema.database}</span>
				<span><strong>Tables:</strong> {schema.tables.length}</span>
				<span><strong>Foreign Keys:</strong> {schema.foreignKeys.length}</span>
				<span><strong>TTL:</strong> {sessionTtlSeconds}s</span>
			</div>

			<div class="diagram-shell">
				<div class="diagram-canvas" style={`width: ${diagramWidth}px; height: ${diagramHeight}px;`}>
					<svg class="diagram-lines" viewBox={`0 0 ${diagramWidth} ${diagramHeight}`} aria-hidden="true">
						<defs>
							<marker
								id="arrowhead"
								markerWidth="12"
								markerHeight="8"
								refX="10"
								refY="4"
								orient="auto"
								markerUnits="strokeWidth"
							>
								<path d="M 0 0 L 12 4 L 0 8 z" fill="#314861" />
							</marker>
						</defs>

						{#each diagramLines as line}
							<path
								d={line.path}
								fill="none"
								stroke="#314861"
								stroke-width="2.25"
								stroke-linejoin="round"
								marker-end="url(#arrowhead)"
							/>
						{/each}
					</svg>

					{#each diagramTables as entry}
						<article
							class="schema-table"
							style={`left: ${entry.x}px; top: ${entry.y}px; width: ${entry.width}px; min-height: ${entry.height}px;`}
						>
							<header>
								<h3>{entry.table.name}</h3>
							</header>

							<ul>
								{#each entry.table.columns as column}
									<li>
										<div class="column-name">
											<span class:is-key={column.isPrimaryKey}>{column.name}</span>
											{#if column.isForeignKey}
												<span class="fk-chip">FK</span>
											{/if}
										</div>
										<small>{column.type}</small>
									</li>
								{/each}
							</ul>
						</article>
					{/each}
				</div>
			</div>

			{#if !schema.tables.length}
				<p class="empty-state">No tables were found in this practice database.</p>
			{/if}
		{/if}
	</section>

	<section class="card query-panel">
		<div class="panel-header">
			<div>
				<h2>Query</h2>
				<p>Run SQL against the current practice database.</p>
			</div>
		</div>

		<div class="form-row">
			<label for="query-input">Query</label>
			<textarea
				id="query-input"
				bind:value={queryText}
				rows="7"
				placeholder="Try CREATE, SELECT, SHOW, or other SQL statements here."
			></textarea>
			<div class="query-actions">
				<button class="secondary" on:click={executeQuery} disabled={queryLoading || !queryText.trim()}>
					{#if queryLoading}Running...{:else}Run Query{/if}
				</button>
			</div>
		</div>

		{#if queryError}
			<p class="error">{queryError}</p>
		{/if}

		{#if queryResult}
			<div class="query-result">
				<h3>Query Result</h3>

				{#if queryResult.note}
					<p class="note">{queryResult.note}</p>
				{/if}

				{#if queryResult.rewrittenQuery}
					<pre>{queryResult.rewrittenQuery}</pre>
				{/if}

				{#if queryResult.kind === 'statement'}
					<p>{queryResult.message} Affected rows: {queryResult.affectedRows}</p>
				{:else}
					<p>Returned rows: {queryResult.rowCount}</p>
					<div class="result-table-wrap">
						<table class="result-table">
							<thead>
								<tr>
									{#each queryResult.columns as column}
										<th>{column}</th>
									{/each}
								</tr>
							</thead>
							<tbody>
								{#each queryResult.rows as row}
									<tr>
										{#each queryResult.columns as column}
											<td>{row[column]}</td>
										{/each}
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</div>
		{/if}
	</section>
</div>

<style>
	:global(body) {
		color: #132238;
	}

	.page {
		display: grid;
		gap: 0.8rem;
		max-width: 1320px;
		margin: 0 auto;
		padding: 4rem 1.5rem 5rem;
	}

	.hero {
		padding: 2rem 0 0;
	}

	.eyebrow {
		margin: 0 0 0.75rem;
		font-size: 0.85rem;
		font-weight: 700;
		letter-spacing: 0.14em;
		text-transform: uppercase;
		color: #245b91;
	}

	h1 {
		margin: 0;
		font-size: clamp(2.5rem, 7vw, 4.5rem);
		line-height: 0.95;
	}

	.intro {
		max-width: 58rem;
		font-size: 1.1rem;
		line-height: 1.6;
		color: #314861;
	}

	.card {
		padding: 1.1rem;
		border: 1px solid rgba(19, 34, 56, 0.08);
		border-radius: 24px;
		background: rgba(255, 255, 255, 0.78);
		backdrop-filter: blur(12px);
		box-shadow: 0 24px 60px rgba(44, 76, 117, 0.12);
	}

	.controls {
		display: grid;
		gap: 0.7rem;
	}

	.query-panel {
		display: grid;
		gap: 0.7rem;
	}

	.controls-header {
		display: flex;
		gap: 1rem;
		align-items: flex-start;
		justify-content: space-between;
	}

	.panel-header p {
		margin: 0.35rem 0 0;
		color: #4a5f77;
	}

	h2,
	h3 {
		margin: 0;
	}

	.controls-header p {
		margin: 0.2rem 0 0;
		color: #4a5f77;
	}

	.form-row {
		display: grid;
		gap: 0.3rem;
	}

	label {
		font-size: 0.92rem;
		font-weight: 700;
	}

	textarea {
		width: 100%;
		padding: 0.95rem 1rem;
		border: 1px solid rgba(19, 34, 56, 0.14);
		border-radius: 14px;
		font: inherit;
		line-height: 1.5;
		resize: vertical;
		background: rgba(255, 255, 255, 0.92);
	}

	button {
		padding: 0.8rem 1rem;
		border: 0;
		border-radius: 14px;
		background: #245b91;
		color: #fff;
		font: inherit;
		font-weight: 700;
		cursor: pointer;
	}

	button:disabled {
		opacity: 0.7;
		cursor: wait;
	}

	.secondary {
		background: #132238;
	}

	.query-actions {
		display: flex;
		justify-content: flex-end;
	}

	.error {
		margin: 0;
		padding: 0.9rem 1rem;
		border-radius: 14px;
		background: rgba(179, 34, 34, 0.1);
		color: #8b1f1f;
	}

	.query-result {
		display: grid;
		gap: 0.55rem;
		padding: 0.85rem 1rem;
		border-radius: 18px;
		background: rgba(236, 243, 252, 0.8);
	}

	.note {
		margin: 0;
		color: #245b91;
		font-weight: 700;
	}

	pre {
		margin: 0;
		padding: 0.9rem 1rem;
		border-radius: 14px;
		overflow-x: auto;
		background: #132238;
		color: #f5f9ff;
		font-size: 0.9rem;
	}

	.result-table-wrap {
		overflow-x: auto;
	}

	.result-table {
		width: 100%;
		border-collapse: collapse;
		font-size: 0.92rem;
	}

	.result-table th,
	.result-table td {
		padding: 0.7rem 0.8rem;
		border-bottom: 1px solid rgba(19, 34, 56, 0.1);
		text-align: left;
		vertical-align: top;
	}

	.result-table th {
		color: #314861;
	}

	.diagram-meta {
		display: flex;
		flex-wrap: wrap;
		gap: 0.55rem 1.4rem;
		color: #4a5f77;
		font-size: 0.95rem;
	}

	.diagram-shell {
		overflow-x: auto;
		padding-bottom: 0.15rem;
		background: transparent;
	}

	.diagram-canvas {
		position: relative;
		border-radius: 0;
		background: transparent;
		box-shadow: none;
	}

	.diagram-lines {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		overflow: visible;
	}

	.schema-table {
		position: absolute;
		border: 2px solid #2f3a45;
		background: rgba(255, 255, 255, 0.98);
		box-shadow: 0 12px 24px rgba(49, 72, 97, 0.08);
	}

	.schema-table header {
		padding: 0.8rem 1rem;
		border-bottom: 2px solid #2f3a45;
		background: #b8d7e8;
	}

	.schema-table h3 {
		font-size: 1.1rem;
		font-style: italic;
		font-weight: 600;
		text-align: center;
	}

	.schema-table ul {
		list-style: none;
		margin: 0;
		padding: 0.55rem 0;
	}

	.schema-table li {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: 1rem;
		padding: 0.32rem 1rem;
		font-size: 1rem;
	}

	.column-name {
		display: flex;
		gap: 0.45rem;
		align-items: center;
		font-style: italic;
	}

	.is-key {
		text-decoration: underline;
		text-decoration-thickness: 1.5px;
		text-underline-offset: 3px;
	}

	.fk-chip {
		display: inline-flex;
		align-items: center;
		justify-content: center;
		min-width: 28px;
		height: 22px;
		padding: 0 0.45rem;
		border-radius: 999px;
		background: #245b91;
		color: #fff;
		font-size: 0.72rem;
		font-style: normal;
		font-weight: 700;
	}

	small {
		color: #566d86;
		font-size: 0.82rem;
	}

	.empty-state {
		margin: 0;
		color: #526a84;
	}

	@media (max-width: 900px) {
		.page {
			padding-left: 1rem;
			padding-right: 1rem;
		}

		.controls-header {
			flex-direction: column;
		}
	}
</style>
