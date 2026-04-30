import re
import time
from collections import defaultdict, deque

from fastapi import HTTPException

from app.core.config import settings

_request_buckets: dict[str, deque[float]] = defaultdict(deque)
_ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def sanitize_text(value: str) -> str:
    cleaned = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", value)
    return cleaned.strip()


def validate_resume_filename(filename: str) -> None:
    lowered = filename.lower()
    if not any(lowered.endswith(ext) for ext in _ALLOWED_EXTENSIONS):
        raise HTTPException(status_code=415, detail="Only PDF and DOCX files are supported")


def enforce_rate_limit(bucket_key: str) -> None:
    now = time.time()
    window_start = now - 60
    bucket = _request_buckets[bucket_key]
    while bucket and bucket[0] < window_start:
        bucket.popleft()
    if len(bucket) >= settings.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    bucket.append(now)
