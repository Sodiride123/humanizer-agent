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
- **2026-03-09 Session 11**: Stakeholder asked for better humanization quality. Initial improvements: enhanced prompt, re-analysis, score banner. Commit 8d70d05.
- **2026-03-09 Session 12**: Sprint 3 (#25 #28) — iteration-aware humanize with escalating prompt, technique labels, full re-analyse loop UI (score progression, Humanize Again, Looks Human badge). Score: 93.3% -> 25.0% round 1. Commit 20ad09a.
- **2026-03-09 Session 13**: Pushed latest code to published repo (patrick-ninjatech/humaniser-agent) per Nova's request. Merged Nova's PRD update. Added 'published' remote. Scout and Pixel acknowledged Sprint 3 assignments.

## Current Tasks
| Task | Issue | Status |
|------|-------|--------|
| FastAPI Backend - Text Analysis API | #12 (Nova repo) | Complete |
| Next.js Frontend - Input & Results | #10 (Nova repo) | Complete |
| Backend: POST /api/humanize endpoint | #16 (Nova repo) | Complete |
| Frontend: Humanize button + output | #17 (Nova repo) | Complete |
| Enhanced humanization prompt | #25 (Nova repo) | Complete |
| Re-analyse after humanize loop | #28 (Nova repo) | Complete |

## Technical Decisions
- Using ninja-standard model (API key restricted to ninja-cline models)
- SessionStorage for passing analysis results to results page
- In-memory dict for results store (MVP - no DB needed)
- CORS: allow_origins=["*"] for MVP
- Next.js rewrites proxy /api/* to localhost:8000
- Humanize prompt: iteration-aware with escalating aggressiveness (round 1: base, round 2: more informal, round 3: complete rewrite)
- Technique labels: contraction_injection, transition_removal, sentence_splitting, casual_connector, active_voice, specificity, fragment_emphasis, rhetorical_question, personal_voice, structure_variation

## Architecture
### Backend (port 8000)
- FastAPI app at backend/main.py
- Endpoints: POST /api/analyze/text, POST /api/extract-url, POST /api/humanize, GET /api/results/{id}, GET /api/health
- Humanize: accepts iteration param (1-5), re-analyses output, returns before/after scores + technique labels

### Frontend (port 3000)
- Next.js + TypeScript + Tailwind CSS
- next.config.ts: rewrites /api/* to localhost:8000/api/*
- lib/api.ts: relative URLs (empty base)
- Pages: / (input), /results/[id] (score + overlay + humanize + score progression + iteration loop)

## Environment
- Sandbox ID: db601214-e21f-4ac9-ba6d-d4dcd687818e
- Frontend URL: https://3000-db601214-e21f-4ac9-ba6d-d4dcd687818e.app.super.betamyninja.ai
- Backend URL: https://8000-db601214-e21f-4ac9-ba6d-d4dcd687818e.app.super.betamyninja.ai

## Pending Items
- Sprint 3 #25 and #28 complete — awaiting Scout QA on #29
- Target: sub-20% AI score (currently achieving ~25% in round 1)
- Pixel design #24 — may need UI refinement after design delivery
