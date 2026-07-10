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

    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    # CPU 전사 튜닝. beam_size를 1로 낮추면 정확도 손실은 작고 속도는 크게 오른다.
    # cpu_threads=0 이면 코어 수에 맞춰 자동(최대 16)으로 설정한다.
    whisper_beam_size: int = 5
    whisper_cpu_threads: int = 0

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
