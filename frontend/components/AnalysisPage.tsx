"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  AGENT_NAMES,
  fetchSetup,
  streamAnalysis,
  type SetupResponse,
  type SSEEvent,
} from "@/lib/api";
import { TickerForm } from "@/components/TickerForm";
import { SetupPanel } from "@/components/SetupPanel";
import { AgentStepper, type AgentStatus } from "@/components/AgentStepper";
import { ReportView } from "@/components/ReportView";

const initialStatuses = (): Record<string, AgentStatus> =>
  Object.fromEntries(AGENT_NAMES.map((name) => [name, "pending"])) as Record<
    string,
    AgentStatus
  >;

export function AnalysisPage() {
  const [ticker, setTicker] = useState("AAPL");
  const [setup, setSetup] = useState<SetupResponse | null>(null);
  const [setupLoading, setSetupLoading] = useState(false);
  const [setupError, setSetupError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [statuses, setStatuses] = useState(initialStatuses);
  const [timings, setTimings] = useState<Record<string, number>>({});
  const [report, setReport] = useState<string | null>(null);
  const [savedPath, setSavedPath] = useState<string | null>(null);
  const [rejections, setRejections] = useState<Array<Record<string, unknown>>>([]);
  const [runError, setRunError] = useState<string | null>(null);
  const [runStartedAt, setRunStartedAt] = useState<number | null>(null);

  const loadSetup = useCallback(async (symbol: string) => {
    if (!symbol.trim()) return;
    setSetupLoading(true);
    setSetupError(null);
    try {
      const data = await fetchSetup(symbol.trim());
      setSetup(data);
    } catch (err) {
      setSetupError(err instanceof Error ? err.message : "Setup check failed");
      setSetup(null);
    } finally {
      setSetupLoading(false);
    }
  }, []);

  useEffect(() => {
    const handle = setTimeout(() => loadSetup(ticker), 300);
    return () => clearTimeout(handle);
  }, [ticker, loadSetup]);

  const totalSeconds = useMemo(() => {
    const values = Object.values(timings);
    if (!values.length) return undefined;
    return values.reduce((a, b) => a + b, 0);
  }, [timings]);

  const handleRun = () => {
    const symbol = ticker.trim().toUpperCase();
    if (!symbol || running) return;

    if (setup && !setup.ready) {
      setRunError("Fix setup issues before running analysis.");
      return;
    }

    setRunning(true);
    setRunError(null);
    setReport(null);
    setSavedPath(null);
    setRejections([]);
    setTimings({});
    setStatuses(initialStatuses());
    setRunStartedAt(Date.now());

    streamAnalysis(symbol, (event: SSEEvent) => {
      if (event.type === "agent_start") {
        setStatuses((prev) => ({ ...prev, [event.agent]: "running" }));
      } else if (event.type === "agent_done") {
        setStatuses((prev) => ({ ...prev, [event.agent]: "done" }));
        setTimings((prev) => ({ ...prev, [event.agent]: event.elapsed_sec }));
      } else if (event.type === "complete") {
        setReport(event.report);
        setSavedPath(event.saved_path);
        setRejections(event.rejections ?? []);
        setTimings(event.timings);
        setRunning(false);
      } else if (event.type === "error") {
        setRunError(event.message);
        setStatuses((prev) => {
          const next = { ...prev };
          for (const name of AGENT_NAMES) {
            if (next[name] === "running") next[name] = "error";
          }
          return next;
        });
        setRunning(false);
      }
    });
  };

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-4 py-8">
      <header className="space-y-2">
        <p className="font-mono text-xs uppercase tracking-[0.2em] text-emerald-500">
          Quant · Rapid Agent Hackathon
        </p>
        <h1 className="text-3xl font-semibold text-zinc-50">
          Agentic earnings intelligence
        </h1>
        <p className="max-w-2xl text-sm text-zinc-400">
          Six-agent pipeline: SEC extraction, quant model, narrative drift, macro
          fingerprint, historical analog search, and synthesis.
        </p>
      </header>

      <TickerForm
        ticker={ticker}
        running={running}
        onTickerChange={setTicker}
        onRun={handleRun}
      />

      {runError && (
        <div className="rounded-lg border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-300">
          {runError}
        </div>
      )}

      {rejections.length > 0 && (
        <div className="rounded-lg border border-amber-900/60 bg-amber-950/30 px-4 py-3 text-sm text-amber-200">
          <p className="font-medium text-amber-100">Grader rejected Agent 2 and retried</p>
          <ul className="mt-2 list-inside list-disc text-amber-200/90">
            {rejections.map((entry, index) => (
              <li key={index}>{String(entry.reason ?? JSON.stringify(entry))}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <div className="space-y-6">
          <SetupPanel setup={setup} loading={setupLoading} error={setupError} />
          <AgentStepper statuses={statuses} timings={timings} />
        </div>

        <div className="min-h-[320px]">
          {report ? (
            <ReportView
              report={report}
              savedPath={savedPath ?? undefined}
              totalSeconds={
                runStartedAt
                  ? (Date.now() - runStartedAt) / 1000
                  : totalSeconds
              }
            />
          ) : (
            <div className="flex h-full min-h-[320px] items-center justify-center rounded-xl border border-dashed border-zinc-800 bg-zinc-900/40 p-8 text-center text-sm text-zinc-500">
              {running
                ? "Agents are running… this usually takes about 2 minutes."
                : "Run analysis to generate a four-section report."}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
