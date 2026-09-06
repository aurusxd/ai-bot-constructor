import { env } from '$env/dynamic/public';

import type {
	Assistant,
	AssistantCreate,
	AssistantUpdate,
	Conversation,
	Message
} from './types';

const BASE_URL = env.PUBLIC_API_BASE_URL ?? 'http://localhost:8010';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	const response = await fetch(`${BASE_URL}${path}`, {
		headers: init?.body ? { 'Content-Type': 'application/json' } : undefined,
		...init
	});

	if (!response.ok) {
		throw new Error(await readError(response));
	}

	return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

/** FastAPI reports errors in `detail`, either as a string or as a validation list. */
async function readError(response: Response): Promise<string> {
	try {
		const body = await response.json();
		const detail = body?.detail;
		if (typeof detail === 'string') return detail;
		if (Array.isArray(detail)) return detail.map((item) => item.msg).join(', ');
	} catch {
		// Fall through to the status line below.
	}
	return `Ошибка ${response.status}`;
}

export function listAssistants(): Promise<Assistant[]> {
	return request<Assistant[]>('/api/assistants');
}

export function getAssistant(id: number): Promise<Assistant> {
	return request<Assistant>(`/api/assistants/${id}`);
}

export function createAssistant(data: AssistantCreate): Promise<Assistant> {
	return request<Assistant>('/api/assistants', {
		method: 'POST',
		body: JSON.stringify(data)
	});
}

export function updateAssistant(id: number, data: AssistantUpdate): Promise<Assistant> {
	return request<Assistant>(`/api/assistants/${id}`, {
		method: 'PUT',
		body: JSON.stringify(data)
	});
}

export function deleteAssistant(id: number): Promise<void> {
	return request<void>(`/api/assistants/${id}`, { method: 'DELETE' });
}

export function activateAssistant(id: number): Promise<Assistant> {
	return request<Assistant>(`/api/assistants/${id}/activate`, { method: 'POST' });
}

export function deactivateAssistant(id: number): Promise<Assistant> {
	return request<Assistant>(`/api/assistants/${id}/deactivate`, { method: 'POST' });
}

export function listConversations(id: number): Promise<Conversation[]> {
	return request<Conversation[]>(`/api/assistants/${id}/conversations`);
}

export function listMessages(id: number, chatId: string): Promise<Message[]> {
	return request<Message[]>(
		`/api/assistants/${id}/conversations/${encodeURIComponent(chatId)}/messages`
	);
}

export function getSystemPrompt(id: number): Promise<{ prompt: string }> {
	return request<{ prompt: string }>(`/api/assistants/${id}/system-prompt`);
}
