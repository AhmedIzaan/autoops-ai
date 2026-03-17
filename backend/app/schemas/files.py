from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    file_id: str
    filename: str
    content_type: str | None = None
    path: str
    size: int | None = None
