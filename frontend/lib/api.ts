// Use relative URLs — Next.js rewrites proxy /api/* to backend on port 8000
// This eliminates CORS issues since everything goes through the same origin
function getApiBaseUrl(): string {
  return "";
}

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

export interface HumanizeChange {
  original: string;
  rewritten: string;
  technique?: string;
}

export interface HumanizeResult {
  original: string;
  humanized: string;
  changes: HumanizeChange[];
  result_id: string;
  original_score?: number;
  new_score?: number;
  improvement?: number;
  iteration?: number;
}

export async function humanizeText(
  text: string,
  resultId?: string,
  iteration?: number
): Promise<HumanizeResult> {
  const res = await fetch(`${getApiBaseUrl()}/api/humanize`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, result_id: resultId, iteration: iteration || 1 }),
  });
  if (!res.ok) {
    const err = await res
      .json()
      .catch(() => ({ detail: "Humanization failed" }));
    throw new Error(err.detail || "Humanization failed");
  }
  return res.json();
}

// --- Image types ---

export interface ImageAnalysisResult {
  id: string;
  overall_score: number;
  confidence_label: string;
  patterns_found: string[];
  summary: string;
  description: string;
  filename: string;
  image_data: string;
  image_mime: string;
  input_type: "image";
}

export interface ImageHumanizeResult {
  result_id: string;
  original_score: number;
  new_score: number;
  improvement: number;
  humanized_image_url: string;
  humanized_image_data: string;
  prompt_used: string;
  changes_summary: string;
}

export async function analyzeImage(file: File): Promise<ImageAnalysisResult> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${getApiBaseUrl()}/api/analyze/image`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Image analysis failed" }));
    throw new Error(err.detail || "Image analysis failed");
  }
  return res.json();
}

export async function humanizeImage(resultId: string): Promise<ImageHumanizeResult> {
  const formData = new FormData();
  formData.append("result_id", resultId);
  const res = await fetch(`${getApiBaseUrl()}/api/humanize/image`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Image humanization failed" }));
    throw new Error(err.detail || "Image humanization failed");
  }
  return res.json();
}

export async function getImageResult(id: string): Promise<ImageAnalysisResult> {
  const res = await fetch(`${getApiBaseUrl()}/api/results/image/${id}`);
  if (!res.ok) throw new Error("Result not found");
  return res.json();
}
