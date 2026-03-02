from textwrap import dedent


def draft_email(subject: str, body: str, to: str | None = None) -> dict[str, str | None]:
    formatted = dedent(body).strip()
    return {"to": to, "subject": subject.strip(), "body": formatted}
