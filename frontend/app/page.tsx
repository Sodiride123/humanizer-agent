"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { analyzeText, analyzeUrl, analyzeFile, analyzeImage, AnalysisResult } from "@/lib/api";
import { Logo } from "@/components/Logo";

type InputMode = "paste" | "upload" | "url" | "image";

export default function Home() {
  const router = useRouter();
  const [mode, setMode] = useState<InputMode>("paste");
  const [text, setText] = useState("");
  const [url, setUrl] = useState("");
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [dragActive, setDragActive] = useState(false);
  const [fileReading, setFileReading] = useState(false);
  const [imageReading, setImageReading] = useState(false);

  // Check if any input mode has content
  const hasTextContent = text.trim().length > 0;
  const hasUrlContent = url.trim().length > 0;
  const hasUploadContent = uploadFile !== null;
  const hasImageContent = imageFile !== null;
  const hasAnyContent = hasTextContent || hasUrlContent || hasUploadContent || hasImageContent;
  const isFileLoading = fileReading || imageReading;

  const clearAllInputs = () => {
    setText("");
    setUrl("");
    setUploadFile(null);
    setImageFile(null);
    setImagePreview("");
    setError("");
    setFileReading(false);
    setImageReading(false);
  };

  const switchMode = (m: InputMode) => {
    if (m === mode) return;
    // If current mode has content, don't allow switching
    if (hasAnyContent) return;
    setMode(m);
    setError("");
  };

  const handleAnalyze = async () => {
    setError("");
    setLoading(true);

    try {
      if (mode === "image") {
        if (!imageFile) {
          setError("Please select an image to analyse");
          setLoading(false);
          return;
        }
        const result = await analyzeImage(imageFile);
        // Don't store in sessionStorage — fetch from backend on results page
        router.push(`/results/image/${result.id}`);
        return;
      }

      let result: AnalysisResult;
      if (mode === "upload") {
        if (!uploadFile && (!text.trim() || text.trim().length < 10)) {
          setError("Please select a file to upload");
          setLoading(false);
          return;
        }
        if (uploadFile) {
          const ext = uploadFile.name.split(".").pop()?.toLowerCase();
          if (ext === "docx" || ext === "pdf") {
            result = await analyzeFile(uploadFile);
          } else {
            // .txt/.md already read into text state
            result = await analyzeText(text.trim());
          }
        } else {
          result = await analyzeText(text.trim());
        }
      } else if (mode === "url") {
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

  const allowedDocExts = [".txt", ".md", ".docx", ".pdf"];

  const readTextFile = (file: File) => {
    const ext = "." + (file.name.split(".").pop()?.toLowerCase() || "");
    setUploadFile(file);
    if (ext === ".txt" || ext === ".md") {
      setFileReading(true);
      const reader = new FileReader();
      reader.onload = (ev) => {
        setText(ev.target?.result as string);
        setFileReading(false);
      };
      reader.onerror = () => {
        setError("Failed to read file");
        setFileReading(false);
      };
      reader.readAsText(file);
    } else {
      setText("");
    }
  };

  const handleFileDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (!file) return;
    const ext = "." + (file.name.split(".").pop()?.toLowerCase() || "");
    if (!allowedDocExts.includes(ext)) {
      setError("Please upload a .txt, .md, .docx, or .pdf file");
      return;
    }
    readTextFile(file);
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    readTextFile(file);
  };

  const handleImageFile = (file: File) => {
    const allowed = ["image/jpeg", "image/png", "image/webp"];
    if (!allowed.includes(file.type)) {
      setError("Please upload a JPEG, PNG, or WebP image");
      return;
    }
    if (file.size > 20 * 1024 * 1024) {
      setError("Image must be under 20MB");
      return;
    }
    setImageFile(file);
    setImageReading(true);
    const reader = new FileReader();
    reader.onload = (ev) => {
      setImagePreview(ev.target?.result as string);
      setImageReading(false);
    };
    reader.onerror = () => {
      setError("Failed to read image");
      setImageReading(false);
    };
    reader.readAsDataURL(file);
    setError("");
  };

  const handleImageDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files[0];
    if (file) handleImageFile(file);
  }, []);

  const handleImageInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleImageFile(file);
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--bg-primary)" }}>
      {/* Nav */}
      <header className="h-16 flex items-center px-6" style={{ borderBottom: "1px solid var(--border-subtle)" }}>
        <div className="max-w-[1200px] mx-auto w-full flex items-center gap-3">
          <Logo size={32} />
          <span className="text-xl font-bold text-white">Humanizer</span>
        </div>
      </header>

      {/* Hero */}
      <main className="flex-1 max-w-[1200px] mx-auto px-6 py-16 w-full">
        <div className="text-center mb-8 max-w-[720px] mx-auto">
          <h1 className="text-5xl font-bold text-white mb-4 leading-tight">
            Detect and Humanize AI Content.
          </h1>
          <p className="text-lg" style={{ color: "var(--text-secondary)" }}>
            Analyse text or images for AI fingerprints, then rewrite or regenerate them to sound authentically human.
          </p>
        </div>

        {/* Input area */}
        <div className="max-w-[680px] mx-auto">
          <div style={{ display: mode === "paste" ? "block" : "none" }}>
            <textarea
              value={text}
              onChange={(e) => setText(e.target.value)}
              placeholder="Paste your text here..."
              className="w-full min-h-[180px] p-5 rounded-2xl resize-y text-base focus:outline-none transition-shadow"
              style={{
                background: "var(--bg-input)",
                border: "1px solid var(--border-subtle)",
                color: "var(--text-primary)",
                fontFamily: "inherit",
                wordBreak: "break-word",
                overflowWrap: "break-word",
                whiteSpace: "pre-wrap",
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
          </div>

          <div style={{ display: mode === "upload" ? "block" : "none" }}>
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
                  <input type="file" accept=".txt,.md,.docx,.pdf" className="hidden" onChange={handleFileInput} />
                </label>
              </p>
              <p className="text-sm" style={{ color: "var(--text-secondary)", opacity: 0.6 }}>Supports .txt, .md, .docx, and .pdf files</p>
              <p className="text-sm mt-1" style={{ color: "var(--text-secondary)", opacity: 0.45 }}>For best results, keep PDF/DOCX files under 15 pages</p>
              {(text || uploadFile) && (
                <div className="mt-4 p-3 rounded-lg text-sm" style={{ background: "rgba(16,185,129,0.1)", color: "var(--accent-human)" }}>
                  {uploadFile ? `${uploadFile.name} selected` : `File loaded (${text.length.toLocaleString()} characters)`}. Click Start Analysing to proceed.
                </div>
              )}
            </div>
          </div>

          <div style={{ display: mode === "url" ? "block" : "none" }}>
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
                Works best with public articles, blog posts, and documentation pages. Sites behind logins or heavy JavaScript may not load correctly.
              </p>
            </div>
          </div>

          <div style={{ display: mode === "image" ? "block" : "none" }}>
            <div>
              {!imagePreview ? (
                <div
                  onDragOver={(e) => { e.preventDefault(); setDragActive(true); }}
                  onDragLeave={() => setDragActive(false)}
                  onDrop={handleImageDrop}
                  className="min-h-[220px] rounded-2xl p-12 text-center transition-colors"
                  style={{
                    background: "var(--bg-input)",
                    border: dragActive ? "2px dashed var(--accent-action)" : "2px dashed var(--border-subtle)",
                  }}
                >
                  <svg width="48" height="48" viewBox="0 0 48 48" fill="none" className="mx-auto mb-4">
                    <rect x="4" y="10" width="40" height="30" rx="4" stroke="var(--text-secondary)" strokeWidth="2.5" fill="none"/>
                    <circle cx="16" cy="20" r="4" stroke="var(--text-secondary)" strokeWidth="2.5" fill="none"/>
                    <path d="M4 34l10-8 8 6 6-5 16 13" stroke="var(--text-secondary)" strokeWidth="2.5" strokeLinejoin="round"/>
                  </svg>
                  <p style={{ color: "var(--text-secondary)" }} className="mb-2">
                    Drag and drop an image here, or{" "}
                    <label className="cursor-pointer font-medium" style={{ color: "var(--accent-action)" }}>
                      browse
                      <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" className="hidden" onChange={handleImageInput} />
                    </label>
                  </p>
                  <p className="text-sm" style={{ color: "var(--text-secondary)", opacity: 0.6 }}>
                    Supports JPEG, PNG, and WebP · Best under 3.5MB for fastest results
                  </p>
                </div>
              ) : (
                <div className="rounded-2xl overflow-hidden relative" style={{ background: "var(--bg-input)", border: "1px solid var(--border-subtle)" }}>
                  <img src={imagePreview} alt="Preview" className="w-full max-h-[320px] object-contain" />
                  <div className="p-3 flex items-center justify-between">
                    <p className="text-sm" style={{ color: "var(--text-secondary)" }}>
                      {imageFile?.name} · {imageFile ? (imageFile.size / 1024).toFixed(0) : 0}KB
                    </p>
                    <button
                      onClick={() => { setImageFile(null); setImagePreview(""); }}
                      className="text-xs px-2 py-1 rounded-md"
                      style={{ color: "var(--accent-ai)", background: "rgba(239,68,68,0.1)" }}
                    >
                      Remove
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Tabs */}
          <div className="flex gap-2 justify-center mt-4 flex-wrap items-center">
            {(["paste", "upload", "url", "image"] as InputMode[]).map((m) => {
              const isActive = mode === m;
              const isDisabled = !isActive && hasAnyContent;
              return (
              <button
                key={m}
                onClick={() => switchMode(m)}
                disabled={isDisabled}
                className="py-2 px-4 rounded-lg text-sm font-medium transition-colors flex items-center gap-1.5"
                style={{
                  background: isActive ? "var(--accent-action)" : "transparent",
                  color: isActive ? "#fff" : "var(--text-secondary)",
                  opacity: isDisabled ? 0.35 : 1,
                  cursor: isDisabled ? "not-allowed" : "pointer",
                }}
              >
                {m === "image" && (
                  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
                    <rect x="1" y="3" width="12" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.5" fill="none"/>
                    <circle cx="4.5" cy="6.5" r="1.5" stroke="currentColor" strokeWidth="1.2" fill="none"/>
                    <path d="M1 10.5l3-2.5 2.5 2 2-1.5 4.5 4" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round"/>
                  </svg>
                )}
                {m === "paste" ? "Paste Text" : m === "upload" ? "Upload File" : m === "url" ? "Enter URL" : "Image"}
              </button>
              );
            })}
            {hasAnyContent && (
              <button
                onClick={clearAllInputs}
                className="py-2 px-4 rounded-lg text-xs font-medium transition-colors"
                style={{ color: "var(--accent-ai)", background: "rgba(239,68,68,0.1)" }}
              >
                Clear
              </button>
            )}
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
            disabled={loading || isFileLoading}
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
            ) : isFileLoading ? (
              <span className="flex items-center justify-center gap-2">
                <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24" fill="none">
                  <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25"/>
                  <path d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" fill="currentColor" className="opacity-75"/>
                </svg>
                Loading File...
              </span>
            ) : (
              "Start Analysing"
            )}
          </button>
        </div>

        {/* Feature cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mt-16 max-w-[1200px]">
          {[
            { title: "Text Detection", desc: "Detect AI-generated text with 24-pattern analysis across content, language and style.", icon: (
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                <circle cx="24" cy="24" r="18" stroke="var(--accent-action)" strokeWidth="3"/>
                <path d="M24 12v12l8 4" stroke="var(--accent-action)" strokeWidth="3" strokeLinecap="round"/>
              </svg>
            )},
            { title: "Image Detection", desc: "Spot AI-generated images by analysing 20 visual patterns — textures, lighting, hands and more.", icon: (
              <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
                <rect x="4" y="10" width="40" height="28" rx="4" stroke="var(--accent-action)" strokeWidth="3" fill="none"/>
                <circle cx="16" cy="22" r="5" stroke="var(--accent-action)" strokeWidth="3" fill="none"/>
                <path d="M4 36l12-10 9 7 7-6 12 9" stroke="var(--accent-action)" strokeWidth="3" strokeLinejoin="round"/>
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
        Humanizer — AI Content Authenticity Detector
      </footer>
    </div>
  );
}
