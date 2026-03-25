from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _uuid() -> str:
    return str(uuid4())


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    prompt: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    message: Mapped[str | None] = mapped_column(String, nullable=True)
    plan: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    cursor: Mapped[int | None] = mapped_column(default=0)
    tool_results: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())


class FileArtifact(Base):
    __tablename__ = "file_artifacts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String, nullable=True)
    path: Mapped[str] = mapped_column(String, nullable=False)
    size: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    owner: Mapped[str | None] = mapped_column(String, nullable=True)
    priority: Mapped[str] = mapped_column(String, default="medium")  # low | medium | high
    status: Mapped[str] = mapped_column(String, default="todo")       # todo | in_progress | done
    source_run_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())