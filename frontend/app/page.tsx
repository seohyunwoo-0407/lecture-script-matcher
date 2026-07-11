"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import UploadPanel from "@/components/UploadPanel";
import CustomizePanel from "@/components/CustomizePanel";
import SettingsSidebar from "@/components/SettingsSidebar";
import ProgressBar from "@/components/ProgressBar";
import { createJob } from "@/lib/api";
import { getThemeById, type TextSizeId, type ThemeId } from "@/lib/themes";

export default function HomePage() {
  const router = useRouter();
  const [audioFile, setAudioFile] = useState<File | null>(null);
  const [pdfFile, setPdfFile] = useState<File | null>(null);
  const [readabilityMode, setReadabilityMode] = useState(false);
  const [highlightMode, setHighlightMode] = useState(true);
  const [noteMode, setNoteMode] = useState<"summary" | "quiz" | "full_note">("full_note");
  const [customPrompt, setCustomPrompt] = useState("");
  const [themeId, setThemeId] = useState<ThemeId>("classic");
  const [textSize, setTextSize] = useState<TextSizeId>("base");
  const [optionsOpen, setOptionsOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processing, setProcessing] = useState(false);
  const [doneJobId, setDoneJobId] = useState<string | null>(null);
  const [progressMessage, setProgressMessage] = useState("");
  const [transcribeProgress, setTranscribeProgress] = useState(0);
  const [matchingProgress, setMatchingProgress] = useState(0);
  const [phase, setPhase] = useState<"queued" | "transcribe" | "matching" | "polish" | "done">("queued");
  const startedRef = useRef(false);

  const handleSubmit = async () => {
    if (!audioFile || !pdfFile || startedRef.current) return;
    startedRef.current = true;
    setLoading(true);
    setError(null);
    setDoneJobId(null);

    try {
      const theme = getThemeById(themeId);
      const { job_id } = await createJob(audioFile, pdfFile, {
        readability_mode: readabilityMode,
        highlight_mode: highlightMode,
        summary_mode: true,
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
          setPhase("done");
          setProgressMessage("완료");
          setTranscribeProgress(100);
          setMatchingProgress(100);
          setDoneJobId(job_id);
          setLoading(false);
          return;
        }
        if (status.status === "error") {
          setError(status.error || "처리 중 오류가 발생했습니다.");
          setProcessing(false);
          setLoading(false);
          startedRef.current = false;
          return;
        }
        setTimeout(poll, 500);
      };
      poll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "업로드 실패");
      setLoading(false);
      setProcessing(false);
      startedRef.current = false;
    }
  };

  return (
    <main className="min-h-screen bg-[#f5f5f0] relative overflow-x-hidden">
      <header className="border-b border-black/10 bg-[#f5f5f0]">
        <div className="max-w-5xl mx-auto px-6 py-5 grid grid-cols-[1fr_auto_1fr] items-center gap-4">
          <Link href="/" className="font-display text-[2rem] tracking-tight text-black leading-none">
            <span className="font-bold">1</span>
            <span className="font-semibold">Q</span>
          </Link>
          <p className="text-center text-sm md:text-[15px] text-[rgb(111,134,168)] whitespace-nowrap">
            한 번의 클릭으로 완성되는 필기
          </p>
          <nav className="justify-self-end text-sm text-slate-700 flex items-center gap-2">
            <a href="#help" className="hover:text-black transition-colors">
              help
            </a>
            <span className="text-slate-400">|</span>
            <a href="#how-to-use" className="hover:text-black transition-colors">
              how to use
            </a>
          </nav>
        </div>
      </header>

      {!processing && (
        <SettingsSidebar
          open={settingsOpen}
          onToggle={() => setSettingsOpen((v) => !v)}
          readabilityMode={readabilityMode}
          highlightMode={highlightMode}
          onReadabilityChange={setReadabilityMode}
          onHighlightChange={setHighlightMode}
        />
      )}

      <div className="max-w-5xl mx-auto px-6 pt-16 md:pt-20 pb-16">
        <UploadPanel
          audioFile={audioFile}
          pdfFile={pdfFile}
          onAudioSelect={setAudioFile}
          onPdfSelect={setPdfFile}
          onSubmit={handleSubmit}
          loading={loading}
          processing={processing}
          error={error}
          optionsOpen={optionsOpen}
          onToggleOptions={() => setOptionsOpen((v) => !v)}
        >
          <CustomizePanel
            noteMode={noteMode}
            customPrompt={customPrompt}
            themeId={themeId}
            textSize={textSize}
            onNoteModeChange={setNoteMode}
            onCustomPromptChange={setCustomPrompt}
            onThemeChange={setThemeId}
            onTextSizeChange={setTextSize}
          />
        </UploadPanel>

        {processing && (
          <ProgressBar
            message={progressMessage}
            transcribeProgress={transcribeProgress}
            matchingProgress={matchingProgress}
            phase={phase}
            canView={!!doneJobId}
            onView={() => doneJobId && router.push(`/result/${doneJobId}`)}
          />
        )}

        <section
          id="how-to-use"
          className="mt-24 pt-8 border-t border-black/5 text-sm text-slate-500 space-y-2 max-w-[860px] mx-auto"
        >
          <h2 className="text-slate-700 font-medium">how to use</h2>
          <ol className="list-decimal list-inside space-y-1">
            <li>Upload record로 강의 음성을 올립니다.</li>
            <li>Upload lecture로 PDF 강의록을 올립니다.</li>
            <li>오른쪽 설정에서 가독성·하이라이트를, customizing에서 테마·노트 모드를 고릅니다.</li>
            <li>두 파일을 올린 뒤 Done을 누르면 처리가 시작됩니다.</li>
          </ol>
        </section>

        <section id="help" className="mt-8 text-sm text-slate-500 space-y-1 max-w-[860px] mx-auto">
          <h2 className="text-slate-700 font-medium">help</h2>
          <p>지원 음성: mp3, m4a, wav, mp4, webm · 강의록: PDF</p>
          <Link href="/result/demo" className="text-[rgb(111,134,168)] hover:underline">
            demo 결과 미리보기 →
          </Link>
        </section>
      </div>
    </main>
  );
}
