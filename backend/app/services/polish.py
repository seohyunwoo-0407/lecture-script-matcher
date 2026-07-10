from __future__ import annotations

import time

from openai import OpenAI

from app.config import get_settings

POLISH_PROMPT = (
    "다음은 교수님의 강의 음성 전사문입니다. 구어체 표현을 자연스러운 문어체 강의노트 문장으로 바꾸세요. "
    "의미를 추가하거나 삭제하지 마세요. 전문 용어, 영어 약어, 수식, 숫자는 보존하세요. "
    "학생이 복습할 수 있는 문장으로만 다듬으세요. 원문에 없는 내용을 추측하지 마세요."
)


def polish_text(raw_text: str) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        return raw_text
    if not settings.openai_text_model:
        return raw_text

    client = OpenAI(api_key=settings.openai_api_key)
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=settings.openai_text_model,
                messages=[
                    {"role": "system", "content": POLISH_PROMPT},
                    {"role": "user", "content": raw_text},
                ],
                temperature=0.2,
            )
            content = response.choices[0].message.content
            return content.strip() if content else raw_text
        except Exception:
            if attempt == max_retries - 1:
                return raw_text
            time.sleep(2**attempt)
    return raw_text
