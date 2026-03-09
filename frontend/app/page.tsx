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
    <div className="min-h-screen flex flex-col" style={{ background: "var(--bg-primary)" }}>
      {/* Nav */}
      <header className="h-16 flex items-center px-6" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
        <div className="max-w-[1200px] mx-auto w-full flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center font-bold text-white" style={{ background: "var(--accent-action)" }}>
            H
          </div>
          <span className="text-xl font-bold text-white">Humaniser</span>
        </div>
      </header>

      {/* Hero */}
      <main className="flex-1 max-w-[1200px] mx-auto px-6 py-16 w-full">
        <div className="text-center mb-8 max-w-[720px] mx-auto">
          <h1 className="text-5xl font-bold text-white mb-4 leading-tight">
            Make Your AI Text Sound Human.
          </h1>
          <p className="text-lg" style={{ color: "var(--text-secondary)" }}>
            Paste your AI-generated text and get a natural human-sounding version in seconds.
          </p>
        </div>

        {/* Input area */}
        <div className="max-w-[680px] mx-auto">
          {mode === "paste" && (
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste your text here or upload a file..."
              className="w-full min-h-[180px] p-5 rounded-2xl resize-y text-base focus:outline-none transition-shadow"
              style={{
                background: "var(--bg-input)",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-primary)",
                fontFamily: "inherit",
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = "var(--border-focus)";
                e.currentTarget.style.boxShadow = "0 0 0 3px rgba(108,92,231,0.15)";
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = "var(--border-subtle)";
                e.currentTarget.style.boxShadow = "none";
              }}
            />
          )}

          {mode === "upload" && (
            <div
              onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
              onDragLeave={() => setDragActive(false)}
              onDrop={handleFileDrop}
              className="min-h-[180px] rounded-2xl p-12 text-center transition-colors"
              style={{
                background: "var(--bg-input)",
                border: dragActive ? "2px dashed var(--accent-action)" : "2px dashed var(--border-subtle)",
              }}
            >
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none" className="mx-auto mb-4">
                <path d="M24 8v24M16 16l8-8 8 8" stroke="var(--text-secondary)" strokeWidth="2.5"/>
                <path d="M8 32v8h32v-8" stroke="var(--text-secondary)" strokeWidth="2.5"/>
              </svg>
              <p style={{ color: "var(--text-secondary)" }} className="mb-2">
                Drag and drop a text file here, or{" "}
                <label className="cursor-pointer font-medium" style={{ color: "var(--accent-action)" }}>
                  browse
                  <input type="file" accept=".txt,.md" className="hidden" onChange={handleFileInput} />
                </label>
              </p>
              <p className="text-sm" style={{ color: "var(--text-secondary)", opacity: 0.6 }}>Supports .txt and .md files</p>
              {text && (
                <div className="mt-4 p-3 rounded-lg text-sm" style={{ background: "rgba(16,185,129,0.1)", color: "var(--accent-human)" }}>
                  File loaded ({text.length.toLocaleString()} characters). Click Analyse to proceed.
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
                className="w-full p-5 rounded-2xl text-base focus:outline-none transition-shadow"
                style={{
                  background: "var(--bg-input)",
                  border: "1px solid var(--border-subtle)",
                  color: "var(--text-primary)",
                }}
                onFocus={(e) => {
                  e.currentTarget.style.borderColor = "var(--border-focus)";
                  e.currentTarget.style.boxShadow = "0 0 0 3px rgba(108,92,231,0.15)";
                }}
                onBlur={(e) => {
                  e.currentTarget.style.borderColor = "var(--border-subtle)";
                  e.currentTarget.style.boxShadow = "none";
                }}
              />
              <p className="mt-2 text-sm" style={{ color: "var(--text-secondary)" }}>
                Enter a URL to extract and analyze the text content
              </p>
            </div>
          )}

          {/* Tabs */}
          <div className="flex gap-2 justify-center mt-4">
            {(["paste", "upload", "url"] as InputMode[]).map((m) => (
              <button
                key={m}
                onClick={() => { setMode(m); setError(""); }}
                className="py-2 px-4 rounded-lg text-sm font-medium transition-colors"
                style={{
                  background: mode === m ? "var(--accent-action)" : "transparent",
                  color: mode === m ? "#fff" : "var(--text-secondary)",
                }}
              >
                {m === "paste" ? "Paste Text" : m === "upload" ? "Upload File" : "Enter URL"}
              </button>
            ))}
          </div>

          {/* Error */}
          {error && (
            <div className="mt-4 p-3 rounded-lg text-sm" style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.2)", color: "var(--accent-ai)" }}>
              {error}
            </div>
          )}

          {/* Analyse button */}
          <button
            onClick={handleAnalyze}
            disabled={loading}
            className="mt-6 mx-auto block w-[280px] h-[56px] rounded-xl text-lg font-semibold text-white transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              background: "var(--accent-action)",
            }}
            onMouseEnter={(e) => {
              if (!loading) {
                e.currentTarget.style.background = "var(--accent-action-hover)";
                e.currentTarget.style.boxShadow = "0 4px 20px rgba(108,92,231,0.4)";
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = "var(--accent-action)";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            {loading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"/>
                  <path d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" fill="currentColor" className="opacity-75"/>
                </svg>
                Analysing...
              </span>
            ) : (
              "Analyse Text"
            )}
          </button>
        </div>

        {/* Feature cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-16 max-w-[1200px]">
          {[
            { title: "AI Detection", desc: "Detect AI-generated content with 98% accuracy using advanced analysis.", icon: (
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                <circle cx="24" cy="24" r="18" stroke="var(--accent-action)" strokeWidth="3"/>
                <path d="M24 12v12l8 4" stroke="var(--accent-action)" strokeWidth="3" strokeLinecap="round"/>
              </svg>
            )},
            { title: "Smart Rewriting", desc: "Preserve meaning while making your text sound naturally human.", icon: (
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                <path d="M8 36l8-8 6 6 10-14 8 8" stroke="var(--accent-action)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            )},
            { title: "Privacy First", desc: "Your data is never stored. All analysis happens in real-time.", icon: (
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                <path d="M24 4L8 12v12c0 11 16 20 16 20s16-9 16-20V12L24 4z" stroke="var(--accent-action)" strokeWidth="3" fill="none"/>
                <path d="M18 24l4 4 8-8" stroke="var(--accent-action)" strokeWidth="3" strokeLinecap="round"/>
              </svg>
            )},
          ].map((card) => (
            <div
              key={card.title}
              className="p-6 rounded-xl transition-transform hover:-translate-y-0.5"
              style={{ background: "var(--bg-secondary)", border: "1px solid var(--border-subtle)" }}
            >
              <div className="mb-4">{card.icon}</div>
              <h3 className="text-base font-semibold text-white mb-2">{card.title}</h3>
              <p className="text-sm" style={{ color: "var(--text-secondary)" }}>{card.desc}</p>
            </div>
          ))}
        </div>
      </main>

      <footer className="py-4 text-center text-sm" style={{ color: "var(--text-secondary)", borderTop: "1px solid var(--border-subtle)" }}>
        Humaniser — AI Content Authenticity Detector
      </footer>
    </div>
  );
}
