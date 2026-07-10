"use client";

export type JobPhase = "queued" | "transcribe" | "matching" | "polish" | "done";

interface ProgressBarProps {
  message: string;
  transcribeProgress: number;
  matchingProgress: number;
  phase?: JobPhase;
}

function PhaseBar({
  label,
  icon,
  progress,
  active,
  done,
}: {
  label: string;
  icon: string;
  progress: number;
  active: boolean;
  done: boolean;
}) {
  const clamped = Math.min(100, Math.max(0, progress));

  return (
    <div
      className={`rounded-xl border p-4 transition-all ${
        active
          ? "border-brand-300 bg-brand-50/60 shadow-sm"
          : done
            ? "border-emerald-200 bg-emerald-50/40"
            : "border-slate-200 bg-white"
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">{icon}</span>
          <span
            className={`text-sm font-medium ${
              active ? "text-brand-700" : done ? "text-emerald-700" : "text-slate-500"
            }`}
          >
            {label}
          </span>
          {done && (
            <span className="text-xs text-emerald-600 bg-emerald-100 px-1.5 py-0.5 rounded">
              완료
            </span>
          )}
          {active && (
            <span className="text-xs text-brand-600 bg-brand-100 px-1.5 py-0.5 rounded animate-pulse">
              진행 중
            </span>
          )}
        </div>
        <span className="text-sm tabular-nums text-slate-500">{clamped}%</span>
      </div>
      <div className="h-2.5 bg-slate-200 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-500 ease-out ${
            done ? "bg-emerald-500" : active ? "bg-brand-600" : "bg-slate-300"
          }`}
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}

export default function ProgressBar({
  message,
  transcribeProgress,
  matchingProgress,
  phase = "queued",
}: ProgressBarProps) {
  const transcribeDone = transcribeProgress >= 100;
  const matchingDone = matchingProgress >= 100;
  const transcribeActive = phase === "transcribe";
  const matchingActive = phase === "matching" || phase === "polish";

  return (
    <div className="w-full max-w-lg mx-auto space-y-4">
      <p className="text-center text-sm text-slate-600">{message}</p>

      <PhaseBar
        label="음성 → 텍스트 변환"
        icon="🎙️"
        progress={transcribeProgress}
        active={transcribeActive}
        done={transcribeDone}
      />

      <PhaseBar
        label="텍스트 → 슬라이드 매칭"
        icon="📄"
        progress={matchingProgress}
        active={matchingActive}
        done={matchingDone}
      />
    </div>
  );
}
