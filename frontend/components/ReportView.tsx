"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Card } from "@/components/ui/Card";

type ReportViewProps = {
  report: string;
  savedPath?: string;
  totalSeconds?: number;
};

export function ReportView({ report, savedPath, totalSeconds }: ReportViewProps) {
  return (
    <Card className="prose prose-invert max-w-none prose-headings:text-zinc-100 prose-p:text-zinc-300 prose-strong:text-zinc-100 prose-li:text-zinc-300">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-zinc-800 pb-4 not-prose">
        <h2 className="text-lg font-semibold text-zinc-100">Analysis report</h2>
        <div className="flex flex-wrap gap-3 text-xs text-zinc-500">
          {totalSeconds !== undefined && (
            <span>Total: {totalSeconds.toFixed(0)}s</span>
          )}
          {savedPath && <span className="font-mono">{savedPath}</span>}
        </div>
      </div>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{report}</ReactMarkdown>
    </Card>
  );
}
