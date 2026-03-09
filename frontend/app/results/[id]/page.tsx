"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getResult, AnalysisResult, SentenceResult } from "@/lib/api";

function getScoreColor(score: number): string {
  if (score >= 80) return "text-red-600";
  if (score >= 60) return "text-orange-500";
  if (score >= 40) return "text-yellow-600";
  return "text-green-600";
}

function getScoreBg(score: number): string {
  if (score >= 80) return "bg-red-50 border-red-200";
  if (score >= 60) return "bg-orange-50 border-orange-200";
  if (score >= 40) return "bg-yellow-50 border-yellow-200";
  return "bg-green-50 border-green-200";
}

function getSentenceBg(label: string): string {
  return label === "ai"
    ? "bg-red-100 border-l-4 border-red-400"
    : "bg-green-100 border-l-4 border-green-400";
}

function ScoreRing({ score }: { score: number }) {
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (score / 100) * circumference;
  const color = score >= 80 ? "#DC2626" : score >= 60 ? "#F97316" : score >= 40 ? "#CA8A04" : "#16A34A";

  return (
    <div className="relative w-36 h-36">
      <svg width="144" height="144" viewBox="0 0 144 144" className="transform -rotate-90">
        <circle cx="72" cy="72" r="54" fill="none" stroke="#E5E7EB" strokeWidth="12" />
        <circle
          cx="72" cy="72" r="54" fill="none"
          stroke={color} strokeWidth="12"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-1000"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`text-3xl font-bold ${getScoreColor(score)}`}>{score}%</span>
        <span className="text-xs text-gray-500">AI Score</span>
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
    // Try sessionStorage first, then API
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
      <div className="min-h-screen flex items-center justify-center bg-[#fafbfc]">
        <div className="text-center">
          <svg className="animate-spin h-10 w-10 mx-auto mb-4 text-indigo-600" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"/>
            <path d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" fill="currentColor" className="opacity-75"/>
          </svg>
          <p className="text-gray-600">Loading results...</p>
        </div>
      </div>
    );
  }

  if (error || !result) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#fafbfc]">
        <div className="text-center">
          <p className="text-red-600 mb-4">{error || "Result not found"}</p>
          <button onClick={() => router.push("/")} className="text-indigo-600 hover:text-indigo-700 font-medium">
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  const aiSentences = result.sentences.filter((s) => s.label === "ai").length;
  const humanSentences = result.sentences.filter((s) => s.label === "human").length;

  return (
    <div className="min-h-screen flex flex-col bg-[#fafbfc]">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
              <rect width="32" height="32" rx="8" fill="#4F46E5"/>
              <path d="M16 6L20 14H12L16 6Z" fill="white"/>
              <path d="M12 14H20L18 22H14L12 14Z" fill="white" opacity="0.8"/>
              <path d="M14 22H18L16 26L14 22Z" fill="white" opacity="0.6"/>
            </svg>
            <h1 className="text-xl font-bold text-gray-900">AI Content Detector</h1>
          </div>
          <button
            onClick={() => router.push("/")}
            className="text-sm text-indigo-600 hover:text-indigo-700 font-medium flex items-center gap-1"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M10 4L6 8l4 4" stroke="currentColor" strokeWidth="2"/>
            </svg>
            New Analysis
          </button>
        </div>
      </header>

      <main className="flex-1 max-w-4xl mx-auto px-4 py-8 w-full">
        {/* Score card */}
        <div className={`rounded-xl border p-6 mb-6 ${getScoreBg(result.overall_score)}`}>
          <div className="flex flex-col sm:flex-row items-center gap-6">
            <ScoreRing score={result.overall_score} />
            <div className="flex-1 text-center sm:text-left">
              <h2 className={`text-2xl font-bold ${getScoreColor(result.overall_score)}`}>
                {result.confidence_label}
              </h2>
              <p className="text-gray-600 mt-1">{result.word_count} words analyzed</p>
              <div className="flex gap-4 mt-3 justify-center sm:justify-start">
                <span className="inline-flex items-center gap-1.5 text-sm">
                  <span className="w-3 h-3 rounded-full bg-red-400 inline-block"></span>
                  {aiSentences} AI sentences
                </span>
                <span className="inline-flex items-center gap-1.5 text-sm">
                  <span className="w-3 h-3 rounded-full bg-green-400 inline-block"></span>
                  {humanSentences} Human sentences
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Summary */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Summary</h3>
          <p className="text-gray-700 leading-relaxed">{result.summary}</p>
        </div>

        {/* Sentence-level overlay */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 mb-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Sentence Analysis</h3>
          <p className="text-sm text-gray-500 mb-4">
            Each sentence is highlighted based on its AI likelihood score
          </p>

          <div className="flex gap-4 mb-4 text-sm">
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-red-200 inline-block border border-red-300"></span>
              AI-Generated
            </span>
            <span className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded bg-green-200 inline-block border border-green-300"></span>
              Human-Written
            </span>
          </div>

          <div className="space-y-2">
            {result.sentences.map((sentence: SentenceResult, i: number) => (
              <div key={i} className={`p-3 rounded-md ${getSentenceBg(sentence.label)}`}>
                <div className="flex justify-between items-start gap-3">
                  <p className="text-gray-800 text-sm flex-1">{sentence.text}</p>
                  <span
                    className={`text-xs font-medium px-2 py-1 rounded-full whitespace-nowrap ${
                      sentence.label === "ai"
                        ? "bg-red-200 text-red-800"
                        : "bg-green-200 text-green-800"
                    }`}
                  >
                    {sentence.score}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Details */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Details</h3>
          <dl className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <dt className="text-gray-500">Input Type</dt>
              <dd className="font-medium text-gray-900 capitalize">{result.input_type}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Word Count</dt>
              <dd className="font-medium text-gray-900">{result.word_count}</dd>
            </div>
            <div>
              <dt className="text-gray-500">Overall Score</dt>
              <dd className="font-medium text-gray-900">{result.overall_score}%</dd>
            </div>
            <div>
              <dt className="text-gray-500">Sentences Analyzed</dt>
              <dd className="font-medium text-gray-900">{result.sentences.length}</dd>
            </div>
            {result.source_url && (
              <div className="col-span-2">
                <dt className="text-gray-500">Source URL</dt>
                <dd className="font-medium text-indigo-600 truncate">{result.source_url}</dd>
              </div>
            )}
          </dl>
        </div>
      </main>

      <footer className="border-t border-gray-200 py-4 text-center text-sm text-gray-500">
        AI Content Authenticity Detector
      </footer>
    </div>
  );
}
