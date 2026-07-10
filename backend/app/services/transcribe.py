from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from app.config import get_settings

_model = None
_model_lock = threading.Lock()

ProgressCallback = Callable[[int, str], None]


def seconds_to_hhmmss(seconds: float) -> str:
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _get_whisper_model():
    global _model
    if _model is not None:
        return _model
    with _model_lock:
        if _model is not None:
            return _model
        import os

        from faster_whisper import WhisperModel

        settings = get_settings()
        cpu_threads = settings.whisper_cpu_threads
        if cpu_threads <= 0:
            cpu_threads = min(16, os.cpu_count() or 4)
        _model = WhisperModel(
            settings.whisper_model,
            device=settings.whisper_device,
            compute_type=settings.whisper_compute_type,
            cpu_threads=cpu_threads,
        )
        return _model


def _build_initial_prompt(glossary: list[str] | None, max_terms: int = 60) -> str:
    """PDF에서 뽑은 용어를 Whisper initial_prompt로 넣어 도메인 용어 인식률을 높인다.

    강의 도메인 용어(후두, TSH, 21-hydroxylase 등)를 미리 알려주면 발음이
    비슷한 일반 단어로 잘못 전사되는 것을 상당히 줄일 수 있다.
    """
    if not glossary:
        return ""
    terms = ", ".join(glossary[:max_terms])
    return f"다음은 의학 강의입니다. 등장 용어: {terms}."


def transcribe_audio(
    audio_path: str,
    on_progress: ProgressCallback | None = None,
    glossary: list[str] | None = None,
) -> list[dict[str, Any]]:
    if on_progress:
        on_progress(5, "Whisper 모델 준비 중...")

    model = _get_whisper_model()

    if on_progress:
        on_progress(10, "음성 파일 분석 중...")

    initial_prompt = _build_initial_prompt(glossary) or None
    beam_size = max(1, get_settings().whisper_beam_size)

    segments_iter, info = model.transcribe(
        audio_path,
        language="ko",
        beam_size=beam_size,
        vad_filter=True,
        initial_prompt=initial_prompt,
        condition_on_previous_text=True,
        no_speech_threshold=0.6,
        compression_ratio_threshold=2.4,
        temperature=[0.0, 0.2, 0.4],
    )

    duration = float(getattr(info, "duration", 0) or 0)
    if duration <= 0:
        duration = float(getattr(info, "duration_after_vad", 0) or 1.0)

    segments: list[dict[str, Any]] = []
    for idx, seg in enumerate(segments_iter):
        segments.append(
            {
                "segment_id": idx,
                "start": float(seg.start),
                "end": float(seg.end),
                "text": seg.text.strip(),
            }
        )
        if on_progress and duration > 0:
            ratio = min(1.0, float(seg.end) / duration)
            pct = int(10 + ratio * 82)  # 10% ~ 92%
            elapsed = seconds_to_hhmmss(seg.end)
            total = seconds_to_hhmmss(duration)
            on_progress(pct, f"음성 전사 중 ({elapsed} / {total})")

    if on_progress:
        on_progress(95, "전사 세그먼트 정리 중...")

    return segments
