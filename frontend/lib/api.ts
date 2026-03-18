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

export async function analyzeFile(file: File): Promise<AnalysisResult> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${getApiBaseUrl()}/api/upload-file`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "File analysis failed" }));
    throw new Error(err.detail || "File analysis failed");
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
  image_type: string;  // photograph, graphic_design, illustration, ui_screenshot, mixed
  filename: string;
  image_url: string;   // relative URL e.g. /api/images/original_xxx.png
  image_mime: string;
  input_type: "image";
}

export interface ImageHumanizeResult {
  result_id: string;
  original_score: number;
  new_score: number;
  improvement: number;
  humanized_image_url: string;  // relative URL e.g. /api/images/humanized_xxx.png
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
  // Step 1: start the background job
  const startRes = await fetch(`${getApiBaseUrl()}/api/humanize/image`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ result_id: resultId }),
  });
  if (!startRes.ok) {
    const err = await startRes.json().catch(() => ({ detail: "Image humanization failed" }));
    throw new Error(err.detail || "Image humanization failed");
  }
  const { job_id } = await startRes.json();

  // Step 2: poll until done (every 3s, max 3 minutes)
  const maxAttempts = 60;
  for (let i = 0; i < maxAttempts; i++) {
    await new Promise((r) => setTimeout(r, 3000));
    const pollRes = await fetch(`${getApiBaseUrl()}/api/humanize/image/status/${job_id}`);
    if (!pollRes.ok) {
      const err = await pollRes.json().catch(() => ({ detail: "Humanization failed" }));
      throw new Error(err.detail || "Humanization failed");
    }
    const data = await pollRes.json();
    if (data.status === "done") return data.result as ImageHumanizeResult;
    if (data.status === "error") throw new Error(data.error || "Humanization failed");
    // still processing — continue polling
  }
  throw new Error("Image humanization timed out. Please try again.");
}

export async function getImageResult(id: string): Promise<ImageAnalysisResult> {
  const res = await fetch(`${getApiBaseUrl()}/api/results/image/${id}`);
  if (!res.ok) throw new Error("Result not found");
  return res.json();
}
