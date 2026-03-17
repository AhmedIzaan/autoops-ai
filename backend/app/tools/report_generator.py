from datetime import datetime
from textwrap import dedent
from typing import Any


def generate_markdown(title: str, summary: str, items: list[dict[str, Any]] | None = None, details: str | None = None) -> dict[str, str]:
    timestamp = datetime.utcnow().isoformat() + "Z"
    items = items or []
    bullet_lines = "\n".join([f"- {i.get('label', 'Item')}: {i.get('value', '')}" for i in items])
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
    return {"format": "markdown", "content": "\n".join(parts)}
