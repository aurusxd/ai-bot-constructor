from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Assistant, Conversation, Message
from app.schemas import AssistantCreate, AssistantUpdate


def list_assistants(db: Session) -> list[Assistant]:
    return list(db.scalars(select(Assistant).order_by(Assistant.id)))


def get_assistant(db: Session, assistant_id: int) -> Assistant | None:
    return db.get(Assistant, assistant_id)


def create_assistant(db: Session, data: AssistantCreate) -> Assistant:
    assistant = Assistant(**data.model_dump())
    db.add(assistant)
    db.commit()
    db.refresh(assistant)
    return assistant


def update_assistant(db: Session, assistant: Assistant, data: AssistantUpdate) -> Assistant:
    for field, value in data.model_dump().items():
        if field == "bot_token" and not value:
            continue
        setattr(assistant, field, value)
    db.commit()
    db.refresh(assistant)
    return assistant


def delete_assistant(db: Session, assistant: Assistant) -> None:
    db.delete(assistant)
    db.commit()


def get_or_create_conversation(
    db: Session, assistant_id: int, telegram_chat_id: str
) -> Conversation:
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.assistant_id == assistant_id,
            Conversation.telegram_chat_id == telegram_chat_id,
        )
    )
    if conversation is None:
        conversation = Conversation(assistant_id=assistant_id, telegram_chat_id=telegram_chat_id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    return conversation


def add_message(db: Session, conversation_id: int, role: str, content: str) -> Message:
    message = Message(conversation_id=conversation_id, role=role, content=content)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_recent_messages(db: Session, conversation_id: int, limit: int = 10) -> list[Message]:
    """Return the last messages of a conversation in chronological order."""
    recent = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id.desc())
        .limit(limit)
    )
    return list(reversed(list(recent)))


def set_webhook_active(db: Session, assistant: Assistant, active: bool) -> Assistant:
    assistant.webhook_active = active
    db.commit()
    db.refresh(assistant)
    return assistant
