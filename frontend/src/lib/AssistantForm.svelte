<script lang="ts">
	import type { AssistantCreate } from './types';

	interface Props {
		values: AssistantCreate;
		submitLabel: string;
		tokenOptional?: boolean;
		saving?: boolean;
		onsubmit: (values: AssistantCreate) => void;
	}

	let {
		values = $bindable(),
		submitLabel,
		tokenOptional = false,
		saving = false,
		onsubmit
	}: Props = $props();

	function handleSubmit(event: SubmitEvent) {
		event.preventDefault();
		onsubmit(values);
	}
</script>

<form onsubmit={handleSubmit}>
	<label>
		Имя сотрудника
		<input bind:value={values.name} required />
	</label>

	<label>
		Должность
		<input bind:value={values.position} required />
	</label>

	<label>
		Язык ответов
		<input bind:value={values.language} required />
	</label>

	<label>
		Тон общения
		<input bind:value={values.tone} required placeholder="дружелюбный, деловой" />
	</label>

	<label>
		Описание бизнеса
		<textarea bind:value={values.business_description} rows="5" required></textarea>
	</label>

	<label>
		Рабочая инструкция
		<textarea bind:value={values.work_instruction} rows="5" required></textarea>
	</label>

	<label>
		Сообщение при отсутствии ответа
		<textarea bind:value={values.fallback_message} rows="2" required></textarea>
	</label>

	<label>
		Telegram chat id админа
		<input bind:value={values.admin_chat_id} required />
	</label>

	<label>
		Токен бота
		<input
			bind:value={values.bot_token}
			required={!tokenOptional}
			placeholder={tokenOptional ? 'Оставьте пустым, чтобы не менять' : ''}
		/>
	</label>

	<button type="submit" disabled={saving}>{saving ? 'Сохранение…' : submitLabel}</button>
</form>

<style>
	form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		max-width: 40rem;
	}

	label {
		display: flex;
		flex-direction: column;
		gap: 0.35rem;
		font-weight: 600;
	}

	input,
	textarea {
		font: inherit;
		font-weight: 400;
		padding: 0.5rem;
		border: 1px solid #c6ccd4;
		border-radius: 4px;
	}

	textarea {
		resize: vertical;
	}

	button {
		align-self: flex-start;
	}
</style>
