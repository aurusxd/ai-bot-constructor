from loguru import logger
from sqlalchemy.orm import Session

from app import crud
from app.models import Assistant
from app.schemas import LlmReply
from app.services import llm, telegram

HISTORY_LIMIT = 10

ADMIN_NOTIFICATION_TEMPLATE = (
    "Ассистент {name} не смог ответить.\n"
    "Чат клиента: {chat_id}\n"
    "Вопрос: {question}\n"
    "Причина: {reason}"
)


def _notify_admin(assistant: Assistant, chat_id: str, question: str, reason: str | None) -> None:
    text = ADMIN_NOTIFICATION_TEMPLATE.format(
        name=assistant.name,
        chat_id=chat_id,
        question=question,
        reason=reason or "не указана",
    )
    try:
        telegram.send_message(assistant.bot_token, assistant.admin_chat_id, text)
    except telegram.TelegramError as exc:
        # A failed hand-off must not break the reply the client is waiting for.
        logger.error("Could not notify admin of assistant {}: {}", assistant.id, exc)


def handle_message(db: Session, assistant: Assistant, chat_id: str, question: str) -> None:
    """Answer one client message, following the flow in section 6 of tech.md."""
    conversation = crud.get_or_create_conversation(db, assistant.id, chat_id)
    crud.add_message(db, conversation.id, "user", question)
    history = crud.get_recent_messages(db, conversation.id, HISTORY_LIMIT)

    try:
        answer = llm.ask(assistant, history)
    except llm.LlmError as exc:
        logger.error("LLM failed for assistant {}: {}", assistant.id, exc)
        answer = LlmReply(needs_human=True, reason=str(exc))

    if answer.needs_human or not answer.reply:
        _notify_admin(assistant, chat_id, question, answer.reason)
        reply_text = assistant.fallback_message
    else:
        reply_text = answer.reply
        crud.add_message(db, conversation.id, "assistant", reply_text)

    try:
        telegram.send_message(assistant.bot_token, chat_id, reply_text)
    except telegram.TelegramError as exc:
        logger.error("Could not reply in chat {}: {}", chat_id, exc)
