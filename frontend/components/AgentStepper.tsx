"use client";

import { AGENT_NAMES } from "@/lib/api";
import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export type AgentStatus = "pending" | "running" | "done" | "error";

type AgentStepperProps = {
  statuses: Record<string, AgentStatus>;
  timings: Record<string, number>;
};

export function AgentStepper({ statuses, timings }: AgentStepperProps) {
  return (
    <Card>
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-zinc-400">
        Agent pipeline
      </h2>
      <ol className="space-y-3">
        {AGENT_NAMES.map((name) => {
          const status = statuses[name] ?? "pending";
          const elapsed = timings[name];
          return (
            <li
              key={name}
              className="flex items-center justify-between gap-3 rounded-lg border border-zinc-800 bg-zinc-950/60 px-3 py-2"
            >
              <div className="min-w-0">
                <p className="truncate font-mono text-sm text-zinc-200">{name}</p>
                {elapsed !== undefined && (
                  <p className="text-xs text-zinc-500">{elapsed.toFixed(1)}s</p>
                )}
              </div>
              <Badge
                tone={
                  status === "done"
                    ? "ok"
                    : status === "running"
                      ? "running"
                      : status === "error"
                        ? "warn"
                        : "neutral"
                }
              >
                {status}
              </Badge>
            </li>
          );
        })}
      </ol>
    </Card>
  );
}
