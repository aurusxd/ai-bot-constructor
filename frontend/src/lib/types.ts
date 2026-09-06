export interface AssistantFields {
	name: string;
	position: string;
	language: string;
	tone: string;
	business_description: string;
	work_instruction: string;
	fallback_message: string;
	admin_chat_id: string;
}

export interface AssistantCreate extends AssistantFields {
	bot_token: string;
}

/** An empty bot_token keeps the token already stored for the assistant. */
export interface AssistantUpdate extends AssistantFields {
	bot_token?: string;
}

export interface Assistant extends AssistantFields {
	id: number;
	webhook_active: boolean;
	created_at: string;
	updated_at: string;
}

export interface Conversation {
	id: number;
	telegram_chat_id: string;
	created_at: string;
}

export interface Message {
	id: number;
	role: 'user' | 'assistant';
	content: string;
	created_at: string;
}

export const EMPTY_ASSISTANT: AssistantCreate = {
	name: '',
	position: '',
	language: 'Русский',
	tone: '',
	business_description: '',
	work_instruction: '',
	fallback_message: '',
	admin_chat_id: '',
	bot_token: ''
};
