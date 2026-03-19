# Humanizer 🤖→👤

**AI Content Detector & Humanizer — reduce AI detection scores for text and images.**

Humanizer analyses your content for AI fingerprints, then rewrites or regenerates it to pass AI detection tools. It supports both text and images, with a style-aware pipeline that preserves your original design intent while minimising detectable AI patterns.

---

## ✨ Features

- **Text Detection** — Analyse text for AI fingerprints using a 24-pattern detection system
- **Text Humanization** — Paste AI-generated text, get a rewritten version with lower AI detection scores
- **Image Detection** — Upload images to detect AI-generated patterns across textures, lighting, and more
- **Image Humanization** — Upload an AI-generated image, get a regenerated version with pixel-level post-processing to reduce AI fingerprints
- **File Upload** — Supports .txt, .md, .docx, and .pdf file uploads with server-side text extraction
- **URL Extraction** — Paste a URL to extract and analyse text content from public web pages
- **Style-Aware Prompting** — Detects image type (photograph, graphic design, illustration, UI screenshot) and applies the right humanization strategy
- **Post-Processing Pipeline** — 6-step pixel-level pipeline applied after generation: shot noise, chromatic aberration, barrel distortion, colour temperature shift, vignette, and JPEG recompression
- **AI Score Tracking** — Shows before/after AI detection scores for every result
- **Pattern Analysis** — Identifies specific AI patterns detected in your content

---

## 📏 Input Limits

### Analysis (Paste Text / File Upload / URL)

| Layer | Limit | Behaviour |
|---|---|---|
| Frontend | none | No client-side cap |
| Backend Pydantic (paste text) | 100,000 chars | Rejected with 422 if exceeded |
| Backend actual analysis | **50,000 chars** | Text silently truncated before analysis |

All three input methods (paste, upload, URL) are truncated to **50,000 characters** before being sent to the LLM. Content beyond that point is not analysed. There is currently no user-visible warning when truncation occurs.

> **Token equivalents** (approximate, varies by language):
> - English: ~12,500 tokens (4 chars/token)
> - Russian / Cyrillic: ~25,000 tokens (2 chars/token)
> - Chinese / Japanese / Korean: ~50,000 tokens (1 char/token)

### Humanization (results page)

| Layer | Limit | Behaviour |
|---|---|---|
| Frontend check | 30,000 chars | Button disabled, error shown |
| Backend Pydantic | 30,000 chars | Rejected with 422 if exceeded |
| Backend logic | 30,000 chars | Explicit 400 error with char count |
| LLM timeout | 300 seconds | RuntimeError if model exceeds limit |
| Frontend poll window | 360 seconds (180 × 2s) | "Humanization timed out" if exceeded |

The 30,000 character humanization limit is set to stay within the **30,000 tokens/minute company rate limit**. For non-English text (Russian/CJK), a 30,000-character input can consume 15,000–30,000 tokens, which approaches or fills the entire TPM budget in a single request.

> **Known limitation:** the 30,000 character cap may still result in a timeout for long non-English texts (particularly CJK) because those use closer to 1 char/token, meaning the LLM must generate a very large output. If you consistently hit timeouts, reduce the input to ~15,000 characters.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│           Next.js Frontend              │
│         (port 3000, production build)   │
│                                         │
│  /                 → Upload & analyse   │
│  /results/[id]     → Text results       │
│  /results/image/[id] → Image results    │
└──────────────┬──────────────────────────┘
               │  /api/* reverse proxy
               ▼
┌─────────────────────────────────────────┐
│           FastAPI Backend               │
│         (port 8000)                     │
│                                         │
│  POST /api/analyze/text       → job     │
│  POST /api/upload-file        → job     │
│  POST /api/extract-url        → job     │
│  GET  /api/analyze/text/status/{id}     │
│  POST /api/humanize           → job     │
│  GET  /api/humanize/status/{id}         │
│  POST /api/analyze/image      → sync    │
│  POST /api/humanize/image     → job     │
│  GET  /api/humanize/image/status/{id}   │
│  GET  /api/results/{id}                 │
│  GET  /api/results/image/{id}           │
│  GET  /api/images/{file}      → static  │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│              utils/                     │
│                                         │
│  chat.py          → LLM calls (LiteLLM) │
│  images.py        → Image generation    │
│  litellm_client.py → Model routing      │
└─────────────────────────────────────────┘
```

### Async architecture note

All LLM calls (`chat_json`, `chat_messages`) use the synchronous `requests` library internally. To prevent these from blocking the asyncio event loop (which caused status-poll requests to time out during processing), every LLM call in an async context is wrapped with `run_in_executor`:

```python
async def _chat_json_async(*args, **kwargs) -> dict:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, functools.partial(chat_json, *args, **kwargs))
```

This allows status endpoints to respond normally while a long humanization or analysis job is running in a thread pool.

---

## 📁 Project Structure

```
humanizer-agent/
├── README.md
├── requirements.txt
│
├── backend/
│   ├── main.py              # FastAPI app — all routes & job logic
│   ├── requirements.txt     # Backend Python dependencies
│   └── generated_images/    # Runtime image storage (gitignored)
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx       # Root layout
│   │   ├── page.tsx         # Home — upload & analyse
│   │   ├── globals.css      # Global styles
│   │   ├── favicon.ico      # Waveform-H logo favicon
│   │   └── results/
│   │       ├── [id]/        # Text humanization results
│   │       └── image/[id]/  # Image humanization results
│   ├── components/
│   │   └── Logo.tsx         # Waveform-H SVG logo component
│   ├── lib/
│   │   └── api.ts           # API client & TypeScript types
│   └── next.config.ts       # Reverse proxy → backend:8000
│
├── utils/
│   ├── chat.py              # LLM chat helpers (supports timeout param)
│   ├── images.py            # Image generation helpers
│   └── litellm_client.py    # LiteLLM model client
│
└── agent-docs/
    ├── PRD.md               # Product requirements
    ├── DEPLOYMENT.md        # Deployment guide
    ├── LITELLM_GUIDE.md     # LiteLLM configuration
    └── MODELS.md            # Model selection guide
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- LiteLLM-compatible API key (configured via `settings.json` or environment variables)

### Option A — Using scripts

```bash
# First time: install all dependencies
bash setup.sh

# Start the app
bash start.sh
```

### Option B — Manual

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000

# Frontend (in a separate terminal)
cd frontend
npm install
npm run build
npx next start -H 0.0.0.0
```

Open [http://localhost:3000](http://localhost:3000).

---

## ⚙️ Configuration

The app reads credentials from `/root/.claude/settings.json`:

```json
{
  "env": {
    "ANTHROPIC_AUTH_TOKEN": "sk-...",
    "ANTHROPIC_BASE_URL": "https://your-litellm-gateway/",
    "ANTHROPIC_MODEL": "claude-sonnet-4-5-20250929"
  }
}
```

You can also override with environment variables `LITELLM_API_KEY` and `LITELLM_BASE_URL`.

See [`agent-docs/LITELLM_GUIDE.md`](agent-docs/LITELLM_GUIDE.md) for full model configuration options.

---

## 🖼️ Image Humanization Pipeline

When an image is submitted for humanization, the backend runs a two-phase pipeline:

### Phase 1 — Analysis
- Image is analysed by a vision LLM
- Detects image type: `photograph`, `graphic_design`, `illustration`, `ui_screenshot`, or `mixed`
- Identifies up to 20 specific AI pattern categories
- Returns an AI detection score and pattern breakdown

### Phase 2 — Humanization
Three strategies are applied based on detected image type:

| Strategy | Image Types | Approach |
|----------|-------------|----------|
| **A — Photograph** | `photograph` | Candid documentary style, DSLR imperfections, natural lighting |
| **B — Graphic Design** | `graphic_design`, `illustration`, `mixed` | Preserves brand/layout, adds hand-crafted imperfections |
| **C — UI Screenshot** | `ui_screenshot` | Faithful interface recreation with subtle organic touches |

### Phase 3 — Post-Processing
After generation, a 6-step pixel-level pipeline is applied:

1. **Shot noise** — Poisson-like noise scaled to local brightness
2. **Chromatic aberration** — R channel shifted +1–2px, B channel –1–2px
3. **Barrel distortion** — 0.4–0.7% lens distortion coefficient
4. **Colour temperature shift** — Random warm / cool / neutral tint
5. **Vignette** — 4–8% edge darkening
6. **JPEG recompression** — 78–85% quality to bake in DCT artifacts

---

## 📋 Logging

The backend logs to stdout and to `/tmp/humanizer-backend.log` when started with:

```bash
nohup uvicorn main:app --host 0.0.0.0 --port 8000 >> /tmp/humanizer-backend.log 2>&1 &
```

All job failures log the full exception stack trace via `logger.exception(...)`, making it possible to diagnose LLM errors, timeouts, and JSON parse failures without restarting the server.

---

## 📄 License

MIT License
