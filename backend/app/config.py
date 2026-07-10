from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str = ""
    openai_embedding_model: str = "text-embedding-3-small"
    openai_text_model: str = ""
    openai_vision_model: str = ""

    # Railway 등 저메모리 환경 기본값. 로컬에서 품질 우선이면 small + beam 5
    whisper_model: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    whisper_beam_size: int = 1
    whisper_cpu_threads: int = 2
    # 1이면 Whisper와 vision caption을 동시에 돌리지 않음 (피크 RAM 감소)
    low_memory: bool = True

    job_storage_dir: str = "./storage/jobs"
    max_audio_size_mb: int = 500
    max_pdf_size_mb: int = 100
    # 쉼표 구분. Vercel 도메인은 allow_origin_regex로 추가 허용
    cors_origins: str = (
        "http://localhost:3000,http://localhost:3010,"
        "http://127.0.0.1:3000,http://127.0.0.1:3010"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def storage_path(self) -> Path:
        return Path(self.job_storage_dir).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
