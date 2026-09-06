from fastapi import APIRouter, HTTPException, status
from loguru import logger
from sqlalchemy.orm import Session

from app import crud
from app.database import DbSession
from app.models import Assistant
from app.schemas import AssistantCreate, AssistantOut, AssistantUpdate

router = APIRouter(prefix="/api/assistants", tags=["assistants"])


def _get_or_404(db: Session, assistant_id: int) -> Assistant:
    assistant = crud.get_assistant(db, assistant_id)
    if assistant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assistant not found")
    return assistant


@router.get("", response_model=list[AssistantOut])
def list_assistants(db: DbSession) -> list[Assistant]:
    return crud.list_assistants(db)


@router.post("", response_model=AssistantOut, status_code=status.HTTP_201_CREATED)
def create_assistant(data: AssistantCreate, db: DbSession) -> Assistant:
    assistant = crud.create_assistant(db, data)
    logger.info("Created assistant {}", assistant.id)
    return assistant


@router.get("/{assistant_id}", response_model=AssistantOut)
def get_assistant(assistant_id: int, db: DbSession) -> Assistant:
    return _get_or_404(db, assistant_id)


@router.put("/{assistant_id}", response_model=AssistantOut)
def update_assistant(assistant_id: int, data: AssistantUpdate, db: DbSession) -> Assistant:
    assistant = _get_or_404(db, assistant_id)
    updated = crud.update_assistant(db, assistant, data)
    logger.info("Updated assistant {}", assistant_id)
    return updated


@router.delete("/{assistant_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assistant(assistant_id: int, db: DbSession) -> None:
    assistant = _get_or_404(db, assistant_id)
    crud.delete_assistant(db, assistant)
    logger.info("Deleted assistant {}", assistant_id)
