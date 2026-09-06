from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AssistantBase(BaseModel):
    name: str
    position: str
    language: str
    tone: str
    business_description: str
    work_instruction: str
    fallback_message: str
    admin_chat_id: str


class AssistantCreate(AssistantBase):
    bot_token: str


class AssistantUpdate(AssistantBase):
    # The panel cannot prefill the stored token, so an empty value keeps it.
    bot_token: str | None = None


class AssistantOut(AssistantBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    webhook_active: bool
    created_at: datetime
    updated_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    telegram_chat_id: str
    created_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    created_at: datetime


class SystemPromptOut(BaseModel):
    prompt: str


class LlmReply(BaseModel):
    """Shape the LLM must return for every client message."""

    reply: str = ""
    needs_human: bool
    reason: str | None = None


class TelegramChat(BaseModel):
    id: int


class TelegramMessage(BaseModel):
    chat: TelegramChat
    text: str | None = None


class TelegramUpdate(BaseModel):
    """Only the parts of a Telegram update this bot reacts to."""

    message: TelegramMessage | None = None
