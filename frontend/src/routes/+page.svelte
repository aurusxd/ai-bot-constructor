<script lang="ts">
	import { onMount } from 'svelte';

	import { deleteAssistant, listAssistants } from '$lib/api';
	import type { Assistant } from '$lib/types';

	let assistants = $state<Assistant[]>([]);
	let loading = $state(true);
	let error = $state('');

	onMount(load);

	async function load() {
		loading = true;
		error = '';
		try {
			assistants = await listAssistants();
		} catch (exc) {
			error = exc instanceof Error ? exc.message : String(exc);
		} finally {
			loading = false;
		}
	}

	async function remove(assistant: Assistant) {
		if (!confirm(`Удалить ассистента «${assistant.name}»?`)) return;
		try {
			await deleteAssistant(assistant.id);
			assistants = assistants.filter((item) => item.id !== assistant.id);
		} catch (exc) {
			error = exc instanceof Error ? exc.message : String(exc);
		}
	}
</script>

<header>
	<h1>Ассистенты</h1>
	<a class="button" href="/assistants/new">Создать ассистента</a>
</header>

{#if error}
	<p class="error">{error}</p>
{/if}

{#if loading}
	<p>Загрузка…</p>
{:else if assistants.length === 0}
	<p>Пока ни одного ассистента.</p>
{:else}
	<table>
		<thead>
			<tr>
				<th>Имя</th>
				<th>Должность</th>
				<th>Статус</th>
				<th></th>
			</tr>
		</thead>
		<tbody>
			{#each assistants as assistant (assistant.id)}
				<tr>
					<td>{assistant.name}</td>
					<td>{assistant.position}</td>
					<td>
						<span class="status" class:active={assistant.webhook_active}>
							{assistant.webhook_active ? 'Активен' : 'Не активен'}
						</span>
					</td>
					<td class="actions">
						<a href="/assistants/{assistant.id}">Редактировать</a>
						<button type="button" onclick={() => remove(assistant)}>Удалить</button>
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
{/if}

<style>
	header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		gap: 1rem;
	}

	table {
		width: 100%;
		border-collapse: collapse;
	}

	th,
	td {
		text-align: left;
		padding: 0.6rem 0.5rem;
		border-bottom: 1px solid #e3e6ea;
	}

	.status {
		color: #6b7280;
	}

	.status.active {
		color: #1a7f37;
		font-weight: 600;
	}

	.actions {
		display: flex;
		gap: 0.75rem;
	}
</style>
