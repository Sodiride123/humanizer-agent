# Product Requirements Document (PRD)

## AI Content Authenticity Detector

**Version:** 1.3
**Author:** Nova (PM)
**Date:** 2026-03-10
**Status:** Active - Proceeding with implementation

---

## 1. Problem Statement

With the rapid proliferation of AI-generated content across text, images, and video, users need a reliable way to determine whether content they encounter is AI-generated or human-created. There is no single, consumer-friendly tool that handles all three content types with clear visual feedback and confidence scoring.

## 2. Vision

Build a web application that acts as an AI content authenticity detector. Users can submit text, images, or video, and the system analyzes the content to determine:

1. **Overall AI likelihood** - A percentage score indicating how likely the content is AI-generated
2. **Visual overlay** - Highlighting which specific parts are AI-generated vs human-created
3. **Summary report** - A plain-language breakdown of the analysis findings

## 3. Target User

**General consumers** - Anyone who wants to verify whether content they encounter online is AI-generated. This includes social media users, students, journalists, and curious individuals.

## 4. Input Formats (All Supported)

| Input Method | Description |
|-------------|-------------|
| **Text paste** | User pastes text directly into a text area |
| **File upload** | User uploads files (text files, images, video files) |
| **URL input** | User provides a URL and the system fetches + analyzes the content |

## 5. Content Type Priority

| Priority | Type | MVP Phase |
|----------|------|-----------|
| **P0 - Highest** | Text Detection | Sprint 1 |
| **P0 - Highest** | Text Humanize | Sprint 2 |
| **P0 - Highest** | Enhanced Humanization & Re-analyse Loop | Sprint 3 |
| **P0 - Highest** | Advanced Humanization (24-pattern system) | Sprint 4 |
| **P1 - High** | Image Detection | Sprint 5 |
| **P2 - Medium** | Video Detection | Sprint 6 |

## 6. Core Features

### 6.1 Text Detection (P0 - MVP)

- Paste or upload text for analysis
- Provide URL to extract and analyze text content
- Display overall AI-generated percentage score
- Highlight specific sentences/paragraphs that are likely AI-generated (visual overlay with color coding)
- Summary report explaining detection reasoning
- Support for long-form text (articles, essays, etc.)

### 6.2 Text Humanization (P0 - Sprint 2)

- After AI detection analysis, user can click "Humanize" to rewrite AI-flagged text
- System uses LLM to paraphrase AI-detected sentences to sound more natural/human-written
- Preserves original meaning and tone
- Display both original and humanized versions (side-by-side or toggle view)
- Highlight specific changes made during humanization
- Copy-to-clipboard for humanized text
- **Endpoint:** `POST /api/humanize`
- **Input:** Original text + analysis result ID
- **Output:** Humanized text + list of changes made
- **Model:** `claude-sonnet` for rewriting

### 6.2.1 Enhanced Humanization (P0 - Sprint 3)

- **Improved rewriting quality** to produce more convincingly human text:
  - Vary sentence length and structure aggressively (mix short and long sentences)
  - Inject natural contractions (don't, it's, they're) and filler words ("I think", "probably", "kind of")
  - Eliminate overly formal transitions ("Furthermore", "Moreover", "Additionally") in favor of casual connectors ("Also", "Plus", "But")
  - Add occasional sentence fragments, vary paragraph lengths, prefer active voice
- **Re-analyse after humanize loop:**
  - After humanization, user clicks "Re-analyse" to run humanized text through detection again
  - Display score progression (e.g., "82% -> 15% -> 8%")
  - "Humanize Again" button when score > 15% threshold
  - Success badge ("Looks Human!") when score drops below 15%
  - Iteration counter showing current round of humanization
- **Technique labels** in API response showing which techniques were applied per change
- **Iteration-aware prompting** — subsequent humanize rounds use different strategies
- **Endpoint updates:**
  - `POST /api/humanize` accepts optional `iteration` parameter
  - Response includes `techniques_applied` field per change
- **Target:** Humanized text scores <20% AI on re-analysis

### 6.2.2 Advanced Humanization — 24-Pattern System (P0 - Sprint 4)

Based on [blader/humanizer](https://github.com/blader/humanizer) (8.2k stars), which implements Wikipedia's "Signs of AI writing" guide (WikiProject AI Cleanup). Expands our 4-technique Sprint 3 system to cover 24 documented AI writing patterns with a two-pass rewrite process.

- **Content patterns to detect and remove (6):**
  1. Significance inflation ("pivotal moment", "enduring testament", "evolving landscape")
  2. Notability name-dropping (listing media outlets without context)
  3. Superficial -ing analyses ("highlighting...", "showcasing...", "reflecting...")
  4. Promotional/advertisement language ("nestled", "vibrant", "breathtaking", "groundbreaking")
  5. Vague attributions ("Experts believe", "Industry reports suggest")
  6. Formulaic "challenges and future prospects" sections ("Despite challenges... continues to thrive")

- **Language and grammar patterns to detect and remove (6):**
  7. AI vocabulary overuse ("Additionally", "delve", "crucial", "tapestry", "underscore", "landscape")
  8. Copula avoidance ("serves as", "stands as", "boasts" instead of "is"/"has")
  9. Negative parallelisms ("It's not just X, it's Y")
  10. Rule of three overuse (forcing ideas into groups of three)
  11. Synonym cycling / elegant variation (excessive synonym substitution)
  12. False ranges ("from X to Y" where X and Y aren't on a scale)

- **Style patterns to detect and remove (6):**
  13. Em dash overuse
  14. Overuse of boldface
  15. Inline-header vertical lists (bolded headers with colons)
  16. Title Case in headings
  17. Emoji decoration in headings/bullets
  18. Curly quotation marks

- **Communication patterns to detect and remove (3):**
  19. Collaborative artifacts ("I hope this helps!", "Let me know if...")
  20. Knowledge-cutoff disclaimers ("as of [date]", "While specific details are limited...")
  21. Sycophantic/servile tone ("Great question!", "You're absolutely right!")

- **Filler and hedging patterns to detect and remove (3):**
  22. Filler phrases ("In order to", "Due to the fact that", "It is important to note")
  23. Excessive hedging ("could potentially possibly be argued that... might")
  24. Generic positive conclusions ("The future looks bright", "Exciting times lie ahead")

- **Two-pass rewrite process:**
  - Pass 1: Rewrite text applying all 24 pattern removals + add personality/voice
  - Pass 2: Anti-AI audit — "What makes this obviously AI generated?" → identify remaining tells → final revision
  - The two-pass approach catches patterns that survive the first rewrite

- **Voice and personality injection:**
  - Have opinions, not just neutral reporting
  - Vary rhythm (short punchy + longer flowing sentences)
  - Acknowledge complexity and mixed feelings
  - Use first person when appropriate
  - Allow imperfection — tangents, asides, half-formed thoughts
  - Be specific about feelings, not generic

- **Expanded technique labels:** Update `techniques_applied` to include all 24 pattern categories
- **Target:** Humanized text scores <10% AI on re-analysis (down from <20% in Sprint 3)
- **Reference:** [blader/humanizer SKILL.md](https://github.com/blader/humanizer/blob/main/SKILL.md)

### 6.3 Image Detection (P1)

- Upload image file or provide image URL
- Display overall AI-generated percentage score
- Visual heatmap overlay showing AI-generated regions vs human-created regions
- Summary report with detection details (model signatures, artifacts found, etc.)
- Support for common formats: JPEG, PNG, WebP

### 6.4 Video Detection (P2)

- Upload video file or provide video URL
- Frame-by-frame or segment analysis
- Timeline view showing AI vs human segments
- Overall AI-generated percentage score
- Summary report with temporal analysis

### 6.5 Shared Features (All Types)

- Clean, modern UI with a single input interface
- Content type auto-detection
- Analysis history (recent scans)
- Shareable results (unique URL per analysis)
- Loading states with progress indicators

## 7. Output Format

Every analysis produces three components:

### 7.1 Confidence Score
- Large, prominent percentage display (0-100%)
- Color-coded: Green (likely human) / Yellow (mixed) / Red (likely AI)
- Confidence level label: "Likely Human", "Possibly AI", "Likely AI"

### 7.2 Visual Overlay
- **Text:** Highlighted spans with color-coded background (red for AI, green for human)
- **Image:** Heatmap overlay with opacity slider
- **Video:** Timeline bar with color-coded segments

### 7.3 Summary Report
- Plain-language explanation of findings
- Key indicators detected
- Breakdown by section/region
- Downloadable as PDF (nice-to-have)

## 8. Technical Architecture

### 8.1 Frontend
- **Framework:** Next.js (React)
- **Port:** 3000
- **Styling:** Tailwind CSS
- **Icons:** SVG icons only (no emojis in the UI)
- **Key pages:**
  - `/` - Landing page with input interface
  - `/results/[id]` - Analysis results page
  - `/history` - Recent analyses (nice-to-have)

### 8.2 Backend
- **Framework:** FastAPI (Python)
- **Port:** 8000
- **Key endpoints:**
  - `POST /api/analyze/text` - Text analysis
  - `POST /api/humanize` - Humanize AI-detected text (Sprint 2)
  - `POST /api/analyze/image` - Image analysis (P1)
  - `POST /api/analyze/video` - Video analysis (P2)
  - `POST /api/extract-url` - Fetch content from URL
  - `GET /api/results/{id}` - Get analysis results
  - `GET /api/health` - Health check

### 8.3 AI Models (via utils/ library)

| Task | Model | Usage |
|------|-------|-------|
| Text analysis reasoning | `claude-sonnet` | Analyze text patterns, structure, repetition |
| Text humanization | `claude-sonnet` | Rewrite AI-flagged sentences to sound human |
| Image analysis | `claude-sonnet` (vision) | Detect AI artifacts in images |
| Embeddings for similarity | `embed-small` | Compare against known AI writing patterns |
| Image generation (test data) | `gemini-image` | Generate test images for validation |

**Reference:** See [LITELLM_GUIDE.md](LITELLM_GUIDE.md) for utility library usage and [MODELS.md](MODELS.md) for full model catalog.

### 8.4 Deployment

- Frontend on port 3000, backend on port 8000
- CORS configured per [DEPLOYMENT.md](DEPLOYMENT.md)
- Frontend dynamically detects backend URL from browser hostname
- Backend reads sandbox metadata for CORS origins
- Both services bind to `0.0.0.0`

## 9. Design Requirements

- **Clean, modern, minimal UI** - Focus on the analysis workflow
- **SVG icons only** - No emojis anywhere in the UI
- **Color palette:** Professional, trustworthy (blues, greens, with red/yellow for warnings)
- **Responsive:** Desktop-first but must work on tablet and mobile
- **Key states:** Empty, loading/analyzing, results, error
- **Accessibility:** Proper contrast ratios, semantic HTML, keyboard navigation

## 10. User Flow

```
1. User lands on homepage
2. User selects input method (paste text / upload file / enter URL)
3. User submits content
4. Loading state with progress indicator
5. Results page displays:
   a. Confidence score (large, prominent)
   b. Visual overlay (highlighted text / image heatmap)
   c. Summary report
6. User clicks "Humanize" to rewrite AI-flagged text
7. User clicks "Re-analyse" to check updated AI score
8. If score > 15%, user clicks "Humanize Again" to iterate
9. When score < 15%, success badge shown ("Looks Human!")
10. User can copy humanized text, share results, or start a new analysis
```

## 11. Acceptance Criteria (MVP - Text Detection)

- [ ] User can paste text and get AI detection results
- [ ] User can upload a text file and get AI detection results
- [ ] User can provide a URL and have text extracted and analyzed
- [ ] Results show overall AI percentage score (0-100%)
- [ ] Results highlight which sentences/paragraphs are likely AI-generated (color overlay)
- [ ] Results include a plain-language summary report
- [ ] UI uses SVG icons (no emojis)
- [ ] Frontend and backend deploy correctly with working CORS
- [ ] Responsive design works on desktop, tablet, and mobile
- [ ] No JS errors, console errors, or network errors
- [ ] Analysis completes within 15 seconds for typical content

## 12. Out of Scope (MVP)

- User authentication / accounts
- API keys for external consumers
- Batch processing
- Browser extension
- Mobile native app
- Paid tiers / billing

## 13. Success Metrics

- Analysis accuracy > 80% on known AI-generated vs human text
- Page load time < 2 seconds
- Analysis time < 15 seconds for text
- No critical bugs in main user flow

## 14. Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| AI detection accuracy varies | Use multiple signals (statistical, LLM reasoning, embeddings) and show confidence range |
| Large files slow down analysis | Set file size limits, show progress indicators |
| URL fetch fails (paywalls, etc.) | Graceful error handling, suggest file upload as fallback |
| `gpt-image` intermittent errors | Use `gemini-image` as default, `gpt-image` as fallback only |

---

**Stakeholder Approval Required:** Please review and confirm this PRD before I create GitHub issues for the team.
