import re
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
from typing import Any
from uuid import uuid4

from app.config import settings


def _safe_filename(title: str) -> str:
    """Convert a title into a filesystem-safe filename."""
    slug = re.sub(r"[^\w\s-]", "", title.lower()).strip()
    slug = re.sub(r"[\s_-]+", "_", slug)
    return slug[:60] or "report"


def generate_markdown(
    title: str,
    summary: str,
    items: list[dict[str, Any]] | None = None,
    details: str | None = None,
) -> dict[str, str]:
    timestamp = datetime.now(timezone.utc).isoformat()
    items = items or []
    bullet_lines = "\n".join(
        [f"- {i.get('label', 'Item')}: {i.get('value', '')}" for i in items]
    )
    parts = [
        f"# {title.strip()}",
        f"_Generated: {timestamp}_",
        "",
        dedent(summary).strip(),
        "",
        "## Highlights",
        bullet_lines or "- (none)",
    ]
    if details:
        parts.extend(["", "## Details", dedent(details).strip()])

    content = "\n".join(parts)

    # ── Persist to disk ──────────────────────────────────────────────────────
    reports_dir = Path(settings.storage_dir).parent / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid4())[:8]
    safe_name = f"{_safe_filename(title)}_{file_id}.md"
    file_path = reports_dir / safe_name

    file_path.write_text(content, encoding="utf-8")
    print(f"[report_generator] Saved report → {file_path}")

    return {
        "format": "markdown",
        "title": title.strip(),
        "content": content,
        "file_path": str(file_path),
        "filename": safe_name,
        "download_url": f"/api/reports/{safe_name}",
        "char_count": str(len(content)),
    }
