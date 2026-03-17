from pypdf import PdfReader
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import settings

# Max characters to feed the LLM — avoids huge context for very long PDFs
_MAX_CHARS = 12_000


def extract_text(file_path: str) -> dict[str, object]:
    """Extract text from a PDF and summarize it using an LLM."""
    reader = PdfReader(file_path)
    pages_text = [page.extract_text() or "" for page in reader.pages]
    full_text = "\n".join(pages_text).strip()

    result: dict[str, object] = {
        "page_count": len(reader.pages),
        "char_count": len(full_text),
    }

    if not full_text:
        result["summary"] = "No readable text could be extracted from this PDF."
        result["raw_extract"] = ""
        return result

    # Truncate to avoid exceeding token limits for very large docs
    truncated = full_text[:_MAX_CHARS]
    was_truncated = len(full_text) > _MAX_CHARS
    result["raw_extract"] = truncated

    if settings.gemini_api_key:
        try:
            llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=settings.gemini_api_key)
            prompt = ChatPromptTemplate.from_messages([
                (
                    "system",
                    "You are an expert document analyst. You will receive the text content extracted from a PDF. "
                    "Your job is to write a clear, concise summary of the document. "
                    "Structure your response as:\n"
                    "1. A short 2-3 sentence overview paragraph.\n"
                    "2. A 'Key Points' section with 4-6 bullet points of the most important facts, numbers, or conclusions.\n"
                    "3. A 'Action Items' section (if applicable) with any tasks, deadlines, or decisions that require follow-up.\n"
                    "Use plain language. Do NOT include any JSON or code blocks."
                    + (" Note: The document was truncated to fit context limits." if was_truncated else "")
                ),
                (
                    "human",
                    "Here is the PDF content:\n\n{text}"
                ),
            ])
            chain = prompt | llm | StrOutputParser()
            summary = chain.invoke({"text": truncated}).strip()
            result["summary"] = summary
        except Exception as exc:
            result["summary"] = f"LLM summarization failed: {exc}"
    else:
        # No LLM — return raw extract as the "summary"
        result["summary"] = truncated[:1000] + ("..." if len(truncated) > 1000 else "")

    return result
