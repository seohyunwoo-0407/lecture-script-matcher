"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import UploadPanel from "@/components/UploadPanel";
import OptionPanel from "@/components/OptionPanel";
import ProgressBar from "@/components/ProgressBar";
import { createJob } from "@/lib/api";
import { getThemeById, type TextSizeId, type ThemeId } from "@/lib/themes";

export default function HomePage() {
  const router = useRouter();
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [readabilityMode, setReadabilityMode] = useState(false);
  const [highlightMode, setHighlightMode] = useState(true);
  const [summaryMode, setSummaryMode] = useState(true);
  const [noteMode, setNoteMode] = useState<"summary" | "quiz" | "full_note">("summary");
  const [customPrompt, setCustomPrompt] = useState("");
  const [themeId, setThemeId] = useState<ThemeId>("classic");
  const [textSize, setTextSize] = useState<TextSizeId>("base");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [progressMessage, setProgressMessage] = useState("");
  const [transcribeProgress, setTranscribeProgress] = useState(0);
  const [matchingProgress, setMatchingProgress] = useState(0);
  const [phase, setPhase] = useState<"queued" | "transcribe" | "matching" | "polish" | "done">("queued");

  const handleSubmit = async () => {
    if (!audioFile || !pdfFile) return;
    setLoading(true);
    setError(null);

    try {
      const theme = getThemeById(themeId);
      const { job_id } = await createJob(audioFile, pdfFile, {
        readability_mode: readabilityMode,
        highlight_mode: highlightMode,
        summary_mode: summaryMode,
        note_mode: noteMode,
        custom_prompt: customPrompt,
        background_color: theme.background,
        text_color: theme.text,
        text_size: textSize,
      });
      setProcessing(true);
      setTranscribeProgress(0);
      setMatchingProgress(0);
      setPhase("queued");
      setProgressMessage("처리 시작...");

      const poll = async () => {
        const { getJobStatus } = await import("@/lib/api");
        const status = await getJobStatus(job_id);
        setTranscribeProgress(status.transcribe_progress);
        setMatchingProgress(status.matching_progress);
        setPhase(status.phase);
        setProgressMessage(status.message);

        if (status.status === "done") {
          router.push(`/result/${job_id}`);
          return;
        }
        if (status.status === "error") {
          setError(status.error || "처리 중 오류가 발생했습니다.");
          setProcessing(false);
          setLoading(false);
          return;
        }
        setTimeout(poll, 500);
      };
      poll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "업로드 실패");
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-gradient-to-b from-slate-50 to-slate-100">
      <div className="max-w-4xl mx-auto px-6 py-16">
        <header className="text-center mb-12">
          <div className="inline-block px-3 py-1 bg-brand-100 text-brand-700 text-xs font-semibold rounded-full mb-4">
            1Q / Lecture Script Matcher
          </div>
          <h1 className="text-3xl md:text-4xl font-bold text-slate-900 mb-3">
            한 번의 클릭으로 완성되는 필기
          </h1>
          <p className="text-slate-500 text-lg">
            AI가 알아서 정리해주는 강의록 위의 스크립트
          </p>
          <a
            href="/result/demo"
            className="inline-block mt-4 text-sm text-brand-600 hover:underline"
          >
            데모 결과 미리보기 →
          </a>
        </header>

        {processing ? (
          <div className="py-20">
            <ProgressBar
              message={progressMessage}
              transcribeProgress={transcribeProgress}
              matchingProgress={matchingProgress}
              phase={phase}
            />
          </div>
        ) : (
          <UploadPanel
            audioFile={audioFile}
            pdfFile={pdfFile}
            onAudioSelect={setAudioFile}
            onPdfSelect={setPdfFile}
            onSubmit={handleSubmit}
            loading={loading}
            error={error}
          >
            <OptionPanel
              readabilityMode={readabilityMode}
              highlightMode={highlightMode}
              summaryMode={summaryMode}
              noteMode={noteMode}
              customPrompt={customPrompt}
              themeId={themeId}
              textSize={textSize}
              onReadabilityChange={setReadabilityMode}
              onHighlightChange={setHighlightMode}
              onSummaryChange={setSummaryMode}
              onNoteModeChange={setNoteMode}
              onCustomPromptChange={setCustomPrompt}
              onThemeChange={setThemeId}
              onTextSizeChange={setTextSize}
            />
          </UploadPanel>
        )}
      </div>
    </main>
  );
}
