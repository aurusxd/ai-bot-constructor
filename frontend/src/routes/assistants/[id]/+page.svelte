<script lang="ts">
	import { onMount } from 'svelte';

	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	import AssistantForm from '$lib/AssistantForm.svelte';
	import Conversations from '$lib/Conversations.svelte';
	import {
		activateAssistant,
		deactivateAssistant,
		deleteAssistant,
		getAssistant,
		getSystemPrompt,
		updateAssistant
	} from '$lib/api';
	import { EMPTY_ASSISTANT, type AssistantCreate } from '$lib/types';

	const id = Number(page.params.id);

	let values = $state<AssistantCreate>({ ...EMPTY_ASSISTANT });
	let webhookActive = $state(false);
	let loading = $state(true);
	let saving = $state(false);
	let switching = $state(false);
	let error = $state('');
	let notice = $state('');
	let promptText = $state('');

	onMount(async () => {
		try {
			const assistant = await getAssistant(id);
			// The API never returns bot_token, so the field stays empty and an
			// empty value tells the backend to keep the stored one.
			values = { ...assistant, bot_token: '' };
			webhookActive = assistant.webhook_active;
		} catch (exc) {
			error = exc instanceof Error ? exc.message : String(exc);
		} finally {
			loading = false;
		}
	});

	function report(exc: unknown) {
		error = exc instanceof Error ? exc.message : String(exc);
	}

	async function save(data: AssistantCreate) {
		saving = true;
		error = '';
		notice = '';
		try {
			await updateAssistant(id, data);
			notice = 'Сохранено';
		} catch (exc) {
			report(exc);
		} finally {
			saving = false;
		}
	}

	async function toggleWebhook() {
		switching = true;
		error = '';
		notice = '';
		try {
			const assistant = webhookActive ? await deactivateAssistant(id) : await activateAssistant(id);
			webhookActive = assistant.webhook_active;
			notice = webhookActive ? 'Бот активирован' : 'Бот отключён';
		} catch (exc) {
			report(exc);
		} finally {
			switching = false;
		}
	}

	async function copyPrompt() {
		error = '';
		notice = '';
		promptText = '';
		let prompt: string;
		try {
			({ prompt } = await getSystemPrompt(id));
		} catch (exc) {
			report(exc);
			return;
		}

		try {
			await navigator.clipboard.writeText(prompt);
			notice = 'System prompt скопирован';
		} catch {
			// The clipboard API needs a secure context, so a panel served over
			// plain http falls back to manual copying.
			promptText = prompt;
			notice = 'Буфер обмена недоступен, скопируйте текст вручную';
		}
	}

	async function remove() {
		if (!confirm(`Удалить ассистента «${values.name}»?`)) return;
		try {
			await deleteAssistant(id);
			await goto('/');
		} catch (exc) {
			report(exc);
		}
	}
</script>

<p><a href="/">← К списку</a></p>
<h1>Ассистент {values.name}</h1>

{#if error}
	<p class="error">{error}</p>
{/if}

{#if notice}
	<p class="notice">{notice}</p>
{/if}

{#if loading}
	<p>Загрузка…</p>
{:else}
	<section class="webhook">
		<p>
			Статус вебхука:
			<strong class:active={webhookActive}>{webhookActive ? 'активен' : 'не активен'}</strong>
		</p>
		<button type="button" onclick={toggleWebhook} disabled={switching}>
			{webhookActive ? 'Отключить бота' : 'Активировать бота'}
		</button>
		<button type="button" onclick={copyPrompt}>Скопировать system prompt</button>
	</section>

	{#if promptText}
		<textarea class="prompt" readonly rows="12">{promptText}</textarea>
	{/if}

	<AssistantForm bind:values submitLabel="Сохранить" tokenOptional {saving} onsubmit={save} />

	<Conversations assistantId={id} />

	<button type="button" class="danger" onclick={remove}>Удалить ассистента</button>
{/if}

<style>
	.webhook {
		display: flex;
		align-items: center;
		gap: 1rem;
		margin-bottom: 1.5rem;
	}

	.webhook p {
		margin: 0;
	}

	strong.active {
		color: #1a7f37;
	}

	.prompt {
		width: 100%;
		max-width: 40rem;
		font: inherit;
		padding: 0.5rem;
		border: 1px solid #c6ccd4;
		border-radius: 4px;
		margin-bottom: 1.5rem;
	}

	.danger {
		margin-top: 2rem;
		color: #b42318;
	}
</style>
