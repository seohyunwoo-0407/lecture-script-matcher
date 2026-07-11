"use client";

import { useRef, type ReactNode } from "react";

export const ACCENT = "rgb(111, 134, 168)";

export function AccentButton({
  children,
  className = "",
  onClick,
  type = "button",
  disabled,
  title,
}: {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  type?: "button" | "submit";
  disabled?: boolean;
  title?: string;
}) {
  return (
    <button
      type={type}
      title={title}
      disabled={disabled}
      onClick={onClick}
      className={`bg-[rgb(111,134,168)] text-black text-sm font-medium
        border border-black/30 rounded-[4px]
        shadow-[0_2px_0_rgba(0,0,0,0.28),0_3px_8px_rgba(0,0,0,0.12)]
        hover:brightness-105 active:translate-y-[1px] active:shadow-[0_1px_0_rgba(0,0,0,0.28)]
        disabled:opacity-50 disabled:cursor-not-allowed transition
        ${className}`}
    >
      {children}
    </button>
  );
}

function MicIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 64 64" fill="none" className={className} aria-hidden>
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
    <svg viewBox="0 0 80 64" fill="none" className={className} aria-hidden>
      <rect x="18" y="6" width="44" height="28" rx="2" fill="currentColor" opacity="0.9" />
      <rect x="22" y="10" width="36" height="20" rx="1" fill="#f5f5f0" />
      <circle cx="40" cy="40" r="5" fill="currentColor" />
      <path d="M32 52c0-4.4 3.6-8 8-8s8 3.6 8 8" fill="currentColor" />
      <circle cx="22" cy="46" r="3.5" fill="currentColor" opacity="0.75" />
      <path d="M16 56c0-3.3 2.7-6 6-6s6 2.7 6 6" fill="currentColor" opacity="0.75" />
      <circle cx="58" cy="46" r="3.5" fill="currentColor" opacity="0.75" />
      <path d="M52 56c0-3.3 2.7-6 6-6s6 2.7 6 6" fill="currentColor" opacity="0.75" />
    </svg>
  );
}

interface UploadCardProps {
  title: string;
  accept: string;
  file: File | null;
  onFileSelect: (file: File | null) => void;
  icon: ReactNode;
  processing?: boolean;
}

function UploadCard({
  title,
  accept,
  file,
  onFileSelect,
  icon,
  processing,
}: UploadCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  if (processing) {
    return (
      <div
        className="flex-1 min-h-[260px] md:min-h-[300px] rounded-[42px] bg-[#a7cdc2]
          flex items-center justify-center
          shadow-[inset_0_2px_10px_rgba(255,255,255,0.35),0_6px_18px_rgba(60,90,80,0.12)]"
      >
        <div className="w-28 h-28 text-[#3d6b55] drop-shadow-[0_2px_6px_rgba(40,80,60,0.35)]">
          {icon}
        </div>
      </div>
    );
  }

  return (
    <div
      className={`flex-1 min-h-[260px] md:min-h-[300px] rounded-[28px] bg-white px-8 py-10
        flex flex-col items-center justify-between
        shadow-[inset_6px_6px_14px_rgba(0,0,0,0.10),inset_-3px_-3px_10px_rgba(255,255,255,0.95)]
        border border-black/[0.04]
        ${file ? "outline outline-2 outline-[rgb(111,134,168)]/50" : ""}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => onFileSelect(e.target.files?.[0] ?? null)}
      />
      <div className="flex-1 flex items-center justify-center text-[#3d5a45] w-28 h-28">
        {icon}
      </div>
      <div className="w-full flex flex-col items-center gap-2">
        <AccentButton
          className="w-full max-w-[190px] py-2.5"
          onClick={() => inputRef.current?.click()}
        >
          {title}
        </AccentButton>
        {file && (
          <p
            className="text-[11px] text-slate-600 truncate max-w-full bg-[#f5f5f0] rounded px-2 py-0.5"
            title={file.name}
          >
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
  processing: boolean;
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
  processing,
  error,
  optionsOpen,
  onToggleOptions,
  children,
}: UploadPanelProps) {
  const canSubmit = !!(audioFile && pdfFile && !loading && !processing);

  return (
    <div className="relative w-full max-w-[860px] mx-auto">
      <div className="flex flex-col md:flex-row gap-8 md:gap-10 px-2">
        <UploadCard
          title="Upload record"
          accept=".mp3,.m4a,.wav,.mp4,.webm,audio/*"
          file={audioFile}
          onFileSelect={onAudioSelect}
          icon={<MicIcon className="w-full h-full" />}
          processing={processing}
        />
        <UploadCard
          title="Upload lecture"
          accept=".pdf,application/pdf"
          file={pdfFile}
          onFileSelect={onPdfSelect}
          icon={<LectureIcon className="w-full h-full" />}
          processing={processing}
        />
      </div>

      {!processing && (
        <div className="mt-10 relative flex flex-col sm:flex-row sm:items-start gap-4">
          <div className="flex-1">
            <AccentButton
              onClick={onToggleOptions}
              className="inline-flex items-center gap-0 px-0 overflow-hidden"
            >
              <span className="px-5 py-2.5">customizing</span>
              <span className="px-3 py-2.5 border-l border-black/25 text-[10px] text-white/90">
                {optionsOpen ? "▲" : "▼"}
              </span>
            </AccentButton>

            {optionsOpen && <div className="mt-3">{children}</div>}
          </div>

          <AccentButton
            onClick={onSubmit}
            disabled={!canSubmit}
            className="px-10 py-2.5 self-start sm:ml-auto"
          >
            {loading ? "업로드 중..." : "Done"}
          </AccentButton>
        </div>
      )}

      {error && (
        <p className="mt-4 text-center text-red-600 text-sm bg-red-50 py-2 px-4 rounded-lg border border-red-200">
          {error}
        </p>
      )}
    </div>
  );
}
