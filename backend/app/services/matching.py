from __future__ import annotations

import re
from typing import Any

import numpy as np
from rank_bm25 import BM25Okapi

from app.services.embedding import cosine_similarity_matrix

TOKEN_RE = re.compile(r"[a-zA-Z0-9가-힣]+")
UPPER_ABBR_RE = re.compile(r"\b[A-Z]{2,}\b")
NUMBER_EXPR_RE = re.compile(r"\d+[\w\-./]*")
FORMULA_RE = re.compile(r"\b[A-Z][a-z]?\d*|[\w]+-[\w]+")
KOREAN_KEYWORDS = ["중요", "시험", "기억", "출제", "핵심", "주의"]

MIN_MATCH_SCORE = 0.35
# 이 값보다 페이지 최고 유사도가 낮으면 "미설명 슬라이드"로 보고 매칭하지 않는다.
UNMATCHED_SCORE = 0.14
# chunk가 작아졌으므로 한 슬라이드에 여러 개를 담을 수 있게 상한을 높인다.
# 실제 개수는 slide별로 다음 anchor까지의 창 크기(가변)로 결정된다.
MAX_CHUNKS_PER_PAGE = 6

# 페이지 타입
PAGE_CONTENT = "content"      # 실제 내용이 많은 슬라이드
PAGE_SECTION = "section"      # 제목/구분 슬라이드 (예: "I. 후두 검사")
PAGE_IMAGE_ONLY = "image_only"  # 텍스트가 거의 없는 그림/도표 슬라이드

# 섹션 슬라이드로 판단할 때 쓰는 힌트 패턴 (로마숫자/장번호 제목)
SECTION_HEAD_RE = re.compile(r"^\s*(?:[IVXⅠ-Ⅹ]+|\d+)\s*[.)]?\s*\S")


def classify_page_type(text: str) -> str:
    """슬라이드 텍스트로 페이지 타입을 추정한다.

    - 텍스트가 거의 없으면 IMAGE_ONLY (그림/도표 위주)
    - 짧고 줄 수가 적으면 SECTION (제목/구분 슬라이드)
    - 그 외는 CONTENT
    이렇게 나눠야 제목·구분 슬라이드에 엉뚱한 chunk가 랜덤 매칭되는 것을 막을 수 있다.
    """
    t = (text or "").strip()
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    n_chars = len(t)

    if n_chars < 25:
        return PAGE_IMAGE_ONLY

    # 짧은 텍스트 + 적은 줄 수 → 구분/제목 슬라이드
    if n_chars < 90 and len(lines) <= 3:
        return PAGE_SECTION
    if len(lines) <= 2 and n_chars < 120 and SECTION_HEAD_RE.match(lines[0] if lines else ""):
        return PAGE_SECTION

    return PAGE_CONTENT


def slide_title(text: str) -> str:
    """슬라이드 제목(첫 의미 있는 줄)을 뽑는다."""
    for ln in (text or "").splitlines():
        s = ln.strip()
        if len(s) >= 2:
            return s
    return ""


def tokenize(text: str) -> list[str]:
    tokens = TOKEN_RE.findall(text.lower())
    return [t for t in tokens if len(t) > 1]


def extract_anchor_terms(page_text: str) -> list[str]:
    anchors: set[str] = set()
    for pattern in (UPPER_ABBR_RE, NUMBER_EXPR_RE, FORMULA_RE):
        for match in pattern.findall(page_text):
            anchors.add(match)
    for kw in KOREAN_KEYWORDS:
        if kw in page_text:
            anchors.add(kw)
    words = re.findall(r"[A-Za-z]{3,}", page_text)
    for i in range(len(words) - 1):
        phrase = f"{words[i]} {words[i + 1]}"
        anchors.add(phrase.lower())
    return list(anchors)


def anchor_score(page_text: str, chunk_text: str) -> float:
    anchors = extract_anchor_terms(page_text)
    if not anchors:
        return 0.0
    chunk_lower = chunk_text.lower()
    hits = sum(1 for a in anchors if a.lower() in chunk_lower)
    return min(1.0, hits / max(1, len(anchors) * 0.3))


def min_max_normalize(scores: np.ndarray) -> np.ndarray:
    if scores.size == 0:
        return scores
    lo, hi = scores.min(), scores.max()
    if hi - lo < 1e-9:
        return np.zeros_like(scores)
    return (scores - lo) / (hi - lo)


def compute_bm25_scores(page_texts: list[str], chunk_texts: list[str]) -> np.ndarray:
    corpus_tokens = [tokenize(t) for t in chunk_texts]
    bm25 = BM25Okapi(corpus_tokens)
    scores = np.zeros((len(page_texts), len(chunk_texts)), dtype=np.float32)
    for i, page_text in enumerate(page_texts):
        query_tokens = tokenize(page_text)
        if not query_tokens:
            continue
        raw = np.array(bm25.get_scores(query_tokens), dtype=np.float32)
        scores[i] = min_max_normalize(raw)
    return scores


def compute_final_scores(
    page_texts: list[str],
    chunk_texts: list[str],
    page_embeddings: np.ndarray,
    chunk_embeddings: np.ndarray,
) -> np.ndarray:
    dense = cosine_similarity_matrix(page_embeddings, chunk_embeddings)
    bm25 = compute_bm25_scores(page_texts, chunk_texts)
    n_pages, n_chunks = dense.shape
    anchor = np.zeros((n_pages, n_chunks), dtype=np.float32)
    for i, page_text in enumerate(page_texts):
        for j, chunk_text in enumerate(chunk_texts):
            anchor[i, j] = anchor_score(page_text, chunk_text)
    return 0.70 * dense + 0.20 * bm25 + 0.10 * anchor


def _align_anchors_dp(
    scores: np.ndarray,
    stay_penalty: float = 0.03,
    jump_penalty: float = 0.015,
) -> list[int]:
    """전역 최적 monotonic 정렬 (DTW 방식 DP).

    페이지 순서와 chunk(시간) 순서가 모두 단조 증가한다는 제약 하에
    전체 점수 합을 최대화하는 anchor 경로를 찾는다.
    한 chunk는 최대 2개의 연속 페이지에서만 anchor가 될 수 있다
    (state 0 = 새로 진입, state 1 = 두 번째 연속 사용).
    새 chunk로 전진할 때 건너뛴 chunk 수에 비례해 jump_penalty를 부과하여,
    신호가 약한 구간에서 수십 분을 한 번에 건너뛰는 것을 억제한다.
    greedy와 달리 한 페이지의 노이즈가 전체 경로를 오염시키지 않는다.
    """
    n_pages, n_chunks = scores.shape
    NEG = -1e18
    # 페이지 수가 chunk 수의 2배를 넘으면 2연속 제한으로는 경로가 없으므로 완화
    allow_long_stay = n_pages > 2 * n_chunks

    dp0 = np.full((n_pages, n_chunks), NEG)
    dp1 = np.full((n_pages, n_chunks), NEG)
    dp0[0] = scores[0].astype(np.float64)

    # 전진 시 조상 chunk 인덱스 (backtrack용)
    back0 = np.full((n_pages, n_chunks), -1, dtype=np.int64)

    for p in range(1, n_pages):
        prev_best = np.maximum(dp0[p - 1], dp1[p - 1])

        # prefix max over c' < c, jump_penalty * (c - c') 반영
        # value(c') = prev_best[c'] + jump_penalty * c'  를 최대화하는 c'를 고르고
        # 최종적으로 - jump_penalty * c 를 더한다.
        adjusted = prev_best + jump_penalty * np.arange(n_chunks)
        best_val = NEG
        best_idx = -1
        pref_val = np.full(n_chunks, NEG)
        pref_idx = np.full(n_chunks, -1, dtype=np.int64)
        for c in range(n_chunks):
            pref_val[c] = best_val
            pref_idx[c] = best_idx
            if adjusted[c] > best_val:
                best_val = adjusted[c]
                best_idx = c

        dp0[p] = scores[p] + pref_val - jump_penalty * np.arange(n_chunks)
        back0[p] = pref_idx
        dp1[p] = scores[p] + dp0[p - 1] - stay_penalty
        if allow_long_stay:
            dp1[p] = np.maximum(dp1[p], scores[p] + dp1[p - 1] - stay_penalty)

    # backtrack
    anchors = [0] * n_pages
    c = int(np.argmax(np.maximum(dp0[-1], dp1[-1])))
    state = 0 if dp0[-1][c] >= dp1[-1][c] else 1
    anchors[-1] = c

    for p in range(n_pages - 1, 0, -1):
        if state == 1:
            anchors[p - 1] = c
            state = 0 if dp0[p - 1][c] >= dp1[p - 1][c] else 1
        else:
            prev_c = int(back0[p][c])
            if prev_c < 0:
                prev_c = c
            c = prev_c
            anchors[p - 1] = c
            state = 0 if dp0[p - 1][c] >= dp1[p - 1][c] else 1

    return anchors


def select_monotonic_matches(
    scores: np.ndarray,
    chunks: list[dict[str, Any]],
    *,
    page_types: list[str] | None = None,
    min_score: float = MIN_MATCH_SCORE,
    unmatched_score: float = UNMATCHED_SCORE,
    max_chunks_per_page: int = MAX_CHUNKS_PER_PAGE,
    max_chars_per_page: int = 2500,
    pace_weight: float = 0.12,
) -> tuple[list[list[dict[str, Any]]], list[str]]:
    warnings: list[str] = []
    n_pages, n_chunks = scores.shape
    if n_pages == 0 or n_chunks == 0:
        return [[] for _ in range(n_pages)], warnings

    if page_types is None:
        page_types = [PAGE_CONTENT] * n_pages

    # 약한 pacing prior: 신호가 약한(점수가 평평한) 구간에서는 페이지 진행률과
    # chunk 진행률이 비슷해지도록 유도한다. 강한 매칭 점수는 prior를 이기므로
    # 슬라이드별 설명 길이가 크게 달라도 실제 신호를 따라간다.
    pos_p = np.arange(n_pages) / max(n_pages - 1, 1)
    pos_c = np.arange(n_chunks) / max(n_chunks - 1, 1)
    prior = -pace_weight * np.abs(pos_p[:, None] - pos_c[None, :])

    anchors = _align_anchors_dp(scores + prior)
    anchor_scores = [float(scores[p, anchors[p]]) for p in range(n_pages)]

    # 적응형 신뢰도 threshold: 점수 분포가 전반적으로 낮으면 절대값 대신 분포 기준
    median_sc = float(np.median(anchor_scores))
    eff_min_score = min(min_score, max(0.15, 0.7 * median_sc))
    # unmatched 판정선도 분포에 맞춰 완화 (너무 공격적으로 비우지 않도록)
    eff_unmatched = min(unmatched_score, 0.5 * eff_min_score)

    page_matches: list[list[dict[str, Any]]] = []

    for p in range(n_pages):
        a = anchors[p]
        anchor_sc = anchor_scores[p]
        ptype = page_types[p]
        page_best = float(scores[p].max())

        # 제목/구분·그림 슬라이드는 신호가 뚜렷할 때만 매칭한다.
        # 내용이 거의 없는 슬라이드에 top-chunk를 억지로 붙이면 랜덤 매칭이 되므로,
        # 판정선을 CONTENT보다 높여 애매하면 비운다.
        if ptype in (PAGE_SECTION, PAGE_IMAGE_ONLY):
            gate = eff_min_score * (0.9 if ptype == PAGE_SECTION else 1.0)
            if page_best < gate:
                page_matches.append([])
                label = "구분/제목" if ptype == PAGE_SECTION else "그림/도표"
                warnings.append(
                    f"페이지 {p + 1}: {label} 슬라이드로 보여 매칭하지 않았습니다 "
                    f"(최고 유사도 {page_best:.2f})."
                )
                continue
        elif page_best < eff_unmatched:
            page_matches.append([])
            warnings.append(
                f"페이지 {p + 1}: 관련 발화를 찾지 못해 매칭하지 않았습니다 "
                f"(최고 유사도 {page_best:.2f}). 설명 없이 넘어간 슬라이드일 수 있습니다."
            )
            continue

        # 이 페이지의 chunk "구간": anchor부터 다음 페이지 anchor 직전까지 연속으로 담는다.
        # top-k를 흩뿌리는 대신 연속 구간이라, 교수님이 한 슬라이드를 길게 설명하면
        # 그 구간이 통째로, 빨리 넘긴 슬라이드는 짧게 들어간다.
        if p + 1 < n_pages:
            window_end = max(anchors[p + 1], a + 1)
        else:
            window_end = a + max_chunks_per_page
        window_end = min(window_end, a + max_chunks_per_page, n_chunks)
        chosen = list(range(a, window_end))  # 연속 구간, 시간순

        trimmed: list[dict[str, Any]] = []
        total_chars = 0
        for cid in chosen:
            ch = chunks[cid]
            if total_chars + len(ch["text"]) > max_chars_per_page and trimmed:
                break
            trimmed.append({**ch, "score": round(float(scores[p, cid]), 4)})
            total_chars += len(ch["text"])

        if not trimmed:
            trimmed = [{**chunks[a], "score": round(anchor_sc, 4)}]

        low_conf = anchor_sc < eff_min_score
        for m in trimmed:
            m["low_confidence"] = low_conf
        if low_conf:
            warnings.append(
                f"페이지 {p + 1}: 매칭 신뢰도 낮음 ({anchor_sc:.2f}), "
                "시간 순서 기준으로 배치했습니다."
            )

        page_matches.append(trimmed)

    return page_matches, warnings


def _title_boost_matrix(
    pages: list[dict[str, Any]], chunk_texts: list[str]
) -> np.ndarray:
    """슬라이드 제목 단어가 chunk에 등장하면 가점을 주는 행렬.

    제목은 슬라이드에서 가장 강한 anchor이므로, 제목 용어가 담긴 chunk에
    작은 additive boost를 준다(embedding 신호를 덮어쓰지 않는 수준).
    """
    n_pages, n_chunks = len(pages), len(chunk_texts)
    boost = np.zeros((n_pages, n_chunks), dtype=np.float32)
    lowered = [ct.lower() for ct in chunk_texts]
    for i, page in enumerate(pages):
        title = slide_title(page.get("text", ""))
        title_terms = [t for t in tokenize(title) if len(t) >= 2]
        if not title_terms:
            continue
        for j, ct in enumerate(lowered):
            hits = sum(1 for t in title_terms if t in ct)
            if hits:
                boost[i, j] = min(1.0, hits / len(title_terms))
    return boost


def match_pages_to_chunks(
    pages: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    page_embeddings: np.ndarray,
    chunk_embeddings: np.ndarray,
) -> tuple[list[list[dict[str, Any]]], list[str]]:
    page_texts = [
        p.get("embedding_text") or p.get("text", "") for p in pages
    ]
    chunk_texts = [c["text"] for c in chunks]
    scores = compute_final_scores(page_texts, chunk_texts, page_embeddings, chunk_embeddings)

    # 제목 부스트를 additive로 얹는다 (dense 우위를 유지하되 제목 일치를 반영).
    title_boost = _title_boost_matrix(pages, chunk_texts)
    scores = scores + 0.08 * title_boost

    page_types = [classify_page_type(p.get("text", "")) for p in pages]
    for p, ptype in zip(pages, page_types):
        p["page_type"] = ptype

    return select_monotonic_matches(scores, chunks, page_types=page_types)
