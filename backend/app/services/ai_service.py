import json
import re
from typing import Any

from openai import OpenAI

from app.core.config import settings


class AIService:
    def __init__(self) -> None:
        self.client = None
        if settings.deepseek_api_key:
            self.client = OpenAI(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_base_url,
            )
        elif settings.openai_api_key:
            self.client = OpenAI(api_key=settings.openai_api_key)

    def _safe_json(self, text: str, fallback: dict[str, Any]) -> dict[str, Any]:
        cleaned = re.sub(r"```json|```", "", text).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            return fallback

    def generate_structured(self, system_prompt: str, user_prompt: str, fallback: dict[str, Any]) -> dict[str, Any]:
        if not self.client:
            return fallback
        try:
            response = self.client.chat.completions.create(
                model=settings.ai_model,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                timeout=30,
            )
            content = response.choices[0].message.content or "{}"
            return self._safe_json(content, fallback)
        except Exception:
            return fallback


ai_service = AIService()
