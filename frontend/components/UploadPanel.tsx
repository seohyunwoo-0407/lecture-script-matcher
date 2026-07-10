"use client";

import { useRef } from "react";

interface UploadCardProps {
  title: string;
  subtitle: string;
  accept: string;
  file: File | null;
  onFileSelect: (file: File | null) => void;
  icon: string;
}

function UploadCard({
  title,
  subtitle,
  accept,
  file,
  onFileSelect,
  icon,
}: UploadCardProps) {
  const inputRef = useRef<HTMLInputElement>(null);

  return (
    <div
      onClick={() => inputRef.current?.click()}
      className={`flex-1 min-h-[200px] rounded-2xl border-2 border-dashed cursor-pointer transition-all
        ${file ? "border-brand-500 bg-brand-50" : "border-slate-300 bg-white hover:border-brand-400 hover:bg-slate-50"}
        flex flex-col items-center justify-center p-8 shadow-sm`}
    >
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        className="hidden"
        onChange={(e) => onFileSelect(e.target.files?.[0] ?? null)}
      />
      <span className="text-4xl mb-3">{icon}</span>
      <h3 className="text-lg font-semibold text-slate-800">{title}</h3>
      <p className="text-sm text-slate-500 mt-1">{subtitle}</p>
      {file && (
        <p className="mt-4 text-sm font-medium text-brand-700 bg-white px-3 py-1 rounded-full">
          {file.name}
        </p>
      )}
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
  children?: React.ReactNode;
}

export default function UploadPanel({
  audioFile,
  pdfFile,
  onAudioSelect,
  onPdfSelect,
  onSubmit,
  loading,
  error,
  children,
}: UploadPanelProps) {
  const canSubmit = audioFile && pdfFile && !loading;

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row gap-6">
        <UploadCard
          title="Upload record"
          subtitle="mp3, m4a, wav, mp4, webm"
          accept=".mp3,.m4a,.wav,.mp4,.webm,audio/*"
          file={audioFile}
          onFileSelect={onAudioSelect}
          icon="🎙️"
        />
        <UploadCard
          title="Upload lecture"
          subtitle="PDF 강의록"
          accept=".pdf,application/pdf"
          file={pdfFile}
          onFileSelect={onPdfSelect}
          icon="📄"
        />
      </div>

      {children}

      {error && (
        <p className="text-center text-red-600 text-sm bg-red-50 py-2 px-4 rounded-lg">
          {error}
        </p>
      )}

      <div className="flex justify-center">
        <button
          onClick={onSubmit}
          disabled={!canSubmit}
          className={`px-10 py-3 rounded-xl font-semibold text-white transition-all
            ${canSubmit ? "bg-brand-600 hover:bg-brand-700 shadow-lg shadow-brand-200" : "bg-slate-300 cursor-not-allowed"}`}
        >
          {loading ? "업로드 중..." : "Done"}
        </button>
      </div>
    </div>
  );
}
