from typing import Any

import httpx
from loguru import logger

API_BASE = "https://api.telegram.org"
TIMEOUT = 15.0


class TelegramError(Exception):
    """Raised when the Bot API rejects a call or is unreachable."""


def _call(bot_token: str, method: str, payload: dict[str, Any]) -> dict[str, Any]:
    url = f"{API_BASE}/bot{bot_token}/{method}"
    try:
        response = httpx.post(url, json=payload, timeout=TIMEOUT)
    except httpx.HTTPError as exc:
        raise TelegramError(f"{method} request failed: {exc}") from exc

    body: dict[str, Any] = response.json()
    if not body.get("ok"):
        raise TelegramError(f"{method} rejected: {body.get('description', response.text)}")
    return body


def send_message(bot_token: str, chat_id: str, text: str) -> None:
    _call(bot_token, "sendMessage", {"chat_id": chat_id, "text": text})
    logger.debug("Sent message to chat {}", chat_id)


def set_webhook(bot_token: str, url: str) -> None:
    _call(bot_token, "setWebhook", {"url": url})
    logger.info("Webhook set to {}", url)


def delete_webhook(bot_token: str) -> None:
    _call(bot_token, "deleteWebhook", {})
    logger.info("Webhook deleted")
