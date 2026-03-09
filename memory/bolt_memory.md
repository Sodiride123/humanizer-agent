# Bolt Memory

## Session Log
- **2026-03-09 Session 1**: First wake-up. Completed onboarding. Slack, GitHub, dashboard all working. PRD not yet written, no GitHub issues assigned. Posted to Slack requesting Nova to create PRD and tasks.
- **2026-03-09 Session 2**: PRD approved, issues assigned. Built FastAPI backend (port 8000) and Next.js frontend (port 3000). Both services running. Code committed and pushed. Signaled Scout for QA.
- **2026-03-09 Session 3**: Fixed critical bug #2 — `lib/api.ts` missing from git due to root `.gitignore` `lib/` pattern. Pushed fix. Replied to Scout and stakeholder. Pixel delivered design mockups.
- **2026-03-09 Session 4**: Fixed CORS (opened to allow_origins=["*"] for cross-sandbox QA). Applied Pixel's dark theme design to both pages — landing page with hero, purple accent, feature cards; results page with two-column layout, 240px gauge, stats cards, sentence overlay with color-coded borders. All pushed. Scout QA passed 9/9.
- **2026-03-09 Session 5**: Stakeholder testing — "Failed to fetch" due to cross-origin sandbox auth. Added Next.js API proxy (rewrites /api/* to localhost:8000). Frontend now uses relative URLs, eliminating CORS entirely. Shared correct sandbox URLs. Commit 0510dbe.

## Current Tasks
| Task | Issue | Status |
|------|-------|--------|
| FastAPI Backend - Text Analysis API | #12 (Nova repo) | Complete |
| Next.js Frontend - Input & Results | #10 (Nova repo) | Complete |

## Technical Decisions
- Using `ninja-standard` model for text analysis (API key restricted to ninja-cline models)
- SessionStorage for passing analysis results to results page (avoids extra API call)
- In-memory dict for results store (MVP - no DB needed for Sprint 1)
- CORS: allow_origins=["*"] for MVP (cross-sandbox testing requires it)
- Next.js rewrites proxy /api/* to localhost:8000 — eliminates cross-origin issues for end users

## Architecture
### Backend (port 8000)
- FastAPI app at `backend/main.py`
- Endpoints: POST /api/analyze/text, POST /api/extract-url, GET /api/results/{id}, GET /api/health
- Uses utils/chat.py for LLM-powered analysis

### Frontend (port 3000)
- Next.js + TypeScript + Tailwind CSS
- next.config.ts: rewrites /api/* to localhost:8000/api/*
- lib/api.ts: relative URLs (empty base) — all API calls go through same origin
- Pages: / (input with 3 modes), /results/[id] (score + overlay + summary)

## Environment
- Sandbox ID: db601214-e21f-4ac9-ba6d-d4dcd687818e
- Stage: beta
- Frontend URL: https://3000-db601214-e21f-4ac9-ba6d-d4dcd687818e.app.super.betamyninja.ai
- Backend URL: https://8000-db601214-e21f-4ac9-ba6d-d4dcd687818e.app.super.betamyninja.ai

## Bug Fixes
- **Bug #2** (Scout repo): `frontend/lib/api.ts` missing from git — root `.gitignore` had `lib/` pattern. Fixed with negation `!frontend/lib/`. Commit 0732f31.
- **CORS fix**: Opened to allow_origins=["*"] for cross-sandbox QA. Commit 82dcdbb.
- **Proxy fix**: Added Next.js rewrites to proxy /api/* through same origin. Commit 0510dbe.

## Pending Items
- Stakeholder testing the live app — waiting for feedback
- Sprint 1 MVP complete — ready for Sprint 2 planning (Image Detection per Nova)
