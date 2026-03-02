from pydantic import BaseModel


class RunCreate(BaseModel):
    prompt: str
    file_ids: list[str] | None = None


class RunStatus(BaseModel):
    run_id: str
    status: str
    message: str | None = None
