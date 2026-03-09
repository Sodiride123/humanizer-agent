"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { analyzeText, analyzeUrl, AnalysisResult } from "@/lib/api";

type InputMode = "paste" | "upload" | "url";

export default function Home() {
  const router = useRouter();
  const [mode, setMode] = useState<InputMode>("paste");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dragActive, setDragActive] = useState(false);

  const handleAnalyze = async () => {
    setError("");
    setLoading(true);

    try {
      let result: AnalysisResult;
      if (mode === "url") {
        if (!url.trim()) {
          setError("Please enter a URL");
          setLoading(false);
          return;
        }
        result = await analyzeUrl(url.trim());
      } else {
        if (!text.trim() || text.trim().length < 10) {
          setError("Please enter at least 10 characters of text");
          setLoading(false);
          return;
        }
        result = await analyzeText(text.trim());
      }
      sessionStorage.setItem(`result-${result.id}`, JSON.stringify(result));
      router.push(`/results/${result.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const handleFileDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file && (file.type === "text/plain" || file.name.endsWith(".txt") || file.name.endsWith(".md"))) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setText(ev.target?.result as string);
        setMode("paste");
      };
      reader.readAsText(file);
    } else {
      setError("Please upload a .txt or .md file");
    }
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (ev) => {
        setText(ev.target?.result as string);
        setMode("paste");
      };
      reader.readAsText(file);
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-[#fafbfc]">
      {/* Header */}
      <header className="border-b border-gray-200 bg-white">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center gap-3">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect width="32" height="32" rx="8" fill="#4F46E5"/>
            <path d="M16 6L20 14H12L16 6Z" fill="white"/>
            <path d="M12 14H20L18 22H14L12 14Z" fill="white" opacity="0.8"/>
            <path d="M14 22H18L16 26L14 22Z" fill="white" opacity="0.6"/>
          </svg>
          <h1 className="text-xl font-bold text-gray-900">AI Content Detector</h1>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 max-w-4xl mx-auto px-4 py-8 w-full">
        <div className="text-center mb-8">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">Detect AI-Generated Content</h2>
          <p className="text-gray-600 text-lg">Paste text, upload a file, or enter a URL to analyze</p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg mb-6 max-w-md mx-auto">
          {(["paste", "upload", "url"] as InputMode[]).map((m) => (
            <button
              key={m}
              onClick={() => { setMode(m); setError(""); }}
              className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
                mode === m ? "bg-white text-gray-900 shadow-sm" : "text-gray-600 hover:text-gray-900"
              }`}
            >
              {m === "paste" ? "Paste Text" : m === "upload" ? "Upload File" : "Enter URL"}
            </button>
          ))}
        </div>

        {/* Input card */}
        <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
          {mode === "paste" && (
            <div>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste your text here to check if it was written by AI..."
                className="w-full h-48 p-4 border border-gray-200 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900 placeholder-gray-400"
              />
              <div className="flex justify-between items-center mt-2 text-sm text-gray-500">
                <span>{text.length.toLocaleString()} characters</span>
                <span>{text.split(/\s+/).filter(Boolean).length} words</span>
              </div>
            </div>
          )}

          {mode === "upload" && (
            <div
              onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
              onDragLeave={() => setDragActive(false)}
              onDrop={handleFileDrop}
              className={`border-2 border-dashed rounded-lg p-12 text-center transition-colors ${
                dragActive ? "border-indigo-500 bg-indigo-50" : "border-gray-300 hover:border-gray-400"
              }`}
            >
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none" className="mx-auto mb-4">
                <path d="M24 8v24M16 16l8-8 8 8" stroke="#9CA3AF" strokeWidth="2.5"/>
                <path d="M8 32v8h32v-8" stroke="#9CA3AF" strokeWidth="2.5"/>
              </svg>
              <p className="text-gray-600 mb-2">
                Drag and drop a text file here, or{" "}
                <label className="text-indigo-600 cursor-pointer hover:text-indigo-700 font-medium">
                  browse
                  <input type="file" accept=".txt,.md" className="hidden" onChange={handleFileInput} />
                </label>
              </p>
              <p className="text-sm text-gray-400">Supports .txt and .md files</p>
              {text && (
                <div className="mt-4 p-3 bg-green-50 rounded-lg text-green-700 text-sm">
                  File loaded ({text.length.toLocaleString()} characters). Click Analyze to proceed.
                </div>
              )}
            </div>
          )}

          {mode === "url" && (
            <div>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://example.com/article"
                className="w-full p-4 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-gray-900 placeholder-gray-400"
              />
              <p className="mt-2 text-sm text-gray-500">Enter a URL to extract and analyze the text content</p>
            </div>
          )}

          {error && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
          )}

          <button
            onClick={handleAnalyze}
            disabled={loading}
            className="mt-6 w-full py-3 px-6 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"/>
                  <path d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" fill="currentColor" className="opacity-75"/>
                </svg>
                Analyzing...
              </>
            ) : (
              "Analyze Content"
            )}
          </button>
        </div>
      </main>

      <footer className="border-t border-gray-200 py-4 text-center text-sm text-gray-500">
        AI Content Authenticity Detector
      </footer>
    </div>
  );
}
