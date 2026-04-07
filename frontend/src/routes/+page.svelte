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
	 * @typedef {{ name: string, type: string, nullable: boolean, isPrimaryKey: boolean }} ColumnMetadata
	 * @typedef {{ name: string, columns: ColumnMetadata[], primaryKey: string[] }} TableMetadata
	 * @typedef {{ fromColumn: string, toColumn: string }} ColumnMapping
	 * @typedef {{ name: string, fromTable: string, toTable: string, columnMapping: ColumnMapping[] }} ForeignKeyMetadata
	 * @typedef {{ database: string, tables: TableMetadata[], foreignKeys: ForeignKeyMetadata[] }} SchemaMetadata
	 */

	let userId = '';
	/** @type {SchemaMetadata | null} */
	let schema = null;
	let loading = false;
	let error = '';

	const features = [
		'Inspect each user\'s practice database schema through the metadata API.',
		'Reflect added attributes by reading the current schema dynamically.',
		'Use this metadata as the source for a future schema diagram view.'
	];

	async function loadSchemaMetadata() {
		loading = true;
		error = '';

		const query = userId.trim() ? `?user_id=${encodeURIComponent(userId.trim())}` : '';

		try {
			const response = await fetch(`${backendBaseUrl}/api/schema-metadata${query}`);
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

	onMount(loadSchemaMetadata);
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

	<section class="card">
		<h2>Next steps</h2>
		<ul>
			{#each features as feature}
				<li>{feature}</li>
			{/each}
		</ul>
		<code>frontend: npm run dev / backend: uvicorn backend.app:app --reload</code>
	</section>

	<section class="card controls">
		<div class="controls-header">
			<div>
				<h2>Schema Metadata</h2>
				<p>Load the current relational schema for a user's practice database.</p>
			</div>
			<button on:click={loadSchemaMetadata} disabled={loading}>
				{#if loading}Loading...{:else}Refresh{/if}
			</button>
		</div>

		<div class="form-row">
			<label for="user-id">User ID</label>
			<input
				id="user-id"
				bind:value={userId}
				placeholder="Leave empty for the default practice DB"
			/>
		</div>

		{#if error}
			<p class="error">{error}</p>
		{/if}

		{#if schema}
			<div class="meta-summary">
				<div>
					<span class="summary-label">Database</span>
					<strong>{schema.database}</strong>
				</div>
				<div>
					<span class="summary-label">Tables</span>
					<strong>{schema.tables.length}</strong>
				</div>
				<div>
					<span class="summary-label">Foreign Keys</span>
					<strong>{schema.foreignKeys.length}</strong>
				</div>
			</div>

			<div class="table-grid">
				{#each schema.tables as table}
					<article class="table-card">
						<header>
							<h3>{table.name}</h3>
							{#if table.primaryKey.length}
								<span>PK: {table.primaryKey.join(', ')}</span>
							{/if}
						</header>

						<ul class="column-list">
							{#each table.columns as column}
								<li>
									<div>
										<strong>{column.name}</strong>
										{#if column.isPrimaryKey}
											<span class="pk-badge">PK</span>
										{/if}
									</div>
									<small>{column.type}{column.nullable ? '' : ' NOT NULL'}</small>
								</li>
							{/each}
						</ul>
					</article>
				{/each}
			</div>

			{#if schema.foreignKeys.length}
				<div class="relations">
					<h3>Relationships</h3>
					<ul>
						{#each schema.foreignKeys as relation}
							<li>
								<strong>{relation.fromTable}</strong>
								<span>
									{relation.columnMapping.map(({ fromColumn, toColumn }) => `${fromColumn} -> ${toColumn}`).join(', ')}
								</span>
								<strong>{relation.toTable}</strong>
							</li>
						{/each}
					</ul>
				</div>
			{/if}
		{/if}
	</section>
</div>

<style>
	.page {
		display: grid;
		gap: 1.5rem;
		max-width: 900px;
		margin: 0 auto;
		padding: 4rem 1.5rem 5rem;
	}

	.hero {
		padding: 2rem 0 0.5rem;
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
		max-width: 40rem;
		font-size: 1.1rem;
		line-height: 1.6;
		color: #314861;
	}

	.card {
		padding: 1.5rem;
		border: 1px solid rgba(19, 34, 56, 0.08);
		border-radius: 24px;
		background: rgba(255, 255, 255, 0.78);
		backdrop-filter: blur(12px);
		box-shadow: 0 24px 60px rgba(44, 76, 117, 0.12);
	}

	h2 {
		margin-top: 0;
	}

	h3 {
		margin: 0;
	}

	ul {
		padding-left: 1.2rem;
		line-height: 1.8;
		color: #314861;
	}

	code {
		display: inline-block;
		margin-top: 0.5rem;
		padding: 0.7rem 0.9rem;
		border-radius: 12px;
		background: #132238;
		color: #f5f9ff;
		font-size: 0.95rem;
	}

	.controls {
		display: grid;
		gap: 1.25rem;
	}

	.controls-header {
		display: flex;
		gap: 1rem;
		align-items: flex-start;
		justify-content: space-between;
	}

	.controls-header p {
		margin: 0.35rem 0 0;
		color: #4a5f77;
	}

	.form-row {
		display: grid;
		gap: 0.45rem;
	}

	label {
		font-size: 0.92rem;
		font-weight: 700;
	}

	input {
		width: 100%;
		padding: 0.85rem 1rem;
		border: 1px solid rgba(19, 34, 56, 0.14);
		border-radius: 14px;
		font: inherit;
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

	.error {
		margin: 0;
		padding: 0.9rem 1rem;
		border-radius: 14px;
		background: rgba(179, 34, 34, 0.1);
		color: #8b1f1f;
	}

	.meta-summary {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
		gap: 0.9rem;
	}

	.meta-summary > div {
		padding: 1rem;
		border-radius: 16px;
		background: rgba(216, 230, 247, 0.65);
	}

	.summary-label {
		display: block;
		margin-bottom: 0.35rem;
		font-size: 0.82rem;
		font-weight: 700;
		letter-spacing: 0.08em;
		text-transform: uppercase;
		color: #4a5f77;
	}

	.table-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
		gap: 1rem;
	}

	.table-card {
		border: 1px solid rgba(19, 34, 56, 0.1);
		border-radius: 18px;
		overflow: hidden;
		background: rgba(255, 255, 255, 0.86);
	}

	.table-card header {
		display: flex;
		gap: 0.8rem;
		align-items: center;
		justify-content: space-between;
		padding: 0.95rem 1rem;
		background: rgba(168, 204, 227, 0.75);
	}

	.table-card header span {
		font-size: 0.8rem;
		font-weight: 700;
		color: #274760;
	}

	.column-list {
		list-style: none;
		margin: 0;
		padding: 0.8rem 1rem 1rem;
	}

	.column-list li {
		display: flex;
		gap: 0.75rem;
		align-items: baseline;
		justify-content: space-between;
		padding: 0.45rem 0;
		border-bottom: 1px solid rgba(19, 34, 56, 0.06);
	}

	.column-list li:last-child {
		border-bottom: 0;
	}

	.column-list strong {
		margin-right: 0.45rem;
	}

	.column-list small {
		color: #4a5f77;
		text-align: right;
	}

	.pk-badge {
		display: inline-block;
		padding: 0.15rem 0.45rem;
		border-radius: 999px;
		background: #132238;
		color: #f5f9ff;
		font-size: 0.72rem;
		font-weight: 700;
	}

	.relations {
		padding-top: 0.25rem;
	}

	.relations ul {
		padding-left: 1.1rem;
	}

	.relations li {
		display: grid;
		gap: 0.2rem;
		margin-bottom: 0.6rem;
	}

	@media (max-width: 640px) {
		.controls-header {
			flex-direction: column;
		}

		.column-list li {
			align-items: flex-start;
			flex-direction: column;
		}
	}
</style>
