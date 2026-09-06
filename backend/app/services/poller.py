import threading
from typing import Any

from loguru import logger

from app.database import SessionLocal
from app.models import Assistant
from app.schemas import TelegramUpdate
from app.services import telegram
from app.services.dialog import handle_message

# How long a poller waits before retrying after a Telegram or network failure.
ERROR_BACKOFF = 5.0


class _BotPoller:
    """One long polling loop, running in its own thread for a single bot."""

    def __init__(self, assistant_id: int, bot_token: str) -> None:
        self.assistant_id = assistant_id
        self.bot_token = bot_token
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, name=f"poller-{assistant_id}", daemon=True)

    def start(self) -> None:
        self.thread.start()

    def stop(self, timeout: float | None = None) -> None:
        self.stop_event.set()
        self.thread.join(timeout=timeout)

    def _run(self) -> None:
        logger.info("Poller started for assistant {}", self.assistant_id)
        offset: int | None = None

        while not self.stop_event.is_set():
            try:
                updates = telegram.get_updates(self.bot_token, offset)
            except telegram.TelegramError as exc:
                logger.error("Polling failed for assistant {}: {}", self.assistant_id, exc)
                self.stop_event.wait(ERROR_BACKOFF)
                continue

            for update in updates:
                offset = update["update_id"] + 1
                if self.stop_event.is_set():
                    break
                self._handle(update)

        logger.info("Poller stopped for assistant {}", self.assistant_id)

    def _handle(self, update: dict[str, Any]) -> None:
        parsed = TelegramUpdate.model_validate(update)
        if parsed.message is None or not parsed.message.text:
            return

        # Each poller thread needs its own session, and the assistant is reloaded
        # so edits made in the panel apply without restarting the bot.
        db = SessionLocal()
        try:
            assistant = db.get(Assistant, self.assistant_id)
            if assistant is None:
                logger.warning("Assistant {} disappeared while polling", self.assistant_id)
                return
            handle_message(db, assistant, str(parsed.message.chat.id), parsed.message.text)
        except Exception:
            # One bad message must not kill the loop for every later one.
            logger.exception("Failed to handle update for assistant {}", self.assistant_id)
        finally:
            db.close()


_pollers: dict[int, _BotPoller] = {}
_lock = threading.Lock()


def start(assistant_id: int, bot_token: str) -> None:
    with _lock:
        existing = _pollers.pop(assistant_id, None)
        if existing is not None:
            existing.stop(timeout=1.0)
        poller = _BotPoller(assistant_id, bot_token)
        _pollers[assistant_id] = poller
        poller.start()


def stop(assistant_id: int) -> None:
    with _lock:
        poller = _pollers.pop(assistant_id, None)
    if poller is not None:
        poller.stop(timeout=1.0)


def is_running(assistant_id: int) -> bool:
    with _lock:
        return assistant_id in _pollers


def stop_all() -> None:
    with _lock:
        pollers = list(_pollers.values())
        _pollers.clear()
    for poller in pollers:
        poller.stop(timeout=1.0)


def start_active() -> None:
    """Bring back the bots that were running before the last shutdown."""
    db = SessionLocal()
    try:
        for assistant in db.query(Assistant).filter(Assistant.bot_active.is_(True)):
            start(assistant.id, assistant.bot_token)
    finally:
        db.close()
