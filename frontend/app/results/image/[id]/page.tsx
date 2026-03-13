"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  getImageResult,
  humanizeImage,
  ImageAnalysisResult,
  ImageHumanizeResult,
} from "@/lib/api";

function getGaugeColor(score: number): string {
  if (score >= 60) return "#ef4444";
  if (score >= 30) return "#f59e0b";
  return "#10b981";
}

function getGaugeGradient(score: number): [string, string] {
  if (score >= 60) return ["#ef4444", "#ff6b6b"];
  if (score >= 30) return ["#f59e0b", "#fbbf24"];
  return ["#10b981", "#4ecdc4"];
}

function ScoreGauge({ score }: { score: number }) {
  const circumference = 2 * Math.PI * 100;
  const offset = circumference - (score / 100) * circumference;
  const [c1, c2] = getGaugeGradient(score);

  return (
    <div className="relative w-52 h-52">
      <svg width="208" height="208" viewBox="0 0 208 208" className="transform -rotate-90">
        <circle cx="104" cy="104" r="88" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="14" />
        <defs>
          <linearGradient id="img-gauge-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={c1} />
            <stop offset="100%" stopColor={c2} />
          </linearGradient>
        </defs>
        <circle
          cx="104" cy="104" r="88" fill="none"
          stroke="url(#img-gauge-gradient)" strokeWidth="14"
          strokeDasharray={circumference * (88 / 100)}
          strokeDashoffset={(circumference * (88 / 100)) - (score / 100) * (circumference * (88 / 100))}
          strokeLinecap="round"
          className="transition-all duration-[800ms] ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[46px] font-bold text-white leading-none">
          {Math.round(score)}%
        </span>
        <span className="text-sm font-medium mt-1" style={{ color: "var(--text-secondary)" }}>
          AI Detected
        </span>
      </div>
    </div>
  );
}

// Pattern descriptions for the 20 visual AI patterns
const PATTERN_LABELS: Record<string, string> = {
  texture_soup: "Texture Soup",
  perfect_symmetry: "Perfect Symmetry",
  uncanny_smoothness: "Uncanny Smoothness",
  repetitive_patterns: "Repetitive Patterns",
  inconsistent_lighting: "Inconsistent Lighting",
  impossible_reflections: "Impossible Reflections",
  malformed_hands: "Malformed Hands",
  text_gibberish: "Text Gibberish",
  ear_deformity: "Ear Deformity",
  jewellery_artifacts: "Jewellery Artifacts",
  background_incoherence: "Background Incoherence",
  floating_elements: "Floating Elements",
  painterly_haze: "Painterly Haze",
  oversaturation: "Oversaturation",
  dramatic_lighting: "Dramatic Lighting",
  stock_photo_composition: "Stock Photo Composition",
  generic_aesthetic: "Generic Aesthetic",
  depth_of_field_abuse: "Depth of Field Abuse",
  no_exif_noise: "No EXIF / Noise",
  watermark_remnants: "Watermark Remnants",
};

const PATTERN_CATEGORIES: Record<string, string[]> = {
  "Texture & Detail": ["texture_soup", "perfect_symmetry", "uncanny_smoothness", "repetitive_patterns", "inconsistent_lighting", "impossible_reflections"],
  "Structural": ["malformed_hands", "text_gibberish", "ear_deformity", "jewellery_artifacts", "background_incoherence", "floating_elements"],
  "Style & Composition": ["painterly_haze", "oversaturation", "dramatic_lighting", "stock_photo_composition", "generic_aesthetic", "depth_of_field_abuse"],
  "Metadata": ["no_exif_noise", "watermark_remnants"],
};

export default function ImageResultPage() {
  const params = useParams();
  const router = useRouter();
  const [result, setResult] = useState<ImageAnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [humanizing, setHumanizing] = useState(false);
  const [humanized, setHumanized] = useState<ImageHumanizeResult | null>(null);
  const [humanizeError, setHumanizeError] = useState("");
  const [showPrompt, setShowPrompt] = useState(false);
  const [downloadReady, setDownloadReady] = useState(false);

  useEffect(() => {
    const id = params.id as string;
    const cached = sessionStorage.getItem(`img-result-${id}`);
    if (cached) {
      setResult(JSON.parse(cached));
      setLoading(false);
      return;
    }
    getImageResult(id)
      .then(setResult)
      .catch(() => setError("Result not found"))
      .finally(() => setLoading(false));
  }, [params.id]);

  const handleHumanize = async () => {
    if (!result) return;
    setHumanizeError("");
    setHumanizing(true);
    try {
      const res = await humanizeImage(result.id);
      setHumanized(res);
      setDownloadReady(true);
    } catch (e) {
      setHumanizeError(e instanceof Error ? e.message : "Humanization failed");
    } finally {
      setHumanizing(false);
    }
  };

  const handleDownload = () => {
    if (!humanized) return;
    const link = document.createElement("a");
    link.href = humanized.humanized_image_url;
    link.download = "humanized_image.png";
    link.target = "_blank";
    link.click();
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-primary)" }}>
        <div className="text-center">
          <svg className="animate-spin h-10 w-10 mx-auto mb-4" style={{ color: "var(--accent-action)" }} viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"/>
            <path d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" fill="currentColor" className="opacity-75"/>
          </svg>
          <p style={{ color: "var(--text-secondary)" }}>Analysing image...</p>
        </div>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-primary)" }}>
        <div className="text-center">
          <p style={{ color: "var(--accent-ai)" }} className="mb-4">{error || "Result not found"}</p>
          <button onClick={() => router.push("/")} style={{ color: "var(--accent-action)" }} className="font-medium">
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  const patternsFound = result.patterns_found || [];

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--bg-primary)" }}>
      {/* Nav */}
      <header className="h-16 flex items-center px-6" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
        <div className="max-w-[1200px] mx-auto w-full flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-white" style={{ background: "var(--accent-action)" }}>
              H
            </div>
            <span className="text-xl font-bold text-white">Humaniser</span>
          </div>
          <button
            onClick={() => router.push("/")}
            className="text-sm font-medium flex items-center gap-1"
            style={{ color: "var(--accent-action)" }}
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M10 4L6 8l4 4" stroke="currentColor" strokeWidth="2"/>
            </svg>
            New Analysis
          </button>
        </div>
      </header>

      {/* Breadcrumb */}
      <div className="max-w-[1200px] mx-auto w-full px-6 pt-4">
        <div className="flex items-center gap-2 text-sm">
          <button onClick={() => router.push("/")} style={{ color: "var(--text-secondary)" }} className="hover:text-white">Home</button>
          <span style={{ color: "var(--text-secondary)" }}>&gt;</span>
          <span style={{ color: "var(--text-secondary)" }}>Image Results</span>
          <span style={{ color: "var(--text-secondary)" }}>&gt;</span>
          <span className="text-white truncate max-w-[200px]">{result.filename}</span>
        </div>
      </div>

      <main className="flex-1 max-w-[1200px] mx-auto px-6 py-6 w-full">
        {/* Top row: score + image side by side */}
        <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-6 mb-6">

          {/* Left: Score + patterns */}
          <div className="space-y-4">
            {/* Score card */}
            <div className="rounded-xl p-6 flex flex-col items-center" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)" }}>
              <h2 className="text-xl font-bold text-white mb-4">Image Analysis</h2>
              <ScoreGauge score={result.overall_score} />
              <p className="mt-3 text-lg font-semibold" style={{ color: getGaugeColor(result.overall_score) }}>
                {result.confidence_label}
              </p>
              <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
                {patternsFound.length} AI pattern{patternsFound.length !== 1 ? "s" : ""} detected
              </p>
            </div>

            {/* Summary */}
            <div className="rounded-xl p-4" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)" }}>
              <h3 className="text-sm font-semibold text-white mb-2">Summary</h3>
              <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{result.summary}</p>
            </div>

            {/* Description */}
            {result.description && (
              <div className="rounded-xl p-4" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)" }}>
                <h3 className="text-sm font-semibold text-white mb-2">Image Description</h3>
                <p className="text-sm leading-relaxed italic" style={{ color: "var(--text-secondary)" }}>{result.description}</p>
              </div>
            )}
          </div>

          {/* Right: Original image + detected patterns */}
          <div className="space-y-4">
            {/* Original image */}
            <div className="rounded-xl overflow-hidden" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)" }}>
              <div className="px-4 pt-4 pb-2 flex items-center justify-between">
                <h3 className="text-base font-semibold text-white">Original Image</h3>
                <span className="text-xs px-2 py-1 rounded-full font-medium"
                  style={{
                    background: result.overall_score >= 60 ? "rgba(239,68,68,0.15)" : result.overall_score >= 30 ? "rgba(245,158,11,0.15)" : "rgba(16,185,129,0.15)",
                    color: getGaugeColor(result.overall_score),
                  }}>
                  {result.overall_score >= 60 ? "Likely AI" : result.overall_score >= 30 ? "Uncertain" : "Likely Human"}
                </span>
              </div>
              <div className="px-4 pb-4">
                <img
                  src={`data:${result.image_mime};base64,${result.image_data}`}
                  alt="Uploaded image"
                  className="w-full rounded-lg object-contain max-h-[400px]"
                  style={{ background: "var(--bg-primary)" }}
                />
              </div>
            </div>

            {/* Detected patterns by category */}
            {patternsFound.length > 0 && (
              <div className="rounded-xl p-4" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)" }}>
                <h3 className="text-base font-semibold text-white mb-3">Detected AI Patterns</h3>
                <div className="space-y-3">
                  {Object.entries(PATTERN_CATEGORIES).map(([category, patternKeys]) => {
                    const found = patternKeys.filter(k => patternsFound.includes(k));
                    if (found.length === 0) return null;
                    return (
                      <div key={category}>
                        <p className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-secondary)" }}>
                          {category}
                        </p>
                        <div className="flex flex-wrap gap-2">
                          {found.map(k => (
                            <span key={k} className="text-xs px-2 py-1 rounded-full"
                              style={{ background: "rgba(239,68,68,0.12)", color: "var(--accent-ai)", border: "1px solid rgba(239,68,68,0.2)" }}>
                              {PATTERN_LABELS[k] || k.replace(/_/g, " ")}
                            </span>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {patternsFound.length === 0 && (
              <div className="rounded-xl p-4" style={{ background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)" }}>
                <p className="text-sm" style={{ color: "var(--accent-human)" }}>
                  ✓ No significant AI patterns detected. This image appears to be human-created.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Humanise Section */}
        <div className="mt-2">
          {!humanized ? (
            <div className="text-center">
              <p className="text-sm mb-4" style={{ color: "var(--text-secondary)" }}>
                {result.overall_score >= 30
                  ? "Regenerate this image with a less AI-looking aesthetic — natural imperfections, authentic lighting, organic composition."
                  : "This image already looks fairly human, but you can still regenerate it in a more authentic style."}
              </p>
              <button
                onClick={handleHumanize}
                disabled={humanizing}
                className="w-full max-w-[480px] h-[60px] rounded-xl text-xl font-semibold text-white transition-all flex items-center justify-center gap-2 mx-auto disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ background: "var(--accent-action)" }}
                onMouseEnter={(e) => {
                  if (!humanizing) e.currentTarget.style.boxShadow = "0 4px 24px rgba(108,92,231,0.5)";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.boxShadow = "none";
                }}
              >
                {humanizing ? (
                  <span className="flex items-center gap-2">
                    <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"/>
                      <path d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" fill="currentColor" className="opacity-75"/>
                    </svg>
                    Regenerating Image...
                  </span>
                ) : (
                  <>
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                      <rect x="2" y="4" width="16" height="12" rx="2" stroke="currentColor" strokeWidth="1.8" fill="none"/>
                      <circle cx="7" cy="8" r="2" stroke="currentColor" strokeWidth="1.5" fill="none"/>
                      <path d="M2 14l5-4 3.5 3 3-2.5 4.5 3.5" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round"/>
                    </svg>
                    Regenerate as Less-AI Image
                  </>
                )}
              </button>
              {humanizeError && (
                <div className="mt-4 p-3 rounded-lg text-sm max-w-[480px] mx-auto"
                  style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)", color: "var(--accent-ai)" }}>
                  {humanizeError}
                </div>
              )}
            </div>
          ) : (
            <div className="rounded-xl p-6" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)" }}>
              {/* Score progression */}
              <div className="mb-6 p-4 rounded-lg flex items-center justify-between flex-wrap gap-3"
                style={{
                  background: humanized.new_score < 30 ? "rgba(16,185,129,0.08)" : "rgba(108,92,231,0.08)",
                  border: `1px solid ${humanized.new_score < 30 ? "rgba(16,185,129,0.2)" : "rgba(108,92,231,0.2)"}`,
                }}>
                <div className="flex items-center gap-3">
                  <span className="text-2xl font-bold" style={{ color: getGaugeColor(humanized.original_score) }}>
                    {humanized.original_score}%
                  </span>
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                    <path d="M4 10h12M13 6l4 4-4 4" stroke="var(--text-secondary)" strokeWidth="1.8" strokeLinecap="round"/>
                  </svg>
                  <span className="text-2xl font-bold" style={{ color: getGaugeColor(humanized.new_score) }}>
                    {humanized.new_score}%
                  </span>
                  {humanized.improvement > 0 && (
                    <span className="text-sm font-medium px-2 py-0.5 rounded-full"
                      style={{ background: "rgba(16,185,129,0.15)", color: "var(--accent-human)" }}>
                      −{humanized.improvement}pt
                    </span>
                  )}
                </div>
                {humanized.new_score < 30 ? (
                  <span className="text-sm font-medium px-3 py-1 rounded-full flex items-center gap-1"
                    style={{ background: "rgba(16,185,129,0.15)", color: "var(--accent-human)" }}>
                    <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                      <path d="M3 7l3 3 5-6" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                    </svg>
                    Looks Human!
                  </span>
                ) : (
                  <span className="text-sm" style={{ color: "var(--text-secondary)" }}>
                    AI score reduced
                  </span>
                )}
              </div>

              {/* Side-by-side images */}
              <h3 className="text-lg font-semibold text-white mb-4">Before & After</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                <div className="rounded-lg overflow-hidden" style={{ border: "1px solid var(--border-subtle)" }}>
                  <div className="px-3 py-2 flex items-center justify-between" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                    <span className="text-xs font-medium" style={{ color: "var(--accent-ai)" }}>Original (AI-generated)</span>
                    <span className="text-xs" style={{ color: "var(--text-secondary)" }}>{humanized.original_score}% AI</span>
                  </div>
                  <img
                    src={`data:${result.image_mime};base64,${result.image_data}`}
                    alt="Original"
                    className="w-full object-contain max-h-[320px]"
                    style={{ background: "var(--bg-primary)" }}
                  />
                </div>
                <div className="rounded-lg overflow-hidden" style={{ border: "1px solid rgba(16,185,129,0.3)" }}>
                  <div className="px-3 py-2 flex items-center justify-between" style={{ borderBottom: "1px solid rgba(16,185,129,0.2)" }}>
                    <span className="text-xs font-medium" style={{ color: "var(--accent-human)" }}>Regenerated (Less AI)</span>
                    <span className="text-xs" style={{ color: "var(--text-secondary)" }}>{humanized.new_score}% AI</span>
                  </div>
                  <img
                    src={humanized.humanized_image_url}
                    alt="Humanized"
                    className="w-full object-contain max-h-[320px]"
                    style={{ background: "var(--bg-primary)" }}
                  />
                </div>
              </div>

              {/* Changes summary */}
              <div className="mb-4 p-4 rounded-lg text-sm" style={{ background: "var(--bg-primary)", border: "1px solid var(--border-subtle)" }}>
                <h4 className="font-semibold text-white mb-1">What was changed</h4>
                <p style={{ color: "var(--text-secondary)" }}>{humanized.changes_summary}</p>
              </div>

              {/* Prompt toggle + download */}
              <div className="flex items-center gap-3 flex-wrap">
                <button
                  onClick={handleDownload}
                  className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold text-white"
                  style={{ background: "var(--accent-action)" }}
                >
                  <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
                    <path d="M8 2v8M5 7l3 3 3-3" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
                    <path d="M2 12h12" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"/>
                  </svg>
                  Download Image
                </button>
                <button
                  onClick={() => setShowPrompt(!showPrompt)}
                  className="text-sm font-medium px-3 py-2 rounded-lg"
                  style={{
                    background: showPrompt ? "rgba(108,92,231,0.15)" : "transparent",
                    color: "var(--accent-action)",
                    border: "1px solid rgba(108,92,231,0.3)",
                  }}
                >
                  {showPrompt ? "Hide Prompt" : "Show Generation Prompt"}
                </button>
                <button
                  onClick={() => router.push("/")}
                  className="text-sm font-medium"
                  style={{ color: "var(--text-secondary)" }}
                >
                  Try Another Image
                </button>
              </div>

              {showPrompt && (
                <div className="mt-4 p-4 rounded-lg" style={{ background: "var(--bg-primary)", border: "1px solid var(--border-subtle)" }}>
                  <h4 className="text-xs font-semibold uppercase tracking-wider mb-2" style={{ color: "var(--text-secondary)" }}>
                    Generation Prompt Used
                  </h4>
                  <p className="text-sm leading-relaxed" style={{ color: "var(--text-primary)" }}>
                    {humanized.prompt_used}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      <footer className="py-4 text-center text-sm" style={{ color: "var(--text-secondary)", borderTop: "1px solid var(--border-subtle)" }}>
        Humaniser — AI Content Authenticity Detector
      </footer>
    </div>
  );
}