"use client";

import { Card } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import type { SetupResponse } from "@/lib/api";

type SetupPanelProps = {
  setup: SetupResponse | null;
  loading: boolean;
  error: string | null;
};

export function SetupPanel({ setup, loading, error }: SetupPanelProps) {
  return (
    <Card>
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-400">
          Setup status
        </h2>
        {loading && <Badge tone="running">Checking…</Badge>}
        {!loading && setup?.ready && <Badge tone="ok">Ready</Badge>}
        {!loading && setup && !setup.ready && <Badge tone="warn">Blocked</Badge>}
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {!loading && setup && setup.issues.length === 0 && (
        <p className="text-sm text-emerald-300">
          All prerequisites met for {setup.ticker}.
        </p>
      )}

      {!loading && setup && setup.issues.length > 0 && (
        <ul className="space-y-2 text-sm text-amber-200/90">
          {setup.issues.map((issue) => (
            <li key={issue} className="flex gap-2">
              <span className="text-amber-500">•</span>
              <span>{issue}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
