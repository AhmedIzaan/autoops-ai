from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.config import settings


# Sync engine for tool use (tools run in thread pool, not async context)
_sync_url = settings.db_url.replace("aiosqlite", "sqlite")
_engine = create_engine(_sync_url, connect_args={"check_same_thread": False})


def create_task(
    title: str,
    description: str | None = None,
    owner: str | None = None,
    priority: str = "medium",
    source_run_id: str | None = None,
    context: str | None = None,   # extra context for LLM description generation
) -> dict[str, object]:
    """
    Create a task and persist it to the SQLite database.

    - If description is empty but context is provided, Gemini writes a description.
    - Returns full task metadata including the DB id.
    """
    from app.models.run import Task  # local import to avoid circular deps at startup

    task_id = str(uuid4())
    clean_title = title.strip()

    # ── Auto-generate description with LLM if not provided ───────────────────
    final_description = (description or "").strip() or None
    if not final_description and (context or clean_title):
        final_description = _generate_description(clean_title, context or clean_title)

    now = datetime.now(timezone.utc)

    task = Task(
        id=task_id,
        title=clean_title,
        description=final_description,
        owner=owner,
        priority=priority if priority in {"low", "medium", "high"} else "medium",
        status="todo",
        source_run_id=source_run_id,
        created_at=now,
        updated_at=now,
    )

    try:
        with Session(_engine) as session:
            session.add(task)
            session.commit()
            session.refresh(task)
        print(f"[task_creator] ✅ Task saved — id={task_id}, title='{clean_title}'")
    except Exception as exc:
        print(f"[task_creator] ❌ DB save failed: {exc!r}")

    return {
        "task_id": task_id,
        "title": clean_title,
        "description": final_description,
        "owner": owner,
        "priority": priority,
        "status": "todo",
        "source_run_id": source_run_id,
        "created_at": now.isoformat(),
    }


def _generate_description(title: str, context: str) -> str | None:
    """Use Gemini to write a concise task description."""
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not settings.gemini_api_key:
            return None

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=settings.gemini_api_key,
        )
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a project manager writing task descriptions. "
                "Given a task title and some context, write a clear, actionable description "
                "in 2-3 sentences. Be specific and practical. No bullet points.",
            ),
            ("human", "Task: {title}\n\nContext:\n{context}"),
        ])
        chain = prompt | llm | StrOutputParser()
        desc = chain.invoke({"title": title, "context": context[:2000]}).strip()
        print(f"[task_creator] LLM description generated ({len(desc)} chars)")
        return desc
    except Exception as exc:
        print(f"[task_creator] LLM description failed: {exc!r}")
        return None
