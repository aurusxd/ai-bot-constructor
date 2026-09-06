from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Assistant(Base):
    __tablename__ = "assistants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    position: Mapped[str] = mapped_column(String(255))
    language: Mapped[str] = mapped_column(String(64))
    tone: Mapped[str] = mapped_column(String(64))
    business_description: Mapped[str] = mapped_column(Text)
    work_instruction: Mapped[str] = mapped_column(Text)
    fallback_message: Mapped[str] = mapped_column(Text)
    admin_chat_id: Mapped[str] = mapped_column(String(64))
    bot_token: Mapped[str] = mapped_column(String(255))
    webhook_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="assistant", cascade="all, delete-orphan"
    )


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (UniqueConstraint("assistant_id", "telegram_chat_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    assistant_id: Mapped[int] = mapped_column(ForeignKey("assistants.id", ondelete="CASCADE"))
    telegram_chat_id: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    assistant: Mapped[Assistant] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(Enum("user", "assistant", name="message_role"))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="messages")
