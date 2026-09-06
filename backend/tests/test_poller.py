from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Assistant
from app.services import dialog, llm, poller, telegram


@pytest.fixture(autouse=True)
def no_live_bots() -> Any:
    """Keep real polling threads out of the tests."""
    yield
    poller.stop_all()


def test_activate_starts_a_poller(
    client: TestClient, db: Session, assistant: Assistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    started: list[tuple[int, str]] = []
    monkeypatch.setattr(telegram, "get_me", lambda token: {"username": "demo_bot"})
    monkeypatch.setattr(telegram, "delete_webhook", lambda token: None)
    monkeypatch.setattr(poller, "start", lambda aid, token: started.append((aid, token)))

    response = client.post(f"/api/assistants/{assistant.id}/activate")

    assert response.status_code == 200
    assert response.json()["bot_active"] is True
    assert started == [(assistant.id, assistant.bot_token)]


def test_activate_rejects_a_bad_token(
    client: TestClient, db: Session, assistant: Assistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    def bad_token(token: str) -> dict[str, Any]:
        raise telegram.TelegramError("getMe rejected: Unauthorized")

    started: list[int] = []
    monkeypatch.setattr(telegram, "get_me", bad_token)
    monkeypatch.setattr(poller, "start", lambda aid, token: started.append(aid))

    response = client.post(f"/api/assistants/{assistant.id}/activate")

    assert response.status_code == 502
    assert started == []
    db.expire_all()
    stored = db.get(Assistant, assistant.id)
    assert stored is not None
    assert stored.bot_active is False


def test_deactivate_stops_the_poller(
    client: TestClient, assistant: Assistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    stopped: list[int] = []
    monkeypatch.setattr(poller, "stop", lambda aid: stopped.append(aid))

    response = client.post(f"/api/assistants/{assistant.id}/deactivate")

    assert response.status_code == 200
    assert response.json()["bot_active"] is False
    assert stopped == [assistant.id]


def test_delete_stops_the_poller(
    client: TestClient, assistant: Assistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    stopped: list[int] = []
    monkeypatch.setattr(poller, "stop", lambda aid: stopped.append(aid))

    assert client.delete(f"/api/assistants/{assistant.id}").status_code == 204
    assert stopped == [assistant.id]


def test_poller_advances_the_offset_and_handles_text(
    db: Session, assistant: Assistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    offsets: list[int | None] = []
    handled: list[str] = []

    def fake_get_updates(token: str, offset: int | None) -> list[dict[str, Any]]:
        offsets.append(offset)
        if offset is None:
            return [
                {"update_id": 7, "message": {"chat": {"id": 555}, "text": "Привет"}},
                {"update_id": 8, "message": {"chat": {"id": 555}}},
            ]
        instance.stop_event.set()
        return []

    monkeypatch.setattr(telegram, "get_updates", fake_get_updates)
    monkeypatch.setattr(poller, "SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)
    monkeypatch.setattr(
        poller,
        "handle_message",
        lambda session, record, chat_id, text: handled.append(text),
    )

    instance = poller._BotPoller(assistant.id, assistant.bot_token)
    instance._run()

    # The second poll confirms both updates, and the update without text is skipped.
    assert offsets == [None, 9]
    assert handled == ["Привет"]


def test_poller_survives_a_telegram_failure(
    assistant: Assistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[int] = []

    def flaky(token: str, offset: int | None) -> list[dict[str, Any]]:
        calls.append(1)
        if len(calls) == 1:
            raise telegram.TelegramError("Bad Gateway")
        instance.stop_event.set()
        return []

    monkeypatch.setattr(telegram, "get_updates", flaky)
    monkeypatch.setattr(poller, "ERROR_BACKOFF", 0.01)

    instance = poller._BotPoller(assistant.id, assistant.bot_token)
    instance._run()

    assert len(calls) == 2


def test_handle_message_falls_back_when_llm_fails(
    db: Session, assistant: Assistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(
        telegram, "send_message", lambda token, chat_id, text: sent.append((chat_id, text))
    )

    def broken(record: Assistant, history: list[Any]) -> Any:
        raise llm.LlmError("provider down")

    monkeypatch.setattr(llm, "ask", broken)

    dialog.handle_message(db, assistant, "555", "Сколько стоит кухня?")

    admin_text = dict(sent)[assistant.admin_chat_id]
    assert assistant.name in admin_text
    assert "Сколько стоит кухня?" in admin_text
    assert dict(sent)["555"] == assistant.fallback_message
