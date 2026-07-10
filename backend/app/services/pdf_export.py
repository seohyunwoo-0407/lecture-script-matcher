from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz

NOTE_HEADER = "핵심 정리"
NOTE_BG = (0.965, 0.973, 1.0)
NOTE_BORDER = (0.55, 0.65, 0.85)
NOTE_TITLE_COLOR = (0.12, 0.22, 0.55)
NOTE_TEXT_COLOR = (0.10, 0.12, 0.18)
EXAMPLE_COLOR = (0.45, 0.32, 0.05)


def hex_to_rgb(hex_str: str | None) -> tuple[float, float, float] | None:
    """'#rrggbb' 문자열을 0~1 RGB 튜플로 변환. 형식이 틀리면 None."""
    if not hex_str:
        return None
    s = hex_str.strip().lstrip("#")
    if len(s) != 6:
        return None
    try:
        return tuple(int(s[i : i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return None


def _load_cjk_font() -> fitz.Font:
    """한글 렌더링이 보장되는 폰트를 로드한다 (PyMuPDF 내장 CJK 우선)."""
    for name in ("korea", "cjk", "china-s"):
        try:
            return fitz.Font(name)
        except Exception:
            continue
    for path in (
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    ):
        if Path(path).exists():
            try:
                return fitz.Font(fontfile=path)
            except Exception:
                continue
    raise RuntimeError("한글 폰트를 로드할 수 없습니다.")


def _wrap_text(
    text: str,
    font: fitz.Font,
    fontsize: float,
    max_width: float,
    indent: str = "",
) -> list[str]:
    """폰트 실측 너비 기준으로 텍스트를 줄바꿈한다 (한글은 아무 곳에서나 개행 가능)."""
    lines: list[str] = []
    current = ""
    for ch in text:
        candidate = current + ch
        if font.text_length(candidate, fontsize) <= max_width:
            current = candidate
        else:
            lines.append(current)
            current = indent + ch
    if current.strip():
        lines.append(current)
    return lines or [text]


def build_annotated_pdf(
    pdf_path: str,
    page_summaries: dict[int, list[str]],
    output_path: str,
    *,
    note_bg: tuple[float, float, float] | None = None,
    note_text: tuple[float, float, float] | None = None,
) -> tuple[str, list[str]]:
    """
    원본 슬라이드는 그대로 두고, 페이지 높이를 늘려 슬라이드 '아래'에
    핵심 정리 노트 영역을 붙인 새 PDF를 생성한다. (겹침 없음)
    page_summaries: {1-based page number: summary bullets}
    note_bg / note_text: 노트 박스 배경·글씨 색 (None이면 기본값)
    """
    warnings: list[str] = []
    font = _load_cjk_font()

    bg_color = note_bg or NOTE_BG
    text_color = note_text or NOTE_TEXT_COLOR
    title_color = note_text or NOTE_TITLE_COLOR

    src = fitz.open(pdf_path)
    out = fitz.open()
    annotated = 0

    try:
        for page_idx in range(len(src)):
            page_num = page_idx + 1
            spage = src[page_idx]
            w, h = spage.rect.width, spage.rect.height
            summary = page_summaries.get(page_num) or []

            if not summary:
                npage = out.new_page(width=w, height=h)
                npage.show_pdf_page(npage.rect, src, page_idx)
                continue

            fontsize = max(9.0, min(12.5, w / 80))
            line_h = fontsize * 1.55
            pad = max(14.0, w * 0.025)
            max_text_w = w - 2 * pad

            # bullet별 줄바꿈 계산 → 필요한 노트 영역 높이 산출
            wrapped: list[tuple[str, bool]] = []  # (line, is_example/answer 강조)
            for point in summary:
                clean = point.strip().lstrip("-•* ")
                is_example = clean.startswith("예)") or clean.startswith("→")
                is_question = clean.startswith("Q") and ". " in clean[:6]
                prefix = "  ▸ " if is_example else ("" if is_question else "• ")
                for j, ln in enumerate(
                    _wrap_text(prefix + clean, font, fontsize, max_text_w, indent="    ")
                ):
                    wrapped.append((ln, is_example))

            title_h = fontsize * 2.0
            note_h = pad + title_h + len(wrapped) * line_h + pad

            npage = out.new_page(width=w, height=h + note_h)
            # 원본 슬라이드 (벡터 그대로)
            npage.show_pdf_page(fitz.Rect(0, 0, w, h), src, page_idx)

            # 노트 배경 + 구분선
            npage.draw_rect(
                fitz.Rect(0, h, w, h + note_h), fill=bg_color, color=None, overlay=True
            )
            npage.draw_line(
                fitz.Point(0, h), fitz.Point(w, h), color=NOTE_BORDER, width=1.2
            )

            title_writer = fitz.TextWriter(npage.rect)
            body_writer = fitz.TextWriter(npage.rect)
            example_writer = fitz.TextWriter(npage.rect)

            y = h + pad + fontsize
            title_writer.append(
                fitz.Point(pad, y), NOTE_HEADER, font=font, fontsize=fontsize * 1.1
            )
            y += title_h

            for line, is_example in wrapped:
                writer = example_writer if is_example else body_writer
                writer.append(fitz.Point(pad, y), line, font=font, fontsize=fontsize)
                y += line_h

            title_writer.write_text(npage, color=title_color)
            body_writer.write_text(npage, color=text_color)
            example_writer.write_text(npage, color=EXAMPLE_COLOR)
            annotated += 1

        if annotated == 0:
            warnings.append("핵심 정리가 들어간 페이지가 없습니다. 원본 PDF를 그대로 저장합니다.")

        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out.save(str(out_file), garbage=4, deflate=True)
    finally:
        out.close()
        src.close()

    return str(output_path), warnings


def summaries_from_result(
    pages: list[dict[str, Any]], note_mode: str = "summary"
) -> dict[int, list[str]]:
    """페이지별 노트 라인 목록을 만든다. quiz 모드면 Q/A를 줄 형태로 변환."""
    result: dict[int, list[str]] = {}
    for page in pages:
        if note_mode == "quiz":
            quiz = page.get("quiz") or []
            lines: list[str] = []
            for qi, item in enumerate(quiz, start=1):
                q = item.get("question", "").strip()
                a = item.get("answer", "").strip()
                if not q:
                    continue
                lines.append(f"Q{qi}. {q}")
                if a:
                    lines.append(f"→ 정답: {a}")
            if lines:
                result[int(page["page"])] = lines
        else:
            summary = page.get("summary") or []
            if summary:
                result[int(page["page"])] = summary
    return result
