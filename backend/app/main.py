from __future__ import annotations

import json
import threading
import traceback
import uuid
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from app.config import get_settings
from app.job_store import job_store
from app.schemas import JobCreateResponse, JobResultResponse, JobStatusResponse
from app.services.chunking import chunk_segments
from app.services.correction import build_glossary, correct_transcript
from app.services.embedding import embed_texts
from app.services.highlight import find_highlights
from app.services.matching import match_pages_to_chunks
from app.services.pdf_extract import extract_pdf
from app.services.polish import polish_text
from app.services.full_lecture_note import (
    FULL_LECTURE_DOCUMENT_PROMPT,
    generate_full_lecture_document,
)
from app.services.pdf_export import build_annotated_pdf, hex_to_rgb, summaries_from_result
from app.services.quiz import QUIZ_SYSTEM_PROMPT, generate_quiz
from app.services.summarize import SUMMARY_SYSTEM_PROMPT, summarize_page
from app.services.vision_caption import caption_pages, get_page_embedding_texts
from app.services.storage import (
    cleanup_audio,
    get_job_dir,
    get_pages_dir,
    save_job_files,
    save_json,
)
from app.services.transcribe import seconds_to_hhmmss, transcribe_audio

app = FastAPI(title="Lecture Script Matcher API", version="0.1.0")

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origin_list,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _set_progress(
    job_id: str,
    *,
    message: str,
    phase: str,
    transcribe: int | None = None,
    matching: int | None = None,
    overall: int | None = None,
) -> None:
    kwargs: dict = {
        "status": "processing",
        "message": message,
        "phase": phase,
    }
    if transcribe is not None:
        kwargs["transcribe_progress"] = transcribe
    if matching is not None:
        kwargs["matching_progress"] = matching
    if overall is not None:
        kwargs["progress"] = overall
    job_store.update(job_id, **kwargs)


def _run_pipeline(job_id: str) -> None:
    record = job_store.get(job_id)
    if not record:
        return

    options = record.options
    warnings: list[str] = []

    try:
        _set_progress(
            job_id,
            message="파일 업로드 완료",
            phase="transcribe",
            transcribe=5,
            matching=0,
            overall=5,
        )

        job_dir = get_job_dir(job_id)
        audio_files = list(job_dir.glob("audio.*"))
        pdf_files = list(job_dir.glob("lecture.*"))
        if not audio_files or not pdf_files:
            raise FileNotFoundError("업로드된 파일을 찾을 수 없습니다.")
        audio_path = str(audio_files[0])
        pdf_path = str(pdf_files[0])

        # PDF를 먼저 추출해 용어집(glossary)을 만들고, 이를 Whisper initial_prompt로
        # 넘겨 도메인 용어 인식률을 높인다.
        _set_progress(
            job_id,
            message="PDF 슬라이드 분석 중",
            phase="transcribe",
            transcribe=5,
            overall=8,
        )
        pages_dir = get_pages_dir(job_id)
        pages, pdf_warnings = extract_pdf(pdf_path, pages_dir)
        warnings.extend(pdf_warnings)
        save_json(job_id, "pages.json", pages)

        glossary = build_glossary(pages)

        # vision caption은 전사문과 무관하므로 전사와 "동시에" 백그라운드로 돌린다.
        # (전사가 끝날 때쯤 caption도 함께 끝나 대기 시간을 겹쳐서 줄인다.)
        caption_warnings: list[str] = []

        def _caption_worker() -> None:
            _, cw = caption_pages(pages)
            caption_warnings.extend(cw)

        caption_thread = threading.Thread(target=_caption_worker, daemon=True)
        caption_thread.start()

        _set_progress(
            job_id,
            message="음성 전사 준비 중",
            phase="transcribe",
            transcribe=8,
            overall=10,
        )

        def on_transcribe_progress(pct: int, msg: str) -> None:
            _set_progress(
                job_id,
                message=msg,
                phase="transcribe",
                transcribe=pct,
                overall=10 + int(pct * 0.28),
            )

        segments = transcribe_audio(
            audio_path, on_progress=on_transcribe_progress, glossary=glossary
        )
        save_json(job_id, "segments.json", segments)

        _set_progress(
            job_id,
            message="전사문 청크 분할 중",
            phase="transcribe",
            transcribe=97,
            overall=38,
        )
        chunks = chunk_segments(segments)
        save_json(job_id, "chunks.json", chunks)

        _set_progress(
            job_id,
            message="전사문 용어 교정 중 (fuzzy + LLM)",
            phase="transcribe",
            transcribe=98,
            overall=44,
        )

        def on_correction_progress(pct: int, msg: str) -> None:
            _set_progress(
                job_id,
                message=msg,
                phase="transcribe",
                transcribe=min(99, 98 + int(pct * 0.01)),
                overall=44 + int(pct * 0.05),
            )

        chunks, correction_warnings = correct_transcript(
            chunks, pages, on_progress=on_correction_progress
        )
        warnings.extend(correction_warnings)
        save_json(job_id, "chunks_corrected.json", chunks)

        _set_progress(
            job_id,
            message="음성 → 텍스트 변환 완료",
            phase="transcribe",
            transcribe=100,
            overall=48,
        )

        # 전사와 병렬로 돌던 vision caption이 끝나길 기다린다 (보통 이미 완료됨).
        _set_progress(
            job_id,
            message="슬라이드 시각 분석 정리 중",
            phase="matching",
            matching=20,
            overall=55,
        )
        caption_thread.join()
        warnings.extend(caption_warnings)
        save_json(job_id, "pages_captioned.json", pages)

        _set_progress(
            job_id,
            message="페이지·스크립트 임베딩 생성 중",
            phase="matching",
            matching=45,
            overall=62,
        )
        page_texts = get_page_embedding_texts(pages)
        chunk_texts = [c["text"] for c in chunks]
        page_embeddings = embed_texts(page_texts)
        chunk_embeddings = embed_texts(chunk_texts)

        _set_progress(
            job_id,
            message="텍스트 → 슬라이드 매칭 중",
            phase="matching",
            matching=75,
            overall=82,
        )
        page_matches, match_warnings = match_pages_to_chunks(
            pages, chunks, page_embeddings, chunk_embeddings
        )
        warnings.extend(match_warnings)

        readability_mode = bool(options.get("readability_mode"))
        highlight_mode = bool(options.get("highlight_mode"))
        summary_mode = bool(options.get("summary_mode"))
        note_mode = options.get("note_mode") or "summary"
        custom_prompt = (options.get("custom_prompt") or "").strip() or None

        if readability_mode:
            _set_progress(
                job_id,
                message="가독성 모드 적용 중",
                phase="polish",
                matching=85,
                overall=88,
            )

        n_pages = len(pages)

        # 1) 페이지별 matched_scripts를 먼저 구성 (가벼운 로컬 작업)
        page_scripts: list[list[dict]] = []
        for i, page in enumerate(pages):
            matched_scripts = []
            for ch in page_matches[i]:
                raw_text = ch.get("raw_text", ch["text"])
                display_text = ch["text"]
                clean_text = polish_text(display_text) if readability_mode else ""
                highlights = find_highlights(clean_text or display_text) if highlight_mode else []
                matched_scripts.append(
                    {
                        "chunk_id": ch["chunk_id"],
                        "start": ch["start"],
                        "end": ch["end"],
                        "start_time": ch["start_time"],
                        "end_time": ch["end_time"],
                        "raw_text": raw_text,
                        "corrected_text": display_text,
                        "clean_text": clean_text,
                        "score": round(float(ch.get("score", 0)), 4),
                        "highlights": highlights,
                        "carried_over": bool(ch.get("carried_over", False)),
                        "low_confidence": bool(ch.get("low_confidence", False)),
                    }
                )
            page_scripts.append(matched_scripts)

        # 2) 요약/퀴즈/전체정리본 생성
        summaries: list[list[str]] = [[] for _ in range(n_pages)]
        quizzes: list[list[dict]] = [[] for _ in range(n_pages)]
        lecture_document: dict[str, Any] = {}

        if summary_mode:
            from app.services.parallel import parallel_map

            if note_mode == "full_note":
                _set_progress(
                    job_id,
                    message="전체 강의 정리본 생성 중",
                    phase="polish",
                    matching=88,
                    overall=90,
                )
                lecture_document = generate_full_lecture_document(
                    pages, page_scripts, system_prompt=custom_prompt
                )
            else:
                phase_labels = {"quiz": "퀴즈 생성 중"}
                phase_label = phase_labels.get(note_mode, "핵심 요약 생성 중")

                def _note(i: int, page: dict):
                    if note_mode == "quiz":
                        if not page_scripts[i]:
                            return []
                        return generate_quiz(
                            page.get("text", ""),
                            page.get("caption", ""),
                            page_scripts[i],
                            system_prompt=custom_prompt,
                        )
                    if not page_scripts[i]:
                        return []
                    return summarize_page(
                        page.get("text", ""),
                        page.get("caption", ""),
                        page_scripts[i],
                        system_prompt=custom_prompt,
                    )

                def _note_progress(done: int, total: int) -> None:
                    pct = int(done / max(total, 1) * 100)
                    _set_progress(
                        job_id,
                        message=f"{phase_label} ({done}/{total}페이지)",
                        phase="polish",
                        matching=85 + int(pct * 0.14),
                        overall=88 + int(pct * 0.10),
                    )

                results = parallel_map(_note, list(pages), on_progress=_note_progress)
                if note_mode == "quiz":
                    quizzes = results
                else:
                    summaries = results

        result_pages = []
        for i, page in enumerate(pages):
            result_pages.append(
                {
                    "page": page["page"],
                    "page_image_url": f"/api/jobs/{job_id}/pages/{page['page']}.png",
                    "page_text": page["text"],
                    "page_caption": page.get("caption", ""),
                    "page_type": page.get("page_type", "content"),
                    "summary": summaries[i],
                    "quiz": quizzes[i],
                    "matched_scripts": page_scripts[i],
                }
            )

        _set_progress(
            job_id,
            message="텍스트 → 슬라이드 매칭 완료",
            phase="matching",
            matching=100,
            overall=98,
        )

        result = {
            "job_id": job_id,
            "status": "done",
            "warnings": warnings,
            "pages": result_pages,
            "readability_mode": readability_mode,
            "highlight_mode": highlight_mode,
            "summary_mode": summary_mode,
            "note_mode": note_mode,
            "lecture_document": lecture_document if lecture_document.get("title") else None,
            "background_color": options.get("background_color"),
            "text_color": options.get("text_color"),
            "text_size": options.get("text_size"),
        }

        save_json(job_id, "result.json", result)
        cleanup_audio(job_id)

        job_store.update(
            job_id,
            status="done",
            progress=100,
            transcribe_progress=100,
            matching_progress=100,
            phase="done",
            message="완료",
            result=result,
            warnings=warnings,
        )
    except Exception as exc:
        job_store.update(
            job_id,
            status="error",
            progress=0,
            message="처리 중 오류가 발생했습니다.",
            error=str(exc),
        )
        traceback.print_exc()


def _start_pipeline(job_id: str) -> None:
    thread = threading.Thread(target=_run_pipeline, args=(job_id,), daemon=True)
    thread.start()


@app.post("/api/jobs", response_model=JobCreateResponse)
async def create_job(
    background_tasks: BackgroundTasks,
    audio_file: UploadFile = File(...),
    pdf_file: UploadFile = File(...),
    readability_mode: bool = Form(False),
    highlight_mode: bool = Form(False),
    summary_mode: bool = Form(True),
    note_mode: str = Form("summary"),
    custom_prompt: str | None = Form(None),
    background_color: str | None = Form(None),
    text_color: str | None = Form(None),
    text_size: str | None = Form(None),
):
    job_id = str(uuid.uuid4())
    options = {
        "readability_mode": readability_mode,
        "highlight_mode": highlight_mode,
        "summary_mode": summary_mode,
        "note_mode": note_mode if note_mode in ("summary", "quiz", "full_note") else "summary",
        "custom_prompt": custom_prompt,
        "background_color": background_color,
        "text_color": text_color,
        "text_size": text_size,
    }
    job_store.create(job_id, options)
    save_job_files(job_id, audio_file, pdf_file)
    _start_pipeline(job_id)
    return JobCreateResponse(job_id=job_id)


@app.get("/api/prompts")
def get_default_prompts():
    """업로드 페이지에서 편집할 수 있는 기본 시스템 프롬프트."""
    return {
        "summary": SUMMARY_SYSTEM_PROMPT,
        "quiz": QUIZ_SYSTEM_PROMPT,
        "full_note": FULL_LECTURE_DOCUMENT_PROMPT,
    }


@app.get("/api/jobs/{job_id}/status", response_model=JobStatusResponse)
def get_job_status(job_id: str):
    record = job_store.get(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job을 찾을 수 없습니다.")
    return JobStatusResponse(
        job_id=job_id,
        status=record.status,  # type: ignore[arg-type]
        progress=record.progress,
        transcribe_progress=record.transcribe_progress,
        matching_progress=record.matching_progress,
        phase=record.phase,  # type: ignore[arg-type]
        message=record.message,
        error=record.error,
    )


@app.get("/api/jobs/{job_id}/result", response_model=JobResultResponse)
def get_job_result(job_id: str):
    record = job_store.get(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job을 찾을 수 없습니다.")
    if record.status != "done" or not record.result:
        raise HTTPException(status_code=400, detail="아직 처리가 완료되지 않았습니다.")
    return JobResultResponse(**record.result)


@app.get("/api/jobs/{job_id}/pages/{page_num}.png")
def get_page_image(job_id: str, page_num: int):
    pages_dir = get_pages_dir(job_id)
    image_path = pages_dir / f"page_{page_num:03d}.png"
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="페이지 이미지를 찾을 수 없습니다.")
    return FileResponse(str(image_path), media_type="image/png")


@app.get("/api/jobs/{job_id}/download.md")
def download_markdown(job_id: str):
    record = job_store.get(job_id)
    if not record or record.status != "done" or not record.result:
        raise HTTPException(status_code=400, detail="결과를 사용할 수 없습니다.")

    lines = [f"# Lecture Script Match — Job {job_id}\n"]
    doc = record.result.get("lecture_document") or {}
    if doc and doc.get("title"):
        lines.append(f"\n# {doc['title']}\n")
        lines.append(f"*{doc.get('subtitle', '')}*\n")
        if doc.get("key_summary"):
            lines.append("\n## 핵심 요약\n")
            for p in doc["key_summary"]:
                lines.append(f"- {p}")
        if doc.get("exam_questions"):
            lines.append("\n## 시험에서 이렇게 나온다\n")
            for q in doc["exam_questions"]:
                lines.append(f"- {q}")
        lines.append("\n---\n")

    for page in record.result["pages"]:
        lines.append(f"\n## Page {page['page']}\n")
        summary = page.get("summary") or []
        if summary:
            lines.append("### 핵심 정리\n")
            for point in summary:
                lines.append(f"- {point}")
            lines.append("")
        quiz = page.get("quiz") or []
        if quiz:
            lines.append("### 복습 퀴즈\n")
            for qi, item in enumerate(quiz, start=1):
                lines.append(f"**Q{qi}. {item.get('question', '')}**")
                if item.get("answer"):
                    lines.append(f"<details><summary>정답 보기</summary>{item['answer']}</details>")
                lines.append("")
        if page["matched_scripts"]:
            lines.append("### 교수님 스크립트\n")
        for script in page["matched_scripts"]:
            text = script.get("clean_text") or script.get("corrected_text") or script["raw_text"]
            lines.append(
                f"**[{script['start_time']} ~ {script['end_time']}]**\n\n{text}\n"
            )

    content = "\n".join(lines)
    md_path = get_job_dir(job_id) / "export.md"
    md_path.write_text(content, encoding="utf-8")
    return FileResponse(
        str(md_path),
        media_type="text/markdown",
        filename=f"lecture_script_{job_id[:8]}.md",
    )


@app.get("/api/jobs/{job_id}/download.json")
def download_json(job_id: str):
    record = job_store.get(job_id)
    if not record or record.status != "done" or not record.result:
        raise HTTPException(status_code=400, detail="결과를 사용할 수 없습니다.")
    json_path = get_job_dir(job_id) / "result.json"
    return FileResponse(
        str(json_path),
        media_type="application/json",
        filename=f"lecture_script_{job_id[:8]}.json",
    )


def _load_done_result(job_id: str) -> dict:
    """메모리 job store 또는 디스크 result.json에서 완료된 결과를 불러온다."""
    record = job_store.get(job_id)
    if record and record.status == "done" and record.result:
        return record.result
    json_path = get_job_dir(job_id) / "result.json"
    if json_path.exists():
        return json.loads(json_path.read_text(encoding="utf-8"))
    raise HTTPException(status_code=404, detail="Job을 찾을 수 없습니다.")


@app.get("/api/jobs/{job_id}/download.pdf")
def download_pdf(job_id: str, note_bg: str | None = None, note_text: str | None = None):
    result = _load_done_result(job_id)

    job_dir = get_job_dir(job_id)
    pdf_files = list(job_dir.glob("lecture.*"))
    if not pdf_files:
        raise HTTPException(status_code=404, detail="원본 PDF를 찾을 수 없습니다.")

    pdf_path = str(pdf_files[0])
    out_path = job_dir / "lecture_with_notes.pdf"
    result_note_mode = result.get("note_mode", "summary")
    page_summaries = summaries_from_result(result["pages"], note_mode=result_note_mode)

    if not page_summaries:
        raise HTTPException(
            status_code=400,
            detail="핵심 정리/퀴즈가 없습니다. 업로드 시 '핵심 요약' 옵션을 켜고 다시 처리해 주세요.",
        )

    try:
        _, export_warnings = build_annotated_pdf(
            pdf_path,
            page_summaries,
            str(out_path),
            note_bg=hex_to_rgb(note_bg),
            note_text=hex_to_rgb(note_text),
        )
        record = job_store.get(job_id)
        if record:
            for w in export_warnings:
                record.warnings.append(w)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"PDF 생성 실패: {exc}") from exc

    if not out_path.exists():
        raise HTTPException(status_code=500, detail="PDF 파일 생성에 실패했습니다.")

    return FileResponse(
        str(out_path),
        media_type="application/pdf",
        filename=f"lecture_notes_{job_id[:8]}.pdf",
    )


@app.get("/health")
def health():
    return {"status": "ok"}
