# Humanizer 🤖→👤

**AI Content Detector & Humanizer — reduce AI detection scores for text and images.**

Humanizer analyses your content for AI fingerprints, then rewrites or regenerates it to pass AI detection tools. It supports both text and images, with a style-aware pipeline that preserves your original design intent while minimising detectable AI patterns.

---

## ✨ Features

- **Text Humanization** — Paste AI-generated text, get a rewritten version with lower AI detection scores
- **Image Humanization** — Upload an AI-generated image, get a regenerated version with pixel-level post-processing to reduce AI fingerprints
- **Style-Aware Prompting** — Detects image type (photograph, graphic design, illustration, UI screenshot) and applies the right humanization strategy
- **Post-Processing Pipeline** — 6-step pixel-level pipeline applied after generation: shot noise, chromatic aberration, barrel distortion, colour temperature shift, vignette, and JPEG recompression
- **AI Score Tracking** — Shows before/after AI detection scores for every result
- **Pattern Analysis** — Identifies specific AI patterns detected in your content

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│           Next.js Frontend              │
│         (port 3000)                     │
│                                         │
│  /           → Upload & analyse         │
│  /results/[id]     → Text results       │
│  /results/image/[id] → Image results    │
└──────────────┬──────────────────────────┘
               │  /api/* reverse proxy
               ▼
┌─────────────────────────────────────────┐
│           FastAPI Backend               │
│         (port 8000)                     │
│                                         │
│  POST /api/analyse        → Analyse     │
│  POST /api/humanize       → Text job    │
│  POST /api/humanize/image → Image job   │
│  GET  /api/results/{id}   → Poll status │
│  GET  /api/images/{file}  → Serve image │
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

---

## 📁 Project Structure

```
humaniser-agent/
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
│   ├── chat.py              # LLM chat helpers
│   ├── images.py            # Image generation helpers
│   └── litellm_client.py    # LiteLLM model client
│
└── agent-docs/
    ├── PRD.md               # Product requirements
    ├── ARCHITECTURE.md      # Architecture notes
    ├── DEPLOYMENT.md        # Deployment guide
    ├── LITELLM_GUIDE.md     # LiteLLM configuration
    └── MODELS.md            # Model selection guide
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- LiteLLM-compatible API key (OpenAI, Anthropic, etc.)

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## ⚙️ Environment Variables

Create a `.env` file in the project root (or export directly):

```env
# LLM API key (used by LiteLLM)
OPENAI_API_KEY=sk-...

# Or for Anthropic
ANTHROPIC_API_KEY=sk-ant-...
```

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

## 📄 License

MIT License — NinjaTech AI