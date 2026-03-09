"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getResult, AnalysisResult, SentenceResult } from "@/lib/api";

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
  const gradientId = "gauge-gradient";
  const [c1, c2] = getGaugeGradient(score);

  return (
    <div className="relative w-60 h-60">
      <svg width="240" height="240" viewBox="0 0 240 240" className="transform -rotate-90">
        <circle cx="120" cy="120" r="100" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="16" />
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={c1} />
            <stop offset="100%" stopColor={c2} />
          </linearGradient>
        </defs>
        <circle
          cx="120" cy="120" r="100" fill="none"
          stroke={`url(#${gradientId})`} strokeWidth="16"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-[800ms] ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-[56px] font-bold text-white" style={{ fontFamily: "var(--font-mono), 'JetBrains Mono', monospace" }}>
          {Math.round(score)}%
        </span>
        <span className="text-base font-medium" style={{ color: "var(--text-secondary)" }}>
          AI Detected
        </span>
      </div>
    </div>
  );
}

export default function ResultsPage() {
  const params = useParams();
  const router = useRouter();
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const id = params.id as string;
    const cached = sessionStorage.getItem(`result-${id}`);
    if (cached) {
      setResult(JSON.parse(cached));
      setLoading(false);
      return;
    }
    getResult(id)
      .then(setResult)
      .catch(() => setError("Result not found"))
      .finally(() => setLoading(false));
  }, [params.id]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: "var(--bg-primary)" }}>
        <div className="text-center">
          <svg className="animate-spin h-10 w-10 mx-auto mb-4" style={{ color: "var(--accent-action)" }} viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"/>
            <path d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" fill="currentColor" className="opacity-75"/>
          </svg>
          <p style={{ color: "var(--text-secondary)" }}>Loading results...</p>
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

  const aiSentences = result.sentences.filter((s) => s.label === "ai").length;
  const humanSentences = result.sentences.filter((s) => s.label === "human").length;
  const confidenceLabel = result.overall_score >= 60 ? "High" : result.overall_score >= 30 ? "Medium" : "Low";
  const confidenceColor = result.overall_score >= 60 ? "var(--accent-ai)" : result.overall_score >= 30 ? "var(--accent-warning)" : "var(--accent-human)";

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
          <button onClick={() => router.push("/")} style={{ color: "var(--text-secondary)" }} className="hover:text-white">
            Home
          </button>
          <span style={{ color: "var(--text-secondary)" }}>&gt;</span>
          <span className="text-white">Results</span>
        </div>
      </div>

      <main className="flex-1 max-w-[1200px] mx-auto px-6 py-6 w-full">
        {/* Two-column layout */}
        <div className="grid grid-cols-1 lg:grid-cols-[380px_1fr] gap-6">
          {/* Left column — Gauge + Stats */}
          <div className="space-y-4">
            <div className="rounded-xl p-6 flex flex-col items-center" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)" }}>
              <h2 className="text-xl font-bold text-white mb-4">Analysis Results</h2>
              <ScoreGauge score={result.overall_score} />
              <p className="mt-2 text-lg font-semibold" style={{ color: getGaugeColor(result.overall_score) }}>
                {result.confidence_label}
              </p>
              <p className="text-sm mt-1" style={{ color: "var(--text-secondary)" }}>
                {result.word_count} words analyzed
              </p>
            </div>

            {/* Stats cards */}
            <div className="grid grid-cols-3 gap-3">
              <div className="rounded-xl p-4 text-center" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)" }}>
                <p className="text-xs font-medium mb-1" style={{ color: "var(--text-secondary)" }}>Confidence</p>
                <p className="text-2xl font-bold" style={{ color: confidenceColor }}>{confidenceLabel}</p>
              </div>
              <div className="rounded-xl p-4 text-center" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)" }}>
                <p className="text-xs font-medium mb-1" style={{ color: "var(--text-secondary)" }}>Sentences</p>
                <p className="text-2xl font-bold text-white">{result.sentences.length}</p>
              </div>
              <div className="rounded-xl p-4 text-center" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)" }}>
                <p className="text-xs font-medium mb-1" style={{ color: "var(--text-secondary)" }}>AI Count</p>
                <p className="text-2xl font-bold" style={{ color: "var(--accent-ai)" }}>{aiSentences}</p>
              </div>
            </div>

            {/* Summary */}
            <div className="rounded-xl p-4" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)" }}>
              <h3 className="text-sm font-semibold text-white mb-2">Summary</h3>
              <p className="text-sm leading-relaxed" style={{ color: "var(--text-secondary)" }}>{result.summary}</p>
            </div>
          </div>

          {/* Right column — Sentence analysis */}
          <div className="rounded-xl p-6 max-h-[600px] overflow-y-auto" style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)" }}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-white">Your Text</h3>
              <div className="flex gap-4 text-xs">
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded" style={{ background: "var(--accent-ai)" }}></span>
                  AI-Generated
                </span>
                <span className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded" style={{ background: "var(--accent-human)" }}></span>
                  Human-Written
                </span>
              </div>
            </div>

            <div className="space-y-1" style={{ lineHeight: "1.8" }}>
              {result.sentences.map((sentence: SentenceResult, i: number) => {
                const isAi = sentence.label === "ai";
                const borderColor = isAi ? "var(--accent-ai)" : "var(--accent-human)";
                const bgColor = isAi ? "rgba(239,68,68,0.08)" : "rgba(16,185,129,0.08)";
                const badgeBg = isAi ? "rgba(239,68,68,0.2)" : "rgba(16,185,129,0.2)";
                const badgeText = isAi ? "var(--accent-ai)" : "var(--accent-human)";

                return (
                  <div
                    key={i}
                    className="p-3 rounded-md"
                    style={{ borderLeft: `3px solid ${borderColor}`, background: bgColor }}
                  >
                    <div className="flex justify-between items-start gap-3">
                      <p className="text-sm flex-1 text-white">{sentence.text}</p>
                      <span
                        className="text-xs font-medium px-2 py-0.5 rounded-full whitespace-nowrap"
                        style={{
                          background: badgeBg,
                          color: badgeText,
                          fontFamily: "var(--font-mono), 'JetBrains Mono', monospace",
                        }}
                      >
                        {Math.round(sentence.score)}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Humanise CTA */}
        <div className="mt-8 text-center">
          <button
            onClick={() => router.push("/")}
            className="w-full max-w-[480px] h-[60px] rounded-xl text-xl font-semibold text-white transition-all flex items-center justify-center gap-2 mx-auto"
            style={{ background: "var(--accent-action)" }}
            onMouseEnter={(e) => {
              e.currentTarget.style.boxShadow = "0 4px 24px rgba(108,92,231,0.5)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            Humanise This Text
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
              <path d="M6 10h8M11 6l4 4-4 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
            </svg>
          </button>
        </div>
      </main>

      <footer className="py-4 text-center text-sm" style={{ color: "var(--text-secondary)", borderTop: "1px solid var(--border-subtle)" }}>
        Humaniser — AI Content Authenticity Detector
      </footer>
    </div>
  );
}
