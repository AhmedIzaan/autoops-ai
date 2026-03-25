import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from textwrap import dedent

from app.config import settings


def draft_email(
    subject: str,
    body: str | None = None,
    to: str | None = None,
    context: str | None = None,   # optional extra context for body auto-generation
) -> dict[str, object]:
    """
    Draft (and optionally send) an email.

    - If `body` is empty/None and `context` is provided, uses the LLM to generate the body.
    - If settings.send_emails is True and SMTP credentials are configured, sends the email.
    - Always returns a structured dict with subject, body, to, sent status, and preview.
    """

    # ── Ensure body exists ────────────────────────────────────────────────────
    raw_body = (body or "").strip()
    if not raw_body:
        if context:
            raw_body = _generate_body_with_llm(subject=subject, context=context)
        else:
            raw_body = f"Please find the details regarding: {subject}"

    formatted_body = dedent(raw_body).strip()
    sender = settings.smtp_sender or settings.smtp_username or "noreply@autoops.ai"

    result: dict[str, object] = {
        "to": to,
        "from": sender,
        "subject": subject.strip(),
        "body": formatted_body,
        "body_preview": formatted_body[:300] + ("..." if len(formatted_body) > 300 else ""),
        "sent": False,
        "send_skipped_reason": None,
    }

    # ── Attempt to send ───────────────────────────────────────────────────────
    if not settings.send_emails:
        result["send_skipped_reason"] = "AUTOOPS_SEND_EMAILS is false — email drafted but not sent."
        print(f"[email_draft] Draft only (send disabled): to={to}, subject={subject}")
        return result

    if not to:
        result["send_skipped_reason"] = "No recipient address (to=) provided."
        return result

    if not settings.smtp_username or not settings.smtp_password:
        result["send_skipped_reason"] = "SMTP credentials not configured (AUTOOPS_SMTP_USERNAME / AUTOOPS_SMTP_PASSWORD)."
        print("[email_draft] SMTP credentials missing — skipping send.")
        return result

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject.strip()
        msg["From"] = sender
        msg["To"] = to
        msg.attach(MIMEText(formatted_body, "plain", "utf-8"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(sender, [to], msg.as_string())

        result["sent"] = True
        result["send_skipped_reason"] = None
        print(f"[email_draft] ✅ Email sent to {to} — subject: {subject}")

    except Exception as exc:
        result["sent"] = False
        result["send_skipped_reason"] = f"SMTP error: {exc}"
        print(f"[email_draft] ❌ SMTP send failed: {exc!r}")

    return result


def _generate_body_with_llm(subject: str, context: str) -> str:
    """Use Gemini to write a professional email body based on subject + context."""
    try:
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import StrOutputParser
        from langchain_google_genai import ChatGoogleGenerativeAI

        if not settings.gemini_api_key:
            return context

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=settings.gemini_api_key,
        )
        prompt = ChatPromptTemplate.from_messages([
            (
                "system",
                "You are a professional business email writer. "
                "Write a concise, friendly, and professional email body based on the subject and context provided. "
                "Do NOT include Subject:, To:, or any headers. Just write the body text. "
                "Start with a greeting and end with a sign-off. Keep it under 200 words.",
            ),
            (
                "human",
                "Subject: {subject}\n\nContext / data to include:\n{context}",
            ),
        ])
        chain = prompt | llm | StrOutputParser()
        body = chain.invoke({"subject": subject, "context": context[:3000]}).strip()
        print(f"[email_draft] LLM generated body ({len(body)} chars)")
        return body
    except Exception as exc:
        print(f"[email_draft] LLM body generation failed: {exc!r}")
        return context
