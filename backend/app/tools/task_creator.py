from uuid import uuid4


def create_task(title: str, description: str | None = None, owner: str | None = None) -> dict[str, str | None]:
    return {"task_id": str(uuid4()), "title": title.strip(), "description": description, "owner": owner}
