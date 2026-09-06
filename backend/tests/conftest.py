from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app
from app.models import Assistant

ASSISTANT_PAYLOAD = {
    "name": "Анна",
    "position": "Менеджер по продажам",
    "language": "Русский",
    "tone": "дружелюбный",
    "business_description": "Мебель на заказ: кухни и шкафы-купе.",
    "work_instruction": "Уточняй размеры и сроки.",
    "fallback_message": "Передал вопрос коллеге.",
    "admin_chat_id": "777000",
    "bot_token": "123456:TEST",
}


@pytest.fixture
def db() -> Iterator[Session]:
    # StaticPool keeps the in-memory database alive across connections, so the
    # test client and the test body see the same data.
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def assistant(db: Session) -> Assistant:
    record = Assistant(**ASSISTANT_PAYLOAD)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record
