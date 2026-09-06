import json
from typing import Any

import httpx
from loguru import logger
from pydantic import ValidationError

from app.config import get_settings
from app.models import Assistant, Message
from app.schemas import LlmReply

TIMEOUT = 60.0

SYSTEM_PROMPT_TEMPLATE = """You are {name}, a {position} of the business described below.
You talk to clients in a Telegram chat on behalf of that business.

Answer language: {language}
Tone of voice: {tone}

Business description:
{business_description}

Working instruction:
{work_instruction}

Rules:
- Answer only from the business description and the working instruction above.
- Never invent prices, terms, availability or any fact that is not stated there.
- Set "needs_human" to true when the question is off topic for this business,
  when answering needs data you were not given, or when the client asks for a human.
- When "needs_human" is true, leave "reply" empty and put a short explanation for
  the administrator into "reason", written in {language}.

Reply with a single JSON object and nothing else:
{{"reply": "text for the client", "needs_human": false, "reason": null}}"""

RETRY_INSTRUCTION = (
    "Your previous answer had the wrong shape. Reply with exactly this JSON object: "
    '{"reply": string, "needs_human": boolean, "reason": string or null}.'
)


class LlmError(Exception):
    """Raised when the provider is unreachable or keeps returning an unusable answer."""


def build_system_prompt(assistant: Assistant) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(
        name=assistant.name,
        position=assistant.position,
        language=assistant.language,
        tone=assistant.tone,
        business_description=assistant.business_description,
        work_instruction=assistant.work_instruction,
    )


def _request(messages: list[dict[str, str]]) -> str:
    settings = get_settings()
    try:
        response = httpx.post(
            f"{settings.deepseek_base_url}/chat/completions",
            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
            json={
                "model": settings.deepseek_model,
                "messages": messages,
                "response_format": {"type": "json_object"},
            },
            timeout=TIMEOUT,
        )
    except httpx.HTTPError as exc:
        raise LlmError(f"request failed: {exc}") from exc

    if response.status_code != httpx.codes.OK:
        raise LlmError(f"provider returned {response.status_code}: {response.text}")

    body: dict[str, Any] = response.json()
    try:
        content: str = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LlmError(f"unexpected response body: {body}") from exc
    return content


def _parse(content: str) -> LlmReply:
    return LlmReply.model_validate(json.loads(content))


def ask(assistant: Assistant, history: list[Message]) -> LlmReply:
    """Ask the provider for the next reply, retrying once on a malformed answer."""
    messages = [{"role": "system", "content": build_system_prompt(assistant)}]
    messages += [{"role": message.role, "content": message.content} for message in history]

    content = _request(messages)
    try:
        return _parse(content)
    except (json.JSONDecodeError, ValidationError) as exc:
        logger.warning("Malformed LLM answer, retrying: {}", exc)

    # json_object mode guarantees valid JSON but not the fields we need, so the
    # retry spells the shape out again.
    messages.append({"role": "assistant", "content": content})
    messages.append({"role": "user", "content": RETRY_INSTRUCTION})
    retry_content = _request(messages)
    try:
        return _parse(retry_content)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise LlmError(f"malformed answer after retry: {exc}") from exc
