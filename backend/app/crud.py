from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Assistant
from app.schemas import AssistantCreate, AssistantUpdate


def list_assistants(db: Session) -> list[Assistant]:
    return list(db.scalars(select(Assistant).order_by(Assistant.id)))


def get_assistant(db: Session, assistant_id: int) -> Assistant | None:
    return db.get(Assistant, assistant_id)


def create_assistant(db: Session, data: AssistantCreate) -> Assistant:
    assistant = Assistant(**data.model_dump())
    db.add(assistant)
    db.commit()
    db.refresh(assistant)
    return assistant


def update_assistant(db: Session, assistant: Assistant, data: AssistantUpdate) -> Assistant:
    for field, value in data.model_dump().items():
        setattr(assistant, field, value)
    db.commit()
    db.refresh(assistant)
    return assistant


def delete_assistant(db: Session, assistant: Assistant) -> None:
    db.delete(assistant)
    db.commit()
