"use client";

import { useRef, type ReactNode } from "react";

function MicIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 64 64"
      fill="none"
      className={className}
      aria-hidden
    >
      <rect x="24" y="8" width="16" height="28" rx="8" fill="currentColor" />
      <path
        d="M16 30a16 16 0 0 0 32 0"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
        fill="none"
      />
      <path
        d="M32 46v8M22 54h20"
        stroke="currentColor"
        strokeWidth="4"
        strokeLinecap="round"
      />
    </svg>
  );
}

function LectureIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 80 64"
      fill="none"
      className={className}
      aria-hidden
    >
      <rect x="18" y="6" width="44" height="28" rx="2" fill="currentColor" opacity="0.85" />
      <rect x="22" y="10" width="36" height="20" rx="1" fill="#eef2e8" />
      <circle cx="40" cy="40" r="5" fill="currentColor" />
      <path
        d="M32 52c0-4.4 3.6-8 8-8s8 3.6 8 8"
        fill="currentColor"
      />
      <circle cx="22" cy="46" r="3.5" fill="currentColor" opacity="0.7" />
      <path d="M16 56c0-3.3 2.7-6 6-6s6 2.7 6 6" fill="currentColor" opacity="0.7" />
      <circle cx="58" cy="46" r="3.5" fill="currentColor" opacity="0.7" />
      <path d="M52 56c0-3.3 2.7-6 6-6s6 2.7 6 6" fill="currentColor" opacity="0.7" />
    </svg>
  );
}

interface UploadCardProps {
  title: string;
  accept: string;
  file: File | null;
  onFileSelect: (file: File | null) => void;
  icon: ReactNode;
  tone: "record" | "lecture";
}

function UploadCard({ title, accept, file, onFileSelect, icon, tone }: UploadCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const toneClass =
    tone === "lecture"
      ? "bg-[#c9d4c4] hover:bg-[#becbb8]"
      : "bg-[#c5d0de] hover:bg-[#b8c5d6]";

  return (
    <div
      className={`flex-1 min-h-[280px] rounded-[28px] px-8 py-10 flex flex-col items-center justify-between
        border-2 border-black/25 shadow-[0_8px_24px_rgba(40,55,80,0.12)] transition-all
        ${toneClass}
        ${file ? "ring-2 ring-brand-700 ring-offset-2 ring-offset-[#e4eaf1]" : ""}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => onFileSelect(e.target.files?.[0] ?? null)}
      />
      <div className="flex-1 flex items-center justify-center text-[#2f4538] w-28 h-28 drop-shadow-sm">
        {icon}
      </div>
      <div className="w-full flex flex-col items-center gap-2">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="w-full max-w-[200px] py-2.5 rounded-md bg-brand-600 text-white text-sm font-medium
            border border-black shadow-[0_2px_6px_rgba(40,55,80,0.35)] hover:bg-brand-700 transition-colors"
        >
          {title}
        </button>
        {file && (
          <p className="text-xs text-slate-700 font-medium truncate max-w-full bg-white/70 rounded px-2 py-0.5" title={file.name}>
            {file.name}
          </p>
        )}
      </div>
    </div>
  );
}

interface UploadPanelProps {
  audioFile: File | null;
  pdfFile: File | null;
  onAudioSelect: (f: File | null) => void;
  onPdfSelect: (f: File | null) => void;
  onSubmit: () => void;
  loading: boolean;
  error: string | null;
  optionsOpen: boolean;
  onToggleOptions: () => void;
  children?: ReactNode;
}

export default function UploadPanel({
  audioFile,
  pdfFile,
  onAudioSelect,
  onPdfSelect,
  onSubmit,
  loading,
  error,
  optionsOpen,
  onToggleOptions,
  children,
}: UploadPanelProps) {
  const canSubmit = !!(audioFile && pdfFile && !loading);

  return (
    <div className="space-y-6">
      <div className="rounded-[32px] bg-[#6F86A6]/25 border border-black/10 p-5 md:p-7 shadow-inner">
        <div className="flex flex-col md:flex-row gap-5 md:gap-6">
          <UploadCard
            title="Upload record"
            accept=".mp3,.m4a,.wav,.mp4,.webm,audio/*"
            file={audioFile}
            onFileSelect={onAudioSelect}
            icon={<MicIcon className="w-full h-full" />}
            tone="record"
          />
          <UploadCard
            title="Upload lecture"
            accept=".pdf,application/pdf"
            file={pdfFile}
            onFileSelect={onPdfSelect}
            icon={<LectureIcon className="w-full h-full" />}
            tone="lecture"
          />
        </div>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center gap-4 rounded-2xl bg-white/80 border border-black/10 px-4 py-3">
        <button
          type="button"
          onClick={onToggleOptions}
          className="inline-flex items-center gap-3 self-start px-5 py-2.5 rounded-md bg-brand-600 text-white text-sm font-medium
            border border-black shadow-[0_2px_6px_rgba(40,55,80,0.35)] hover:bg-brand-700 transition-colors"
          aria-expanded={optionsOpen}
        >
          customizing
          <span
            className={`text-[10px] leading-none transition-transform duration-200 ${
              optionsOpen ? "rotate-180" : ""
            }`}
          >
            ▼
          </span>
        </button>

        <div className="flex-1" />

        <button
          type="button"
          onClick={onSubmit}
          disabled={!canSubmit}
          className={`px-10 py-2.5 rounded-md text-sm font-semibold border border-black transition-all
            ${
              canSubmit
                ? "bg-brand-600 text-white shadow-[0_2px_6px_rgba(40,55,80,0.35)] hover:bg-brand-700"
                : "bg-slate-200 text-slate-400 cursor-not-allowed"
            }`}
        >
          {loading ? "업로드 중..." : "Done"}
        </button>
      </div>

      {optionsOpen && children}

      {error && (
        <p className="text-center text-red-600 text-sm bg-red-50 py-2 px-4 rounded-lg border border-red-200">
          {error}
        </p>
      )}
    </div>
  );
}
