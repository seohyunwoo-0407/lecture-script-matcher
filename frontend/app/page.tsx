"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
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
  const [optionsOpen, setOptionsOpen] = useState(false);
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
    <main className="min-h-screen bg-[#e4eaf1]">
      <header className="border-b border-black/10 bg-[#f7f8fa]/90 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-6 py-5 grid grid-cols-[1fr_auto_1fr] items-center gap-4">
          <Link href="/" className="font-display text-3xl tracking-tight text-slate-900 leading-none">
            <span className="font-bold">1</span>
            <span className="font-normal">Q</span>
          </Link>
          <p className="text-center text-sm md:text-base text-brand-600/90 whitespace-nowrap">
            한 번의 클릭으로 완성되는 필기
          </p>
          <nav className="justify-self-end text-sm text-slate-600 flex items-center gap-2">
            <a href="#help" className="hover:text-slate-900 transition-colors">
              help
            </a>
            <span className="text-slate-300">|</span>
            <a href="#how-to-use" className="hover:text-slate-900 transition-colors">
              how to use
            </a>
            <Link
              href="/result/demo"
              className="ml-2 hidden sm:inline-flex items-center px-3 py-1.5 rounded-md bg-brand-600 text-white text-xs font-medium
                border border-black shadow-[0_2px_6px_rgba(111,134,166,0.4)] hover:bg-brand-700 transition-colors"
            >
              demo
            </Link>
          </nav>
        </div>
      </header>

      <div className="max-w-4xl mx-auto px-6 py-14 md:py-20">
        {processing ? (
          <div className="py-16">
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
            optionsOpen={optionsOpen}
            onToggleOptions={() => setOptionsOpen((v) => !v)}
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

        <section id="how-to-use" className="mt-20 pt-8 border-t border-black/5 text-sm text-slate-500 space-y-2">
          <h2 className="text-slate-700 font-medium">how to use</h2>
          <ol className="list-decimal list-inside space-y-1">
            <li>Upload record로 강의 음성을 올립니다.</li>
            <li>Upload lecture로 PDF 강의록을 올립니다.</li>
            <li>필요하면 customizing에서 노트 모드·테마를 고릅니다.</li>
            <li>Done을 누르면 AI가 필기를 완성합니다.</li>
          </ol>
        </section>

        <section id="help" className="mt-8 text-sm text-slate-500 space-y-1">
          <h2 className="text-slate-700 font-medium">help</h2>
          <p>지원 음성: mp3, m4a, wav, mp4, webm · 강의록: PDF</p>
        </section>
      </div>
    </main>
  );
}
