from io import BytesIO

import docx
from pypdf import PdfReader


def extract_text(filename: str, content: bytes) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        reader = PdfReader(BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    if lower.endswith(".docx"):
        document = docx.Document(BytesIO(content))
        return "\n".join(paragraph.text for paragraph in document.paragraphs).strip()
    raise ValueError("Unsupported file format")


def basic_ats_checks(text: str) -> list[str]:
    issues = []
    if len(text.split()) < 200:
        issues.append("Resume appears too short for ATS richness.")
    if "@" not in text:
        issues.append("Email may be missing.")
    if "experience" not in text.lower():
        issues.append("Work experience section keyword not detected.")
    return issues
