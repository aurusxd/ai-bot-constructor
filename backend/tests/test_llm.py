import json

import pytest
from fastapi.testclient import TestClient

from app.models import Assistant
from app.services import llm


def test_system_prompt_contains_assistant_fields(assistant: Assistant) -> None:
    prompt = llm.build_system_prompt(assistant)

    assert assistant.name in prompt
    assert assistant.position in prompt
    assert assistant.language in prompt
    assert assistant.tone in prompt
    assert assistant.business_description in prompt
    assert assistant.work_instruction in prompt


def test_system_prompt_asks_for_the_needs_human_flag(assistant: Assistant) -> None:
    prompt = llm.build_system_prompt(assistant)

    assert "needs_human" in prompt
    assert "reply" in prompt


def test_system_prompt_endpoint_matches_builder(client: TestClient, assistant: Assistant) -> None:
    response = client.get(f"/api/assistants/{assistant.id}/system-prompt")

    assert response.status_code == 200
    assert response.json()["prompt"] == llm.build_system_prompt(assistant)


def test_ask_parses_a_valid_answer(assistant: Assistant, monkeypatch: pytest.MonkeyPatch) -> None:
    answer = {"reply": "Кухня от 90 000 рублей", "needs_human": False, "reason": None}
    monkeypatch.setattr(llm, "_request", lambda messages: json.dumps(answer, ensure_ascii=False))

    result = llm.ask(assistant, [])

    assert result.needs_human is False
    assert result.reply == answer["reply"]


def test_ask_retries_once_on_a_malformed_answer(
    assistant: Assistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    answers = [
        json.dumps({"wrong": "shape"}),
        json.dumps({"reply": "", "needs_human": True, "reason": "нет данных"}, ensure_ascii=False),
    ]
    calls: list[int] = []

    def fake_request(messages: list[dict[str, str]]) -> str:
        calls.append(len(messages))
        return answers[len(calls) - 1]

    monkeypatch.setattr(llm, "_request", fake_request)

    result = llm.ask(assistant, [])

    assert len(calls) == 2
    # The retry carries the bad answer plus the format reminder.
    assert calls[1] == calls[0] + 2
    assert result.needs_human is True


def test_ask_raises_when_the_retry_also_fails(
    assistant: Assistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(llm, "_request", lambda messages: json.dumps({"wrong": "shape"}))

    with pytest.raises(llm.LlmError):
        llm.ask(assistant, [])
