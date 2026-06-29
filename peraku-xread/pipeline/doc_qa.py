import anthropic
from models.schemas import DocQAResult

client = anthropic.Anthropic()

SYSTEM_PROMPT = open("../.claude/agents/doc_qa_inspector.md").read()


def inspect(file_bytes: bytes, filename: str, password: str | None = None) -> DocQAResult:
    # Detect encryption before sending to Claude
    if _is_encrypted_pdf(file_bytes) and password is None:
        return DocQAResult(
            status="ENCRYPTED",
            reason="Document is password-protected.",
            action_required="PROMPT_USER_FOR_PASSWORD",
        )

    content = _extract_text(file_bytes, password)

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": f"Filename: {filename}\n\nExtracted content preview:\n{content[:3000]}",
            }
        ],
    )

    import json
    raw = message.content[0].text
    data = json.loads(raw)
    return DocQAResult(**data)


def _is_encrypted_pdf(file_bytes: bytes) -> bool:
    try:
        from pypdf import PdfReader
        from io import BytesIO
        reader = PdfReader(BytesIO(file_bytes))
        return reader.is_encrypted
    except Exception:
        return False


def _extract_text(file_bytes: bytes, password: str | None) -> str:
    try:
        from pypdf import PdfReader
        from io import BytesIO
        reader = PdfReader(BytesIO(file_bytes))
        if reader.is_encrypted and password:
            reader.decrypt(password)
            password = None  # wipe reference immediately
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as e:
        return f"[extraction error: {e}]"
