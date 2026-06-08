"use client";

import { Button } from "@/components/ui/Button";

type TickerFormProps = {
  ticker: string;
  running: boolean;
  onTickerChange: (value: string) => void;
  onRun: () => void;
};

export function TickerForm({
  ticker,
  running,
  onTickerChange,
  onRun,
}: TickerFormProps) {
  return (
    <form
      className="flex flex-wrap items-end gap-3"
      onSubmit={(e) => {
        e.preventDefault();
        onRun();
      }}
    >
      <label className="flex flex-col gap-1.5">
        <span className="text-xs font-medium uppercase tracking-wide text-zinc-400">
          Ticker
        </span>
        <input
          value={ticker}
          onChange={(e) => onTickerChange(e.target.value.toUpperCase())}
          className="w-40 rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 font-mono text-lg text-zinc-100 outline-none ring-emerald-500/0 transition focus:ring-2"
          placeholder="AAPL"
          maxLength={8}
          disabled={running}
        />
      </label>
      <Button type="submit" disabled={running || !ticker.trim()}>
        {running ? "Running analysis…" : "Run analysis"}
      </Button>
    </form>
  );
}
