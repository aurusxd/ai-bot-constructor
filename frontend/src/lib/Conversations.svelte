<script lang="ts">
	import { onMount } from 'svelte';

	import { listConversations, listMessages } from './api';
	import type { Conversation, Message } from './types';

	interface Props {
		assistantId: number;
	}

	let { assistantId }: Props = $props();

	let conversations = $state<Conversation[]>([]);
	let messages = $state<Message[]>([]);
	let selected = $state<string | null>(null);
	let loading = $state(true);
	let error = $state('');

	onMount(async () => {
		try {
			conversations = await listConversations(assistantId);
		} catch (exc) {
			error = exc instanceof Error ? exc.message : String(exc);
		} finally {
			loading = false;
		}
	});

	async function open(chatId: string) {
		selected = chatId;
		messages = [];
		error = '';
		try {
			messages = await listMessages(assistantId, chatId);
		} catch (exc) {
			error = exc instanceof Error ? exc.message : String(exc);
		}
	}

	function formatTime(value: string) {
		return new Date(value).toLocaleString('ru-RU');
	}
</script>

<section>
	<h2>Диалоги</h2>

	{#if error}
		<p class="error">{error}</p>
	{/if}

	{#if loading}
		<p>Загрузка…</p>
	{:else if conversations.length === 0}
		<p>Диалогов пока нет.</p>
	{:else}
		<ul class="chats">
			{#each conversations as conversation (conversation.id)}
				<li>
					<button
						type="button"
						class:selected={selected === conversation.telegram_chat_id}
						onclick={() => open(conversation.telegram_chat_id)}
					>
						Чат {conversation.telegram_chat_id}
						<small>{formatTime(conversation.created_at)}</small>
					</button>
				</li>
			{/each}
		</ul>

		{#if selected}
			<ol class="messages">
				{#each messages as message (message.id)}
					<li class={message.role}>
						<span class="who">{message.role === 'user' ? 'Клиент' : 'Ассистент'}</span>
						<span class="text">{message.content}</span>
					</li>
				{/each}
			</ol>
		{/if}
	{/if}
</section>

<style>
	section {
		margin: 2rem 0;
	}

	.chats {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		list-style: none;
		padding: 0;
	}

	.chats button {
		display: flex;
		flex-direction: column;
		align-items: flex-start;
		gap: 0.15rem;
	}

	.chats button.selected {
		border-color: #1f2328;
	}

	small {
		color: #6b7280;
	}

	.messages {
		list-style: none;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		max-width: 40rem;
	}

	.messages li {
		display: flex;
		flex-direction: column;
		gap: 0.2rem;
		padding: 0.6rem 0.8rem;
		border-radius: 6px;
		background: #fff;
		border: 1px solid #e3e6ea;
	}

	.messages li.assistant {
		background: #f0f6ff;
	}

	.who {
		font-size: 0.8rem;
		font-weight: 600;
		color: #6b7280;
	}

	.text {
		white-space: pre-wrap;
	}
</style>
