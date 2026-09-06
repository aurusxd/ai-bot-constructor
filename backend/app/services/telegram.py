from typing import Any

import httpx
from loguru import logger

API_BASE = "https://api.telegram.org"
TIMEOUT = 15.0
POLL_TIMEOUT = 25


class TelegramError(Exception):
    """Raised when the Bot API rejects a call or is unreachable."""


def _call(bot_token: str, method: str, payload: dict[str, Any], timeout: float) -> dict[str, Any]:
    url = f"{API_BASE}/bot{bot_token}/{method}"
    try:
        response = httpx.post(url, json=payload, timeout=timeout)
    except httpx.HTTPError as exc:
        raise TelegramError(f"{method} request failed: {exc}") from exc

    body: dict[str, Any] = response.json()
    if not body.get("ok"):
        raise TelegramError(f"{method} rejected: {body.get('description', response.text)}")
    return body


def send_message(bot_token: str, chat_id: str, text: str) -> None:
    _call(bot_token, "sendMessage", {"chat_id": chat_id, "text": text}, TIMEOUT)
    logger.debug("Sent message to chat {}", chat_id)


def get_me(bot_token: str) -> dict[str, Any]:
    """Check that the token is valid before a bot is started."""
    result: dict[str, Any] = _call(bot_token, "getMe", {}, TIMEOUT)["result"]
    return result


def delete_webhook(bot_token: str) -> None:
    _call(bot_token, "deleteWebhook", {}, TIMEOUT)
    logger.info("Webhook deleted")


def get_updates(bot_token: str, offset: int | None) -> list[dict[str, Any]]:
    """Long poll for new updates, returning as soon as Telegram has any."""
    payload: dict[str, Any] = {"timeout": POLL_TIMEOUT, "allowed_updates": ["message"]}
    if offset is not None:
        payload["offset"] = offset

    # The read must outlast the long poll itself, otherwise every empty poll
    # would surface as a timeout error.
    result: list[dict[str, Any]] = _call(bot_token, "getUpdates", payload, POLL_TIMEOUT + TIMEOUT)[
        "result"
    ]
    return result
