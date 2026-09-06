from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import crud
from app.models import Assistant
from tests.conftest import ASSISTANT_PAYLOAD


def test_create_assistant_hides_bot_token(client: TestClient) -> None:
    response = client.post("/api/assistants", json=ASSISTANT_PAYLOAD)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == ASSISTANT_PAYLOAD["name"]
    assert body["webhook_active"] is False
    assert "bot_token" not in body


def test_list_assistants(client: TestClient, assistant: Assistant) -> None:
    response = client.get("/api/assistants")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [assistant.id]


def test_get_missing_assistant_returns_404(client: TestClient) -> None:
    assert client.get("/api/assistants/999").status_code == 404


def test_update_without_token_keeps_stored_one(
    client: TestClient, db: Session, assistant: Assistant
) -> None:
    payload = {**ASSISTANT_PAYLOAD, "name": "Анна Сергеевна"}
    del payload["bot_token"]

    response = client.put(f"/api/assistants/{assistant.id}", json=payload)

    assert response.status_code == 200
    db.expire_all()
    stored = db.get(Assistant, assistant.id)
    assert stored is not None
    assert stored.name == "Анна Сергеевна"
    assert stored.bot_token == ASSISTANT_PAYLOAD["bot_token"]


def test_update_with_token_replaces_it(
    client: TestClient, db: Session, assistant: Assistant
) -> None:
    payload = {**ASSISTANT_PAYLOAD, "bot_token": "999:NEW"}

    assert client.put(f"/api/assistants/{assistant.id}", json=payload).status_code == 200

    db.expire_all()
    stored = db.get(Assistant, assistant.id)
    assert stored is not None
    assert stored.bot_token == "999:NEW"


def test_delete_assistant(client: TestClient, assistant: Assistant) -> None:
    assert client.delete(f"/api/assistants/{assistant.id}").status_code == 204
    assert client.get(f"/api/assistants/{assistant.id}").status_code == 404


def test_conversation_is_reused_for_same_chat(db: Session, assistant: Assistant) -> None:
    first = crud.get_or_create_conversation(db, assistant.id, "555")
    second = crud.get_or_create_conversation(db, assistant.id, "555")

    assert first.id == second.id


def test_recent_messages_are_limited_and_chronological(db: Session, assistant: Assistant) -> None:
    conversation = crud.get_or_create_conversation(db, assistant.id, "555")
    for index in range(12):
        crud.add_message(db, conversation.id, "user", f"вопрос {index}")

    recent = crud.get_recent_messages(db, conversation.id, 10)

    assert len(recent) == 10
    assert [message.content for message in recent] == [f"вопрос {index}" for index in range(2, 12)]


def test_messages_endpoint_returns_history(
    client: TestClient, db: Session, assistant: Assistant
) -> None:
    conversation = crud.get_or_create_conversation(db, assistant.id, "555")
    crud.add_message(db, conversation.id, "user", "Сколько стоит кухня?")
    crud.add_message(db, conversation.id, "assistant", "Зависит от размеров.")

    response = client.get(f"/api/assistants/{assistant.id}/conversations/555/messages")

    assert response.status_code == 200
    assert [(item["role"], item["content"]) for item in response.json()] == [
        ("user", "Сколько стоит кухня?"),
        ("assistant", "Зависит от размеров."),
    ]


def test_messages_endpoint_404_for_unknown_chat(client: TestClient, assistant: Assistant) -> None:
    response = client.get(f"/api/assistants/{assistant.id}/conversations/000/messages")

    assert response.status_code == 404


def test_conversations_endpoint_lists_chats(
    client: TestClient, db: Session, assistant: Assistant
) -> None:
    crud.get_or_create_conversation(db, assistant.id, "111")
    crud.get_or_create_conversation(db, assistant.id, "222")

    response = client.get(f"/api/assistants/{assistant.id}/conversations")

    assert response.status_code == 200
    assert [item["telegram_chat_id"] for item in response.json()] == ["222", "111"]
