const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type SetupResponse = {
  ready: boolean;
  issues: string[];
  ticker: string;
};

export type SSEEvent =
  | { type: "agent_start"; agent: string }
  | { type: "agent_done"; agent: string; elapsed_sec: number }
  | {
      type: "complete";
      report: string;
      timings: Record<string, number>;
      saved_path: string;
    }
  | { type: "error"; message: string };

export const AGENT_NAMES = [
  "Agent 1 — Extraction",
  "Agent 2 — Quant model",
  "Agent 3 — Narrative drift",
  "Agent 4 — Market fingerprint",
  "Agent 5 — Analog search",
  "Agent 6 — Synthesis",
] as const;

export function getApiUrl(): string {
  return API_URL;
}

export async function fetchSetup(ticker: string): Promise<SetupResponse> {
  const res = await fetch(
    `${API_URL}/setup?ticker=${encodeURIComponent(ticker)}`,
    { cache: "no-store" },
  );
  if (!res.ok) {
    throw new Error(`Setup check failed (${res.status})`);
  }
  return res.json();
}

export function streamAnalysis(
  ticker: string,
  onEvent: (event: SSEEvent) => void,
): () => void {
  const url = `${API_URL}/analyze/${encodeURIComponent(ticker)}/stream`;
  const source = new EventSource(url);

  source.onmessage = (message) => {
    try {
      const data = JSON.parse(message.data) as SSEEvent;
      onEvent(data);
      if (data.type === "complete" || data.type === "error") {
        source.close();
      }
    } catch {
      onEvent({ type: "error", message: "Invalid SSE payload from server" });
      source.close();
    }
  };

  source.onerror = () => {
    onEvent({
      type: "error",
      message:
        "Connection lost. Ensure the API is running (uvicorn api.main:app --port 8000).",
    });
    source.close();
  };

  return () => source.close();
}
