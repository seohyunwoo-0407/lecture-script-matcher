from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import get_settings

ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".m4a", ".wav", ".mp4", ".webm"}
ALLOWED_PDF_EXTENSIONS = {".pdf"}


def get_job_dir(job_id: str) -> Path:
    settings = get_settings()
    job_dir = settings.storage_path / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    return job_dir


def get_pages_dir(job_id: str) -> Path:
    pages_dir = get_job_dir(job_id) / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    return pages_dir


def _validate_extension(filename: str, allowed: set[str]) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"허용되지 않는 파일 형식입니다: {ext}. 허용: {', '.join(sorted(allowed))}",
        )
    return ext


def _read_limited(file: UploadFile, max_bytes: int) -> bytes:
    data = file.file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기가 제한({max_bytes // (1024 * 1024)}MB)을 초과했습니다.",
        )
    return data


def save_upload_file(file: UploadFile, dest: Path, max_bytes: int) -> None:
    data = _read_limited(file, max_bytes)
    dest.write_bytes(data)


def save_job_files(job_id: str, audio_file: UploadFile, pdf_file: UploadFile) -> tuple[Path, Path]:
    settings = get_settings()
    job_dir = get_job_dir(job_id)

    audio_ext = _validate_extension(audio_file.filename or "audio.mp3", ALLOWED_AUDIO_EXTENSIONS)
    pdf_ext = _validate_extension(pdf_file.filename or "lecture.pdf", ALLOWED_PDF_EXTENSIONS)

    audio_path = job_dir / f"audio{audio_ext}"
    pdf_path = job_dir / f"lecture{pdf_ext}"

    save_upload_file(
        audio_file,
        audio_path,
        settings.max_audio_size_mb * 1024 * 1024,
    )
    save_upload_file(
        pdf_file,
        pdf_path,
        settings.max_pdf_size_mb * 1024 * 1024,
    )
    return audio_path, pdf_path


def cleanup_audio(job_id: str) -> None:
    job_dir = get_job_dir(job_id)
    for path in job_dir.glob("audio.*"):
        path.unlink(missing_ok=True)


def save_json(job_id: str, name: str, data: dict | list) -> Path:
    import json

    path = get_job_dir(job_id) / name
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_json(job_id: str, name: str) -> dict | list:
    import json

    path = get_job_dir(job_id) / name
    return json.loads(path.read_text(encoding="utf-8"))
