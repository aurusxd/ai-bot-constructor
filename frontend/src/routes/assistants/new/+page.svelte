<script lang="ts">
	import { goto } from '$app/navigation';

	import AssistantForm from '$lib/AssistantForm.svelte';
	import { createAssistant } from '$lib/api';
	import { EMPTY_ASSISTANT, type AssistantCreate } from '$lib/types';

	let values = $state<AssistantCreate>({ ...EMPTY_ASSISTANT });
	let saving = $state(false);
	let error = $state('');

	async function save(data: AssistantCreate) {
		saving = true;
		error = '';
		try {
			const created = await createAssistant(data);
			await goto(`/assistants/${created.id}`);
		} catch (exc) {
			error = exc instanceof Error ? exc.message : String(exc);
		} finally {
			saving = false;
		}
	}
</script>

<p><a href="/">← К списку</a></p>
<h1>Новый ассистент</h1>

{#if error}
	<p class="error">{error}</p>
{/if}

<AssistantForm bind:values submitLabel="Создать" {saving} onsubmit={save} />
