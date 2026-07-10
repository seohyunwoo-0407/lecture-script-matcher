from __future__ import annotations

import json
import time
from typing import Any

from openai import OpenAI

from app.config import get_settings

SUMMARY_SYSTEM_PROMPT = (
    "당신은 의대생을 위한 강의 노트 정리 도우미입니다. "
    "특정 강의 슬라이드와, 그 슬라이드를 설명하는 동안 교수님이 실제로 말한 전사문이 주어집니다. "
    "전사문에서 이 슬라이드의 개념과 관련해 교수님이 강조·설명·비교·예시로 든 내용을 "
    "복습용 개조식 노트로 풍부하게 정리하세요.\n\n"
    "규칙:\n"
    "- 각 항목은 명사형 종결체('~함.', '~임.', '~됨.', '~해야 함.')로 끝낸다.\n"
    "- 슬라이드에 적힌 정확한 의학 용어 표기를 사용한다(전사문에 오타가 있어도 슬라이드 표기를 따른다).\n"
    "- 슬라이드/전사문에 없는 내용은 절대 지어내지 않는다.\n"
    "- 교수님이 '시험에 나온다', '중요하다'고 언급한 부분은 항목 끝에 (⭐중요) 표시.\n"
    "- 교수님이 든 **구체적 예시**(증례, 임상 상황, 비유, 숫자, '~하면 ~한다' 식 설명)는 "
    "반드시 별도 항목으로 포함하고, 항목 앞에 '예)' 접두어를 붙인다. "
    "예: '예) 신생아에서 inspiratory stridor가 수면·식사 시 악화됨.'\n"
    "- 교수님이 A와 B를 **비교**했으면 'A vs B: ...' 형식으로 정리한다.\n"
    "- 정의, 원인, 증상, 진단, 치료, 강조 포인트, 주의사항 등 슬라이드 주제와 관련된 "
    "내용을 빠짐없이 담아 **5~10개** 항목으로 작성한다(관련 내용이 많으면 10개까지).\n"
    "- 관련 발화가 거의 없으면 빈 목록을 반환한다.\n"
    "출력은 반드시 JSON 형식: {\"points\": [\"...\", \"...\"]}"
)


FULL_NOTE_SYSTEM_PROMPT = (
    "당신은 의대생을 위한 강의 정리본 작성자입니다. "
    "특정 강의 슬라이드와, 그 슬라이드를 설명하는 동안 교수님이 실제로 말한 전사문이 주어집니다. "
    "슬라이드 내용과 교수님 설명을 통합해, 이 슬라이드 부분의 '완결된 정리본'을 작성하세요. "
    "각 슬라이드의 정리본을 이어 붙이면 강의 전체의 완성된 학습 노트가 되어야 합니다.\n\n"
    "규칙:\n"
    "- 슬라이드에 적힌 내용을 뼈대로 삼고, 교수님이 덧붙인 설명·예시·강조를 살로 붙인다.\n"
    "- 슬라이드에만 있고 교수님이 언급하지 않은 항목도 정리본에 포함한다(정리본은 완결성이 중요).\n"
    "- 개념 정의 → 상세 설명 → 예시/임상 포인트 순으로 자연스럽게 배치한다.\n"
    "- 각 항목은 명사형 종결체('~함.', '~임.', '~됨.')로 끝내되, 필요하면 2~3문장으로 충분히 설명한다.\n"
    "- 하위 개념은 항목 앞에 '- ' 를 붙여 들여쓰기 구조를 표현한다.\n"
    "- 교수님이 든 구체적 예시는 '예)' 접두어로 별도 항목 처리한다.\n"
    "- '시험에 나온다', '중요하다' 강조 부분은 항목 끝에 (⭐중요) 표시.\n"
    "- 슬라이드에 적힌 정확한 의학 용어 표기를 사용한다.\n"
    "- 슬라이드/전사문에 없는 내용은 절대 지어내지 않는다.\n"
    "- 분량 제한 없음. 슬라이드 내용을 빠짐없이 커버한다.\n"
    "출력은 반드시 JSON 형식: {\"points\": [\"...\", \"...\"]}"
)


def _extract_points(content: str) -> list[str]:
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.startswith("json"):
            content = content[4:]
    try:
        data = json.loads(content)
        points = data.get("points", [])
        return [str(p).strip() for p in points if str(p).strip()]
    except (json.JSONDecodeError, AttributeError):
        lines = [ln.strip("-• \t") for ln in content.splitlines() if ln.strip()]
        return [ln for ln in lines if len(ln) > 2][:10]


def summarize_page(
    page_text: str,
    caption: str,
    scripts: list[dict[str, Any]],
    system_prompt: str | None = None,
    require_scripts: bool = True,
) -> list[str]:
    settings = get_settings()
    if not settings.openai_api_key or not settings.openai_text_model:
        return []
    if not scripts and require_scripts:
        return []

    script_text = "\n".join(
        f"[{s.get('start_time', '')}] {s.get('corrected_text') or s.get('text') or s.get('raw_text', '')}"
        for s in scripts
    ).strip()
    if not script_text:
        if require_scripts:
            return []
        if not page_text.strip():
            return []
        script_text = "(이 슬라이드에 대한 교수님 발화 없음 — 슬라이드 내용만으로 정리)"

    slide_info = f"슬라이드 텍스트:\n{page_text.strip()}"
    if caption:
        slide_info += f"\n\n슬라이드 시각 설명:\n{caption.strip()}"

    user_prompt = (
        f"{slide_info}\n\n"
        f"이 슬라이드를 설명할 때 교수님의 전사문:\n{script_text}\n\n"
        "위 전사문에서 이 슬라이드 개념과 관련된 핵심 내용을 개조식으로 정리하세요. "
        "교수님이 말한 구체적 예시·비교·임상 포인트가 있으면 '예)' 항목으로 반드시 포함하세요."
    )

    client = OpenAI(api_key=settings.openai_api_key)
    for attempt in range(2):
        try:
            response = client.chat.completions.create(
                model=settings.openai_text_model,
                temperature=0.25,
                response_format={"type": "json_object"},
                messages=[
                    {"role": "system", "content": system_prompt or SUMMARY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            content = response.choices[0].message.content
            return _extract_points(content) if content else []
        except Exception:
            if attempt == 1:
                return []
            time.sleep(2**attempt)
    return []
