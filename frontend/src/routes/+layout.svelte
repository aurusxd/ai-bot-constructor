<script lang="ts">
	let { children } = $props();
</script>

<main>
	{@render children()}
</main>

<style>
	:global(body) {
		margin: 0;
		font-family: system-ui, -apple-system, 'Segoe UI', sans-serif;
		color: #1f2328;
		background: #f6f7f9;
	}

	:global(button),
	:global(.button) {
		font: inherit;
		padding: 0.5rem 0.9rem;
		border: 1px solid #c6ccd4;
		border-radius: 4px;
		background: #fff;
		text-decoration: none;
		color: inherit;
		cursor: pointer;
	}

	:global(button:disabled) {
		opacity: 0.6;
		cursor: default;
	}

	:global(.error) {
		color: #b42318;
	}

	:global(.notice) {
		color: #1a7f37;
	}

	main {
		max-width: 60rem;
		margin: 0 auto;
		padding: 2rem 1.5rem 4rem;
	}
</style>
