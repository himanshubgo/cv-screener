import type { HealthInfo, Scorecard } from "./types";

interface ScreenTextResponse {
  id: string;
  filename: string;
  status: "ok" | "error";
  card?: Scorecard;
  error?: string;
}

export async function fetchHealth(): Promise<HealthInfo> {
  const res = await fetch("/api/health");
  if (!res.ok) throw new Error(`health check failed: ${res.status}`);
  return res.json();
}

/** Screen one CV's raw text against the agent. Never throws for a screening
 * failure - a non-"ok" status/error string comes back instead - so the caller
 * can show that one candidate failed without losing the rest of the batch. */
export async function screenText(filename: string, cvText: string): Promise<ScreenTextResponse> {
  try {
    const res = await fetch("/api/screen-text", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ filename, cv_text: cvText }),
    });
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      return { id: filename, filename, status: "error", error: `request failed (${res.status}): ${detail}` };
    }
    return await res.json();
  } catch (e) {
    return {
      id: filename,
      filename,
      status: "error",
      error: e instanceof Error ? e.message : "network error",
    };
  }
}

export function readFileAsText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result ?? ""));
    reader.onerror = () => reject(reader.error ?? new Error(`could not read ${file.name}`));
    reader.readAsText(file);
  });
}
