<svelte:head>
	<title>MySQL Interpreter</title>
	<meta
		name="description"
		content="Frontend shell for the MySQL interpreter project built with SvelteKit."
	/>
</svelte:head>

<script>
	const features = [
		'Build query input and result views here.',
		'Connect this page to the backend API next.',
		'Use SvelteKit routes for future screens.'
	];
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
		<code>npm install && npm run dev</code>
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
</style>
