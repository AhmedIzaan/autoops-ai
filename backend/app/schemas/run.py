from typing import Any

from pydantic import BaseModel


class RunCreate(BaseModel):
    prompt: str
    file_refs: list[str] | None = None


class RunResult(BaseModel):
    run_id: str
    status: str
    message: str | None = None
    plan: list[dict[str, Any]] | None = None
    cursor: int | None = None
    tool_results: list[dict[str, Any]] | None = None


class RunStatus(BaseModel):
    run_id: str
    status: str
    message: str | None = None
