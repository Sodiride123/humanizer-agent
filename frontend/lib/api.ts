function getApiBaseUrl(): string {
  if (typeof window !== "undefined") {
    const match = window.location.hostname.match(/^\d+-(.+)$/);
    if (match) return `https://8000-${match[1]}`;
  }
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
}

export const API_URL = getApiBaseUrl();

export interface SentenceResult {
  text: string;
  score: number;
  label: "ai" | "human";
}

export interface AnalysisResult {
  id: string;
  overall_score: number;
  confidence_label: string;
  sentences: SentenceResult[];
  summary: string;
  input_type: string;
  word_count: number;
  source_url?: string;
}

export async function analyzeText(text: string): Promise<AnalysisResult> {
  const res = await fetch(`${getApiBaseUrl()}/api/analyze/text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Analysis failed" }));
    throw new Error(err.detail || "Analysis failed");
  }
  return res.json();
}

export async function analyzeUrl(url: string): Promise<AnalysisResult> {
  const res = await fetch(`${getApiBaseUrl()}/api/extract-url`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "URL analysis failed" }));
    throw new Error(err.detail || "URL analysis failed");
  }
  return res.json();
}

export async function getResult(id: string): Promise<AnalysisResult> {
  const res = await fetch(`${getApiBaseUrl()}/api/results/${id}`);
  if (!res.ok) {
    throw new Error("Result not found");
  }
  return res.json();
}
