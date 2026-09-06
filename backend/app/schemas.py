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
    bot_token: str


class AssistantOut(AssistantBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    webhook_active: bool
    created_at: datetime
    updated_at: datetime
