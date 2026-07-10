"use client";

interface SummaryPanelProps {
  summary: string[];
  hasScripts: boolean;
  title?: string;
  subtitle?: string;
}

function renderPoint(point: string, idx: number) {
  const important = point.includes("⭐") || point.includes("중요");
  const clean = point.replace(/^[-•*]\s*/, "");
  const isExample = clean.startsWith("예)");
  return (
    <li
      key={idx}
      className={`flex gap-2 leading-relaxed ${
        important ? "text-slate-900 font-medium" : "text-slate-700"
      } ${isExample ? "pl-2 border-l-2 border-amber-300 bg-amber-50/60 py-1.5 pr-2 rounded-r" : ""}`}
    >
      <span className="mt-1.5 shrink-0 w-1.5 h-1.5 rounded-full bg-brand-500" />
      <span>
        {isExample && (
          <span className="text-xs font-semibold text-amber-700 mr-1">예시</span>
        )}
        {clean}
      </span>
    </li>
  );
}

export default function SummaryPanel({
  summary,
  hasScripts,
  title = "핵심 정리",
  subtitle = "교수님 설명·예시 요약",
}: SummaryPanelProps) {
  return (
    <div className="flex flex-col h-full">
      <h2 className="text-sm font-semibold text-slate-600 mb-3 px-1 flex items-center gap-2">
        <span>{title}</span>
        <span className="text-xs font-normal text-slate-400">{subtitle}</span>
      </h2>
      <div className="flex-1 rounded-xl border border-brand-100 bg-brand-50/40 p-5 overflow-y-auto min-h-[500px]">
        {summary && summary.length > 0 ? (
          <ul className="space-y-3">{summary.map(renderPoint)}</ul>
        ) : (
          <div className="text-center py-12 px-4">
            <p className="text-3xl mb-3">📝</p>
            <p className="text-slate-500 font-medium">정리할 내용이 없습니다</p>
            <p className="text-slate-400 text-sm mt-2 leading-relaxed">
              {hasScripts
                ? "요약 모드가 꺼져 있거나, 이 슬라이드에서 정리할 핵심 발화를 찾지 못했습니다."
                : "이 슬라이드에는 매칭된 교수님 발화가 없습니다."}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
