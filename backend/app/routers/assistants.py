from fastapi import APIRouter, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from app import crud
from app.database import DbSession
from app.models import Assistant, Conversation, Message
from app.schemas import (
    AssistantCreate,
    AssistantOut,
    AssistantUpdate,
    ConversationOut,
    MessageOut,
    SystemPromptOut,
)
from app.services import llm, poller, telegram

router = APIRouter(prefix="/api/assistants", tags=["assistants"])


def _get_or_404(db: Session, assistant_id: int) -> Assistant:
    assistant = crud.get_assistant(db, assistant_id)
    if assistant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assistant not found")
    return assistant


@router.get("", response_model=list[AssistantOut])
def list_assistants(db: DbSession) -> list[Assistant]:
    return crud.list_assistants(db)


@router.post("", response_model=AssistantOut, status_code=status.HTTP_201_CREATED)
def create_assistant(data: AssistantCreate, db: DbSession) -> Assistant:
    assistant = crud.create_assistant(db, data)
    logger.info("Created assistant {}", assistant.id)
    return assistant


@router.get("/{assistant_id}", response_model=AssistantOut)
def get_assistant(assistant_id: int, db: DbSession) -> Assistant:
    return _get_or_404(db, assistant_id)


@router.put("/{assistant_id}", response_model=AssistantOut)
def update_assistant(assistant_id: int, data: AssistantUpdate, db: DbSession) -> Assistant:
    assistant = _get_or_404(db, assistant_id)
    updated = crud.update_assistant(db, assistant, data)
    logger.info("Updated assistant {}", assistant_id)
    return updated


@router.delete("/{assistant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assistant(assistant_id: int, db: DbSession) -> None:
    assistant = _get_or_404(db, assistant_id)
    poller.stop(assistant_id)
    crud.delete_assistant(db, assistant)
    logger.info("Deleted assistant {}", assistant_id)


@router.post("/{assistant_id}/activate", response_model=AssistantOut)
def activate_assistant(assistant_id: int, db: DbSession) -> Assistant:
    assistant = _get_or_404(db, assistant_id)
    try:
        telegram.get_me(assistant.bot_token)
        # Telegram refuses getUpdates while a webhook is registered for the bot.
        telegram.delete_webhook(assistant.bot_token)
    except telegram.TelegramError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    poller.start(assistant.id, assistant.bot_token)
    logger.info("Activated assistant {}", assistant_id)
    return crud.set_bot_active(db, assistant, True)


@router.post("/{assistant_id}/deactivate", response_model=AssistantOut)
def deactivate_assistant(assistant_id: int, db: DbSession) -> Assistant:
    assistant = _get_or_404(db, assistant_id)
    poller.stop(assistant.id)
    logger.info("Deactivated assistant {}", assistant_id)
    return crud.set_bot_active(db, assistant, False)


@router.get("/{assistant_id}/conversations", response_model=list[ConversationOut])
def list_conversations(assistant_id: int, db: DbSession) -> list[Conversation]:
    _get_or_404(db, assistant_id)
    return crud.list_conversations(db, assistant_id)


@router.get(
    "/{assistant_id}/conversations/{telegram_chat_id}/messages",
    response_model=list[MessageOut],
)
def list_messages(assistant_id: int, telegram_chat_id: str, db: DbSession) -> list[Message]:
    _get_or_404(db, assistant_id)
    conversation = crud.get_conversation(db, assistant_id, telegram_chat_id)
    if conversation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")
    return crud.list_messages(db, conversation.id)


@router.get("/{assistant_id}/system-prompt", response_model=SystemPromptOut)
def get_system_prompt(assistant_id: int, db: DbSession) -> SystemPromptOut:
    assistant = _get_or_404(db, assistant_id)
    return SystemPromptOut(prompt=llm.build_system_prompt(assistant))
