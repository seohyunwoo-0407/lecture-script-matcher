from __future__ import annotations

import time
from typing import Optional

import numpy as np
from openai import OpenAI

from app.config import get_settings

EMBEDDING_DIM = 1536


def _require_api_key() -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError(
            "OPENAI_API_KEY가 설정되지 않아 페이지-스크립트 매칭을 수행할 수 없습니다."
        )
    return settings.openai_api_key


def _normalize_text(text: str) -> str:
    return " ".join(text.replace("\n", " ").split())


def _embed_batch(client: OpenAI, texts: list[str], model: str) -> list[list[float]]:
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.embeddings.create(input=texts, model=model)
            return [item.embedding for item in response.data]
        except Exception:
            if attempt == max_retries - 1:
                raise
            time.sleep(2**attempt)
    return []


def embed_texts(texts: list[str]) -> np.ndarray:
    api_key = _require_api_key()
    settings = get_settings()
    client = OpenAI(api_key=api_key)
    model = settings.openai_embedding_model

    normalized = [_normalize_text(t) for t in texts]
    non_empty_indices = [i for i, t in enumerate(normalized) if t.strip()]
    result = np.zeros((len(texts), EMBEDDING_DIM), dtype=np.float32)

    if not non_empty_indices:
        return result

    batch_size = 64
    for start in range(0, len(non_empty_indices), batch_size):
        batch_indices = non_empty_indices[start : start + batch_size]
        batch_texts = [normalized[i] for i in batch_indices]
        embeddings = _embed_batch(client, batch_texts, model)
        for idx, emb in zip(batch_indices, embeddings):
            result[idx] = np.array(emb, dtype=np.float32)

    return result


def l2_normalize(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    return matrix / norms


def cosine_similarity_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a_norm = l2_normalize(a)
    b_norm = l2_normalize(b)
    return a_norm @ b_norm.T
