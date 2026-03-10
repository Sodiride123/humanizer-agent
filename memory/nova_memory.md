# Nova Memory

## Current Sprint
- Sprint 4: IN PROGRESS (Advanced Humanization — 24-Pattern System)
- PRD Status: Active v1.3 (updated with Sprint 4 features 2026-03-10)
- Reference: blader/humanizer (github.com/blader/humanizer, 8.2k stars)

## Sprint 1 (CLOSED)
- All 5 issues closed (#8, #9, #10, #12, #13)
- QA: 9/9 tests passed, detection accuracy 82.5%

## Sprint 2 (CLOSED)
- All 4 issues closed (#15, #16, #17, #18)
- QA: 11/11 tests passed, 0 failures. Sprint 1 regression 9/9 still passing.
- Features: POST /api/humanize endpoint, Humanize button on results page, toggle view, copy-to-clipboard, changes list
- **Bolt's URL:** https://3000-db601214-e21f-4ac9-ba6d-d4dcd687818e.app.super.betamyninja.ai

## Sprint 3 (CLOSED)
- All 4 issues closed (#24, #25, #28, #29)
- QA: 16/16 tests passed, 0 failures. Sprint 1+2 regression all passing.
- **Features:** Enhanced humanization prompts (contractions, varied structure, casual connectors), re-analyse loop (score progression, Humanize Again button), technique labels, iteration-aware prompting
- **Score improvement:** 86.2% → 28.3% (57.9pt drop in round 1)
- **Technique labels:** contraction_injection, structure_variation, casual_connector, specificity
- **Bolt commits:** 8d70d05 (initial), 20ad09a (full iteration loop)
- **Published repo:** https://github.com/patrick-ninjatech/humaniser-agent

## Sprint 4 (IN PROGRESS)
- Issues: #1 (Pixel design), #2 (Bolt backend), #3 (Bolt frontend), #4 (Scout QA)
- **Scope:** Integrate blader/humanizer 24-pattern system into our humanize prompts
- **Key features:** 24 AI writing pattern detection, two-pass rewrite (pattern removal + anti-AI audit), expanded technique labels by category, pattern count badges
- **Target:** Humanized text scores <10% AI (down from <20% in Sprint 3)
- **Reference:** blader/humanizer SKILL.md (Wikipedia's "Signs of AI writing" guide)

## Team Status
- **Pixel**: Assigned #1 — Design for 24-pattern UI updates
- **Bolt**: Assigned #2 (backend) + #3 (frontend) — 24-pattern prompt + two-pass rewrite + UI
- **Scout**: Assigned #4 — QA for pattern coverage + regression + E2E
- **Nova**: Sprint 4 scoped, issues created, PRD updated to v1.3

## Session Log
### Session 1 (2026-03-09)
- Onboarding, stakeholder interview, PRD drafted and approved
- Created Sprint 1 issues, cleaned up duplicates

### Session 2 (2026-03-09 ~09:37)
- Scout escalated Bolt MIA. Bolt came back. Sprint 1 coordination.

### Session 3 (2026-03-09 ~10:07)
- Stakeholder status request. Bolt bug #2 blocker. Design misalignment flagged.

### Session 4 (2026-03-09 ~10:44)
- All blockers fixed. Scout final QA: 9/9 pass. MVP ready.

### Session 5 (2026-03-09 ~11:05)
- Deployed app for stakeholder. Fixed "Failed to fetch" with Next.js proxy rewrites.

### Session 6 (2026-03-09 ~11:23)
- Stakeholder requested humanize button feature
- Sprint 1 closed, Sprint 2 created (#15-#18)
- Bolt completed backend + frontend for humanize (commit 5cbf13d)
- Scout QA: 11/11 pass, 0 failures. All Sprint 2 issues closed.
- Shared working URL with stakeholder for testing

### Session 7 (2026-03-09 ~13:27)
- Stakeholder asked how to make humanized content more human
- Stakeholder approved all 4 enhancements for Sprint 3
- Created Sprint 3 canonical issues: #24, #25, #28, #29
- Cleaned up duplicate issues from concurrent Nova instances
- Bolt shipped initial prompt improvements (commit 8d70d05)
- Updated PRD to v1.2, pushed to humaniser-agent repo

### Session 8 (2026-03-09 ~14:05)
- Bolt completed #25 and #28 (commit 20ad09a)
- Closed #25 and #28. Flagged missing push of 20ad09a to humaniser-agent repo.

### Session 9 (2026-03-09 ~14:33)
- Scout completed QA: 16/16 tests pass, 0 failures
- Closed #24 and #29 — all Sprint 3 issues now closed
- Posted Sprint 3 completion update for stakeholder
- Score drop: 86.2% → 28.3% (57.9pt improvement in round 1)
- Sprint 3 officially COMPLETE

### Session 10 (2026-03-10)
- Stakeholder shared github.com/blader/humanizer (8.2k stars) — Claude Code skill for removing AI writing signs
- Based on Wikipedia's "Signs of AI writing" guide, detects 24 patterns
- Stakeholder approved: "scope it out and implement"
- Fetched full SKILL.md — 24 patterns across 5 categories + two-pass rewrite + voice injection
- Updated PRD to v1.3 with section 6.2.2 (Advanced Humanization)
- Created Sprint 4 issues: #1 (Pixel), #2 (Bolt backend), #3 (Bolt frontend), #4 (Scout QA)
- Created sprint-4 label, fixed GitHub auth
- Posted Sprint 4 kickoff to Slack
- Image Detection bumped to Sprint 5 per stakeholder priority

## Decisions Made
- Sprint 1: Text Detection only (P0)
- Sprint 2: Humanize Feature (P0)
- Sprint 3: Humanization Quality Enhancements (P0)
- Sprint 4: Advanced Humanization (24-pattern system from blader/humanizer, per stakeholder)
- Sprint 5 (planned): Image Detection (P1) — bumped from Sprint 4
- Tech stack: Next.js (port 3000) + FastAPI (port 8000)
- Sandbox proxy: always use Next.js rewrites to proxy API calls
- GitHub assignees: only patrick-ninjatech is collaborator — use labels + issue body
- Humanization target: <20% AI score on re-analysis, with <15% showing "Looks Human!" badge
- Code published to: patrick-ninjatech/humaniser-agent (per stakeholder request)

## Pending Items
- Sprint 4 in progress — waiting for Pixel, Bolt, Scout to pick up issues
- Push updated PRD v1.3 to humaniser-agent repo when auth allows

## Key Notes
- Channel: #humaniser-agent
- Workspace: NinjaSquad Marketing
- Source repo: patrick-ninjatech/Nova-humaniser-agent (orchestration)
- Published repo: patrick-ninjatech/humaniser-agent (app code, per stakeholder)
- Stakeholder user ID: U0AF7RUELP5
- Design constraint: SVG icons only, no emojis in UI
- Multiple Nova instances may run concurrently — check Slack for recent messages before posting to avoid duplicates
