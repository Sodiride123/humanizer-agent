# Bolt Memory

## Session Log
- **2026-03-09 Session 1**: First wake-up. Completed onboarding. Slack, GitHub, dashboard all working. PRD not yet written, no GitHub issues assigned. Posted to Slack requesting Nova to create PRD and tasks.
- **2026-03-09 Session 2**: PRD approved, issues assigned. Built FastAPI backend (port 8000) and Next.js frontend (port 3000). Both services running. Code committed and pushed. Signaled Scout for QA.
- **2026-03-09 Session 3**: Fixed critical bug #2 — lib/api.ts missing from git due to root .gitignore lib/ pattern. Pushed fix. Replied to Scout and stakeholder. Pixel delivered design mockups.
- **2026-03-09 Session 4**: Fixed CORS (opened to allow_origins=["*"] for cross-sandbox QA). Applied Pixel dark theme design to both pages. All pushed. Scout QA passed 9/9.
- **2026-03-09 Session 5**: Stakeholder testing — "Failed to fetch" due to cross-origin sandbox auth. Added Next.js API proxy. Commit 0510dbe.
- **2026-03-09 Session 6**: Sprint 2 — Built humanize feature. Backend POST /api/humanize + frontend button. Both #16 and #17 complete. Commit 5cbf13d.
- **2026-03-09 Session 7**: Fixed edge case where LLM returned changes but didn't apply them in humanized_text field. Commit 47ec23b.
- **2026-03-09 Session 8**: Sprint 2 officially complete. Scout QA passed 11/11. All issues closed.
- **2026-03-09 Session 11**: Stakeholder asked for better humanization quality. Shipped: (1) enhanced prompt with contractions, casual connectors, varied sentence length, active voice, dropped formal transitions; (2) re-analysis after humanize showing before/after AI scores; (3) score comparison banner on frontend. Tested: 93.8% to 42.0% (51.8pt improvement). Commit 8d70d05.

## Current Tasks
| Task | Issue | Status |
|------|-------|--------|
| FastAPI Backend - Text Analysis API | #12 (Nova repo) | Complete |
| Next.js Frontend - Input & Results | #10 (Nova repo) | Complete |
| Backend: POST /api/humanize endpoint | #16 (Nova repo) | Complete |
| Frontend: Humanize button + output | #17 (Nova repo) | Complete |
| Humanize quality + re-analyse score | stakeholder request | Complete |

## Technical Decisions
- Using ninja-standard model (API key restricted to ninja-cline models)
- SessionStorage for passing analysis results to results page
- In-memory dict for results store (MVP - no DB needed)
- CORS: allow_origins=["*"] for MVP
- Next.js rewrites proxy /api/* to localhost:8000
- Humanize prompt uses aggressive techniques: contractions, casual connectors, varied sentence length, active voice

## Architecture
### Backend (port 8000)
- FastAPI app at backend/main.py
- Endpoints: POST /api/analyze/text, POST /api/extract-url, POST /api/humanize, GET /api/results/{id}, GET /api/health
- Humanize endpoint re-analyses output and returns before/after AI scores

### Frontend (port 3000)
- Next.js + TypeScript + Tailwind CSS
- next.config.ts: rewrites /api/* to localhost:8000/api/*
- lib/api.ts: relative URLs (empty base)
- Pages: / (input), /results/[id] (score + overlay + humanize + score comparison)

## Environment
- Sandbox ID: db601214-e21f-4ac9-ba6d-d4dcd687818e
- Frontend URL: https://3000-db601214-e21f-4ac9-ba6d-d4dcd687818e.app.super.betamyninja.ai
- Backend URL: https://8000-db601214-e21f-4ac9-ba6d-d4dcd687818e.app.super.betamyninja.ai

## Pending Items
- Humanization quality improvements shipped — awaiting stakeholder feedback
- Nova to scope Sprint 3 formally
- Pixel design polish items (collapsible changes, download TXT) — potential future enhancements
