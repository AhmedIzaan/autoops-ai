from datetime import datetime
from textwrap import dedent


def generate_markdown(title: str, summary: str, details: str | None = None) -> str:
    timestamp = datetime.utcnow().isoformat() + "Z"
    parts = [f"# {title.strip()}", f"_Generated: {timestamp}_", "", dedent(summary).strip()]
    if details:
        parts.extend(["", dedent(details).strip()])
    return "\n".join(parts)
