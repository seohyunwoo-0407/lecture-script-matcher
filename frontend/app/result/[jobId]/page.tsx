"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import PdfPreview from "@/components/PdfPreview";
import ScriptPanel from "@/components/ScriptPanel";
import SummaryPanel from "@/components/SummaryPanel";
import QuizPanel from "@/components/QuizPanel";
import FullLectureNoteView from "@/components/FullLectureNoteView";
import ProgressBar from "@/components/ProgressBar";
import {
  getDownloadUrl,
  getJobResult,
  getJobStatus,
  getPageImageUrl,
  apiUrl,
  type JobResultResponse,
} from "@/lib/api";

const NOTE_BG_OPTIONS = [
  { label: "연파랑", value: "#f5f8ff" },
  { label: "연노랑", value: "#fefce8" },
  { label: "연녹색", value: "#f0fdf4" },
  { label: "연회색", value: "#f8fafc" },
  { label: "흰색", value: "#ffffff" },
];

const NOTE_TEXT_OPTIONS = [
  { label: "검정", value: "#1a1f2e" },
  { label: "남색", value: "#1e3a8a" },
  { label: "진녹색", value: "#14532d" },
  { label: "갈색", value: "#713f12" },
];

export default function ResultPage({ params }: { params: { jobId: string } }) {
  const { jobId } = params;
  const [result, setResult] = useState<JobResultResponse | null>(null);
  const [pageIndex, setPageIndex] = useState(0);
  const [showScript, setShowScript] = useState(true);
  const [noteBg, setNoteBg] = useState(NOTE_BG_OPTIONS[0].value);
  const [noteText, setNoteText] = useState(NOTE_TEXT_OPTIONS[0].value);
  const [viewMode, setViewMode] = useState<"document" | "slides">("document");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [progressMessage, setProgressMessage] = useState("");
  const [transcribeProgress, setTranscribeProgress] = useState(0);
  const [matchingProgress, setMatchingProgress] = useState(0);
  const [phase, setPhase] = useState<"queued" | "transcribe" | "matching" | "polish" | "done">("queued");

  const loadResult = useCallback(async () => {
    try {
      const status = await getJobStatus(jobId);
      if (status.status === "error") {
        setError(status.error || "처리 실패");
        setLoading(false);
        return;
      }
      if (status.status !== "done") {
        setTranscribeProgress(status.transcribe_progress);
        setMatchingProgress(status.matching_progress);
        setPhase(status.phase);
        setProgressMessage(status.message);
        return false;
      }
      const data = await getJobResult(jobId);
      setResult(data);
      if (data.note_mode !== "full_note" || !data.lecture_document) {
        setViewMode("slides");
      }
      setLoading(false);
      return true;
    } catch (e) {
      setError(e instanceof Error ? e.message : "결과 로드 실패");
      setLoading(false);
      return true;
    }
  }, [jobId]);

  const loadMock = useCallback(async () => {
    const res = await fetch("/sample_result.json");
    const data = await res.json();
    // 데모 JSON의 localhost 이미지 URL은 배포 환경에서 동작하지 않음
    data.pages = (data.pages || []).map((p: { page_image_url?: string }) => ({
      ...p,
      page_image_url: "",
    }));
    setResult(data);
    setLoading(false);
    setError(null);
  }, []);

  useEffect(() => {
    if (jobId === "demo" || jobId === "sample") {
      loadMock();
      return;
    }
    let cancelled = false;
    const poll = async () => {
      if (cancelled) return;
      const done = await loadResult();
      if (!done && !cancelled) {
        setTimeout(poll, 500);
      }
    };
    poll();
    return () => {
      cancelled = true;
    };
  }, [loadResult, jobId, loadMock]);

  if (loading && !result) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-slate-50">
        <div className="w-full max-w-lg px-6">
          <ProgressBar
            message={progressMessage || "결과 로딩 중..."}
            transcribeProgress={transcribeProgress}
            matchingProgress={matchingProgress}
            phase={phase}
          />
        </div>
      </main>
    );
  }

  if (error && !result) {
    return (
      <main className="min-h-screen flex flex-col items-center justify-center bg-slate-50 gap-4">
        <p className="text-red-600">{error}</p>
        <button
          onClick={loadMock}
          className="text-brand-600 underline text-sm"
        >
          Mock 결과 보기
        </button>
        <Link href="/" className="text-slate-500 text-sm">
          ← 돌아가기
        </Link>
      </main>
    );
  }

  if (!result || result.pages.length === 0) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <p className="text-slate-500">결과가 없습니다.</p>
      </main>
    );
  }

  const currentPage = result.pages[pageIndex];
  const totalPages = result.pages.length;
  const hasLectureDoc =
    result.note_mode === "full_note" && !!result.lecture_document?.title;
  const imageUrl = apiUrl(
    currentPage.page_image_url.startsWith("http")
      ? currentPage.page_image_url
      : currentPage.page_image_url.startsWith("/api")
        ? currentPage.page_image_url
        : getPageImageUrl(jobId, currentPage.page)
  );

  return (
    <main className="min-h-screen bg-slate-100">
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between">
        <div>
          <Link href="/" className="text-sm text-slate-400 hover:text-slate-600">
            ← 새 업로드
          </Link>
          <h1 className="text-lg font-semibold text-slate-800 mt-1">
            강의 스크립트 매칭 결과
          </h1>
        </div>
        <div className="flex gap-2 items-center flex-wrap justify-end">
          {jobId !== "demo" && jobId !== "sample" && (
            <>
              {result.summary_mode && result.note_mode === "full_note" && (
                <a
                  href={`${getDownloadUrl(jobId, "pdf")}?note_bg=${encodeURIComponent(
                    noteBg
                  )}&note_text=${encodeURIComponent(noteText)}`}
                  className="px-4 py-2 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700 font-medium border border-black"
                >
                  PDF (전체 정리본)
                </a>
              )}
              {result.summary_mode && result.note_mode !== "full_note" && (
                <div className="flex items-center gap-2">
                  <label className="flex items-center gap-1.5 text-xs text-slate-500">
                    박스색
                    <select
                      value={noteBg}
                      onChange={(e) => setNoteBg(e.target.value)}
                      className="text-xs border border-slate-200 rounded-md px-1.5 py-1 bg-white"
                      style={{ backgroundColor: noteBg }}
                    >
                      {NOTE_BG_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="flex items-center gap-1.5 text-xs text-slate-500">
                    글씨색
                    <select
                      value={noteText}
                      onChange={(e) => setNoteText(e.target.value)}
                      className="text-xs border border-slate-200 rounded-md px-1.5 py-1 bg-white font-medium"
                      style={{ color: noteText }}
                    >
                      {NOTE_TEXT_OPTIONS.map((o) => (
                        <option key={o.value} value={o.value} style={{ color: o.value }}>
                          {o.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <a
                    href={`${getDownloadUrl(jobId, "pdf")}?note_bg=${encodeURIComponent(
                      noteBg
                    )}&note_text=${encodeURIComponent(noteText)}`}
                    className="px-4 py-2 text-sm bg-brand-600 text-white rounded-lg hover:bg-brand-700 font-medium border border-black"
                  >
                    PDF (핵심정리 포함)
                  </a>
                </div>
              )}
              <a
                href={getDownloadUrl(jobId, "md")}
                className="px-4 py-2 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50"
              >
                Markdown
              </a>
              <a
                href={getDownloadUrl(jobId, "json")}
                className="px-4 py-2 text-sm bg-white border border-slate-200 rounded-lg hover:bg-slate-50"
              >
                JSON
              </a>
            </>
          )}
        </div>
      </header>

      {result.warnings.length > 0 && (
        <div className="mx-6 mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg text-sm text-amber-800">
          {result.warnings.map((w, i) => (
            <p key={i}>⚠ {w}</p>
          ))}
        </div>
      )}

      <div className="mx-auto px-6 py-6 max-w-[1600px]">
        {hasLectureDoc && (
          <div className="flex gap-2 mb-4">
            <button
              onClick={() => setViewMode("document")}
              className={`px-4 py-2 text-sm rounded-lg border transition ${
                viewMode === "document"
                  ? "bg-brand-600 text-white border-brand-600"
                  : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
              }`}
            >
              전체 정리본
            </button>
            <button
              onClick={() => setViewMode("slides")}
              className={`px-4 py-2 text-sm rounded-lg border transition ${
                viewMode === "slides"
                  ? "bg-brand-600 text-white border-brand-600"
                  : "bg-white text-slate-600 border-slate-200 hover:bg-slate-50"
              }`}
            >
              슬라이드별 보기
            </button>
          </div>
        )}

        {viewMode === "document" && result.lecture_document ? (
          <FullLectureNoteView
            document={result.lecture_document}
            onSlideRef={(pageNum) => {
              const idx = result.pages.findIndex((p) => p.page === pageNum);
              if (idx >= 0) {
                setPageIndex(idx);
                setViewMode("slides");
              }
            }}
          />
        ) : (
          <>
        <div className="flex justify-between items-center mb-3">
          <div>
            {currentPage.page_type === "section" && (
              <span className="text-xs text-violet-700 bg-violet-50 px-2 py-1 rounded">
                구분/제목 슬라이드
              </span>
            )}
            {currentPage.page_type === "image_only" && (
              <span className="text-xs text-teal-700 bg-teal-50 px-2 py-1 rounded">
                그림/도표 슬라이드
              </span>
            )}
          </div>
          <button
            onClick={() => setShowScript((v) => !v)}
            className="text-sm px-3 py-1.5 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-slate-600"
          >
            {showScript ? "원본 스크립트 숨기기" : "원본 스크립트 보기"}
          </button>
        </div>
        <div
          className={`grid grid-cols-1 gap-6 ${
            showScript ? "xl:grid-cols-3" : "lg:grid-cols-2"
          }`}
        >
          <PdfPreview
            imageUrl={imageUrl}
            pageNumber={currentPage.page}
            totalPages={totalPages}
          />
          {result.note_mode === "quiz" ? (
            <QuizPanel
              quiz={currentPage.quiz || []}
              hasScripts={currentPage.matched_scripts.length > 0}
              pageKey={currentPage.page}
            />
          ) : result.note_mode === "full_note" ? (
            <SummaryPanel
              summary={currentPage.summary || []}
              hasScripts={currentPage.matched_scripts.length > 0}
              title="슬라이드 메모"
              subtitle="전체 정리본은 상단 탭에서 확인"
            />
          ) : (
            <SummaryPanel
              summary={currentPage.summary || []}
              hasScripts={currentPage.matched_scripts.length > 0}
            />
          )}
          {showScript && (
            <ScriptPanel
              scripts={currentPage.matched_scripts}
              readabilityMode={!!result.readability_mode}
              highlightMode={!!result.highlight_mode}
              backgroundColor={result.background_color}
              textColor={result.text_color}
              textSize={result.text_size}
            />
          )}
        </div>
          </>
        )}
      </div>

      {viewMode === "slides" && (
      <footer className="fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 py-4">
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-center gap-6">
          <button
            onClick={() => setPageIndex((i) => Math.max(0, i - 1))}
            disabled={pageIndex === 0}
            className="px-6 py-2 rounded-lg border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
          >
            Prev
          </button>
          <span className="text-sm font-medium text-slate-600">
            Page {currentPage.page} / {totalPages}
          </span>
          <button
            onClick={() => setPageIndex((i) => Math.min(totalPages - 1, i + 1))}
            disabled={pageIndex >= totalPages - 1}
            className="px-6 py-2 rounded-lg border border-slate-200 disabled:opacity-40 hover:bg-slate-50"
          >
            Next
          </button>
        </div>
      </footer>
      )}
    </main>
  );
}
