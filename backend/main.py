import json
import uuid
import re
import sys
import os
import base64
import mimetypes
import asyncio
import io
import random
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
import requests

# Add parent dir to path so we can import utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.chat import chat_json, chat, chat_messages
from utils.images import generate_image

app = FastAPI(title="AI Content Authenticity Detector", version="2.0.0")

# CORS setup — allow all origins for MVP
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory results store
results_store: dict = {}

# Background jobs store for async image humanization
jobs_store: dict = {}  # job_id -> {status, result, error}

# Directory for generated/humanised images
IMAGES_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "generated_images"
IMAGES_DIR.mkdir(exist_ok=True)
app.mount("/api/images", StaticFiles(directory=str(IMAGES_DIR)), name="generated_images")


# --- Models ---

class TextAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=100000)

class URLExtractRequest(BaseModel):
    url: str

class HumanizeRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=100000)
    result_id: Optional[str] = None
    iteration: int = Field(default=1, ge=1, le=5)

class SentenceResult(BaseModel):
    text: str
    score: float
    label: str  # "ai" or "human"
    patterns: list[str] = []  # which of the 24 patterns were detected

class AnalysisResponse(BaseModel):
    id: str
    overall_score: float
    confidence_label: str
    sentences: list[SentenceResult]
    summary: str
    input_type: str
    word_count: int
    patterns_found: list[str] = []  # aggregate list of patterns detected across all sentences


# --- Image Models ---

class ImageAnalysisResponse(BaseModel):
    id: str
    overall_score: float
    confidence_label: str
    patterns_found: list[str] = []
    summary: str
    description: str          # What the image depicts (used as regeneration seed)
    image_type: str = "photograph"  # photograph, graphic_design, illustration, ui_screenshot, mixed
    input_type: str = "image"
    filename: str             # original uploaded filename
    image_url: str            # URL to original image served via /api/images/
    image_mime: str           # e.g. image/jpeg


class ImageHumanizeResponse(BaseModel):
    result_id: str
    original_score: float
    new_score: float
    improvement: float
    humanized_image_url: str  # relative URL served by /api/images/
    prompt_used: str
    changes_summary: str


# --- Helpers ---

def strip_markup(text: str) -> str:
    """Strip markdown and basic HTML so sentence splitting works on clean prose."""
    # Fenced code blocks (``` or ~~~) — remove entirely, not prose
    text = re.sub(r'```[\s\S]*?```', ' ', text)
    text = re.sub(r'~~~[\s\S]*?~~~', ' ', text)
    # Block-level HTML tags → newline so their content stays as separate lines
    text = re.sub(r'</(p|div|h[1-6]|li|blockquote|section|article|tr|td|th)>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    # Remaining HTML tags → strip
    text = re.sub(r'<[^>]+>', '', text)
    # Horizontal rules (---, ***, ___)
    text = re.sub(r'^\s*[\*\-_]{3,}\s*$', '', text, flags=re.MULTILINE)
    # ATX headings (# Heading)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Setext headings (underlined with === or ---)
    text = re.sub(r'^[=\-]{3,}\s*$', '', text, flags=re.MULTILINE)
    # Blockquotes (> text)
    text = re.sub(r'^\s*>\s?', '', text, flags=re.MULTILINE)
    # Bold/italic (**, *, __, _)
    text = re.sub(r'\*{1,3}|_{1,3}', '', text)
    # Inline code
    text = re.sub(r'`[^`]*`', '', text)
    # Images ![alt](url) — remove entirely
    text = re.sub(r'!\[[^\]]*\]\([^\)]*\)', '', text)
    # Links [text](url) → keep text
    text = re.sub(r'\[([^\]]+)\]\([^\)]*\)', r'\1', text)
    # Reference-style links [text][ref] → keep text
    text = re.sub(r'\[([^\]]+)\]\[[^\]]*\]', r'\1', text)
    # Footnote markers [^1] [1]
    text = re.sub(r'\[\^?\d+\]', '', text)
    # Bullet/numbered list markers at line start
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+[.)]\s+', '', text, flags=re.MULTILINE)
    # Collapse multiple blank lines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


# Sentence-ending punctuation split pattern:
# - Western (.!?): require trailing whitespace to avoid splitting "3.14" or "Dr. Smith"
# - CJK (。！？) and Arabic (؟ ۔) and ellipsis (…): split immediately — no space used in these scripts
_SENT_END_RE = re.compile(r'(?<=[.!?])\s+|(?<=[。！？؟۔…])')


def split_sentences(text: str) -> list[str]:
    """Split text into sentences robustly, handling markdown, HTML, and multiple languages."""
    text = strip_markup(text)

    result = []
    # Split on newlines first — separates headers, bullets, and paragraph blocks
    # that don't end in punctuation from each other
    for block in re.split(r'\n+', text):
        block = block.strip()
        if not block or len(block) < 5:
            continue
        # Within each block, split on sentence-ending punctuation + whitespace
        # This handles: English, Russian, CJK, Arabic — without splitting on
        # decimal numbers (3.14) or abbreviations (Dr. / e.g.) since those
        # are followed by digits or lowercase without a space gap
        parts = _SENT_END_RE.split(block)
        for part in parts:
            part = part.strip()
            if part and len(part) >= 5:
                result.append(part)

    return result

def get_confidence_label(score: float) -> str:
    if score >= 80:
        return "Likely AI"
    elif score >= 60:
        return "Mixed / Uncertain"
    elif score >= 40:
        return "Possibly Human"
    else:
        return "Likely Human"


# --- Upgraded Analysis Prompt (incorporates all 24 patterns from blader/humanizer SKILL.md) ---

ANALYSIS_PROMPT = """You are an expert AI content detection system. Analyze the following text and determine if each sentence was written by AI or a human.

For EACH sentence, provide a score from 0-100 where:
- 0-30 = Likely written by a human
- 31-60 = Uncertain / mixed signals
- 61-100 = Likely AI-generated

You must check for ALL 24 known AI writing patterns (based on Wikipedia's "Signs of AI writing" guide):

CONTENT PATTERNS:
1. significance_inflation — Puffed-up importance: "marking a pivotal moment", "testament to", "underscores its vital role", "evolving landscape", "setting the stage for", "indelible mark"
2. notability_namedropping — Listing media outlets without context: "featured in NYT, BBC, FT", "active social media presence"
3. superficial_ing_analyses — Fake depth via -ing phrases: "symbolizing...", "reflecting...", "showcasing...", "highlighting...", "fostering...", "contributing to..."
4. promotional_language — Advertisement tone: "nestled within", "breathtaking", "vibrant", "rich cultural heritage", "groundbreaking", "renowned", "must-visit", "stunning", "boasts"
5. vague_attributions — Weasel words: "Experts believe", "Industry observers note", "Some critics argue", "several sources suggest"
6. formulaic_challenges — Boilerplate structure: "Despite challenges... continues to thrive", "Despite its X, faces challenges typical of..."

LANGUAGE PATTERNS:
7. ai_vocabulary — High-frequency AI words: "Additionally", "Moreover", "Furthermore", "delve", "tapestry", "landscape" (abstract), "testament", "underscore", "pivotal", "crucial", "vibrant", "showcase", "foster", "garner", "interplay", "intricate", "align with", "enhance"
8. copula_avoidance — Avoiding "is/are": "serves as", "stands as", "marks", "represents", "boasts", "features", "offers" used instead of simple "is/has"
9. negative_parallelisms — "It's not just X, it's Y", "Not only... but also...", "It's not merely X, it's Y"
10. rule_of_three — Forced triads: "innovation, inspiration, and insights", "streamlining, enhancing, and fostering"
11. synonym_cycling — Excessive synonym substitution: "protagonist... main character... central figure... hero" all in same passage
12. false_ranges — "from X to Y" where X and Y aren't on a meaningful scale: "from the Big Bang to dark matter"

STYLE PATTERNS:
13. em_dash_overuse — Excessive em dashes (—) used for dramatic effect
14. boldface_overuse — Mechanical bolding of terms: **OKRs**, **KPIs**, **key insight**
15. inline_header_lists — Bullet points starting with bolded headers: "**Performance:** Performance improved..."
16. title_case_headings — All Main Words Capitalised In Headings
17. emojis — Decorative emojis in headings or bullets: 🚀, 💡, ✅
18. curly_quotes — Curly/smart quotation marks " " instead of straight " "

COMMUNICATION PATTERNS:
19. chatbot_artifacts — "I hope this helps!", "Let me know if...", "Of course!", "Certainly!", "Here is a..."
20. cutoff_disclaimers — "As of my last update", "While specific details are limited", "based on available information"
21. sycophantic_tone — "Great question!", "You're absolutely right!", "Excellent point!"

FILLER AND HEDGING:
22. filler_phrases — "In order to", "Due to the fact that", "At this point in time", "It is important to note that", "It should be noted"
23. excessive_hedging — "could potentially possibly", "might have some effect", stacking multiple hedges
24. generic_conclusions — "The future looks bright", "Exciting times lie ahead", "This represents a major step forward"

For each sentence, list which pattern IDs were detected (use the snake_case names above).

Return a JSON object with this EXACT structure:
{
  "sentences": [
    {
      "text": "the sentence text",
      "score": 85,
      "label": "ai",
      "patterns": ["ai_vocabulary", "significance_inflation"]
    },
    {
      "text": "another sentence",
      "score": 20,
      "label": "human",
      "patterns": []
    }
  ],
  "overall_score": 72.5,
  "patterns_found": ["ai_vocabulary", "significance_inflation", "filler_phrases"],
  "summary": "A 2-3 sentence plain-language explanation of findings, mentioning the most prominent AI patterns detected."
}

Rules:
- "label" = "ai" if score >= 50, otherwise "human"
- "overall_score" = weighted average of all sentence scores
- "patterns_found" = deduplicated list of all patterns found across all sentences
- Be precise: only flag patterns that are genuinely present

TEXT TO ANALYZE:
"""


BATCH_SIZE = 40  # max sentences per LLM call to keep JSON output within token limits


def _analyze_batch(batch_text: str) -> dict:
    """Analyze a single batch of text, returning the parsed JSON result."""
    prompt = ANALYSIS_PROMPT + batch_text
    return chat_json(prompt, model="claude-sonnet-4-6", max_tokens=8192)


async def analyze_text(text: str) -> AnalysisResponse:
    """Analyze text for AI content using LLM with 24-pattern detection.
    Long documents are split into batches and analyzed in parallel."""
    # Truncate very long text to avoid excessive processing
    if len(text) > 50000:
        text = text[:50000]

    sentences = split_sentences(text)
    if not sentences:
        raise HTTPException(status_code=400, detail="No valid sentences found in input")

    # Cap sentence count to keep response times reasonable
    if len(sentences) > 300:
        sentences = sentences[:300]
        text = " ".join(sentences)

    # For short texts, single call
    if len(sentences) <= BATCH_SIZE:
        try:
            result = chat_json(ANALYSIS_PROMPT + text, model="claude-sonnet-4-6", max_tokens=8192)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
        if not result or "sentences" not in result:
            raise HTTPException(status_code=500, detail="Invalid analysis response")
        all_results = [result]
    else:
        # Split into batches and analyze concurrently
        batches = []
        for i in range(0, len(sentences), BATCH_SIZE):
            batch_sentences = sentences[i:i + BATCH_SIZE]
            batches.append(" ".join(batch_sentences))

        loop = asyncio.get_event_loop()
        try:
            tasks = [loop.run_in_executor(None, _analyze_batch, batch) for batch in batches]
            all_results = await asyncio.gather(*tasks)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

        # Validate all batches returned sentences
        for r in all_results:
            if not r or "sentences" not in r:
                raise HTTPException(status_code=500, detail="Invalid analysis response from batch")

    # Merge all batch results
    result_id = str(uuid.uuid4())
    sentence_results = []
    all_patterns = set()

    for result in all_results:
        for s in result.get("sentences", []):
            score = float(s.get("score", 50))
            sentence_results.append(SentenceResult(
                text=s.get("text", ""),
                score=score,
                label=s.get("label", "ai" if score >= 50 else "human"),
                patterns=s.get("patterns", []),
            ))
            all_patterns.update(s.get("patterns", []))

    # Compute overall score as weighted average across all sentences
    if sentence_results:
        overall = sum(s.score for s in sentence_results) / len(sentence_results)
    else:
        overall = 50.0

    # Merge summaries from all batches
    summaries = [r.get("summary", "") for r in all_results if r.get("summary")]
    if len(summaries) == 1:
        summary = summaries[0]
    elif summaries:
        summary = summaries[0]  # Use first batch summary as primary
    else:
        summary = "Analysis complete."

    response = AnalysisResponse(
        id=result_id,
        overall_score=round(overall, 1),
        confidence_label=get_confidence_label(overall),
        sentences=sentence_results,
        summary=summary,
        input_type="text",
        word_count=len(text.split()),
        patterns_found=sorted(all_patterns),
    )

    # Store for later retrieval
    results_store[result_id] = response.model_dump()

    return response


# --- Humanize Prompts (full blader/humanizer SKILL.md logic + iteration support) ---

HUMANIZE_PROMPT_BASE = """You are an expert writing editor. Your job is to remove all signs of AI-generated writing and make the text sound authentically human. You follow the Wikipedia "Signs of AI writing" guide and apply a two-pass rewrite process.

STEP 1 — REWRITE: Fix all 24 AI writing patterns listed below.
STEP 2 — AUDIT: Ask yourself "What still makes this obviously AI-generated?" then fix those remaining tells.

ONLY rewrite sentences marked [AI-GENERATED]. Keep [HUMAN-WRITTEN] sentences exactly as-is.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART A — REMOVE THESE 24 AI PATTERNS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONTENT PATTERNS:
1. SIGNIFICANCE INFLATION — Remove puffed-up importance claims.
   ✗ "marking a pivotal moment in the evolution of..."
   ✓ State the plain fact instead.

2. NOTABILITY NAME-DROPPING — Replace vague media lists with specific citations.
   ✗ "cited in NYT, BBC, FT, and The Hindu"
   ✓ "In a 2024 NYT interview, she argued..."

3. SUPERFICIAL -ING ANALYSES — Remove or expand fake-depth participial phrases.
   ✗ "symbolizing..., reflecting..., showcasing..., highlighting..., fostering..."
   ✓ Remove entirely or replace with a specific sourced fact.

4. PROMOTIONAL LANGUAGE — Use neutral, factual language.
   ✗ "nestled within the breathtaking region", "vibrant", "rich cultural heritage", "groundbreaking", "stunning"
   ✓ Plain description with actual facts.

5. VAGUE ATTRIBUTIONS — Replace with specific sources.
   ✗ "Experts believe", "Industry observers note", "Some critics argue"
   ✓ Name the actual source or remove.

6. FORMULAIC CHALLENGES — Replace with specific facts.
   ✗ "Despite challenges... continues to thrive"
   ✓ Name the actual challenge and what happened.

LANGUAGE PATTERNS:
7. AI VOCABULARY — Replace these overused AI words:
   Additionally → Also / drop it | Moreover/Furthermore → drop or use "and" | delve → look at / explore
   tapestry/landscape (abstract) → be specific | testament → drop it | underscore/highlight → say it directly
   pivotal/crucial/vital → important, or just state the fact | vibrant → specific description
   showcase → show | foster → help / support | garner → get / earn | interplay → interaction
   intricate/intricacies → complex / details | align with → match / fit | enhance → improve

8. COPULA AVOIDANCE — Use simple "is/are/has" instead of elaborate substitutes.
   ✗ "serves as", "stands as", "marks", "represents", "boasts", "features", "offers"
   ✓ "is", "has", "are"

9. NEGATIVE PARALLELISMS — State the point directly.
   ✗ "It's not just about X; it's about Y"
   ✓ State Y directly.

10. RULE OF THREE — Use the natural number of items, not forced triads.
    ✗ "innovation, inspiration, and insights"
    ✓ List only what's actually relevant.

11. SYNONYM CYCLING — Repeat the clearest word rather than cycling synonyms.
    ✗ "protagonist... main character... central figure... hero" (all in same passage)
    ✓ "protagonist" (repeated when it's the clearest choice)

12. FALSE RANGES — Replace "from X to Y" with a direct list.
    ✗ "from the Big Bang to dark matter"
    ✓ "the Big Bang, star formation, and dark matter"

STYLE PATTERNS:
13. EM DASH OVERUSE — Replace most em dashes with commas or periods.
    ✗ "institutions—not the people—yet this continues—"
    ✓ "institutions, not the people, yet this continues"

14. BOLDFACE OVERUSE — Remove mechanical bolding of terms.
    ✗ "**OKRs**, **KPIs**, **BMC**"
    ✓ "OKRs, KPIs, BMC"

15. INLINE-HEADER LISTS — Convert to prose.
    ✗ "**Performance:** Performance improved significantly."
    ✓ "Performance improved significantly."

16. TITLE CASE HEADINGS — Use sentence case.
    ✗ "## Strategic Negotiations And Global Partnerships"
    ✓ "## Strategic negotiations and global partnerships"

17. EMOJIS — Remove all decorative emojis from headings and bullets.
    ✗ "🚀 **Launch Phase:**"
    ✓ "The product launches in Q3."

18. CURLY QUOTES — Replace curly quotes with straight quotes.
    ✗ said "the project"
    ✓ said "the project"

COMMUNICATION PATTERNS:
19. CHATBOT ARTIFACTS — Remove entirely.
    ✗ "I hope this helps!", "Let me know if you'd like me to expand", "Of course!", "Certainly!"
    ✓ Delete these phrases completely.

20. KNOWLEDGE-CUTOFF DISCLAIMERS — Remove or replace with real facts.
    ✗ "While specific details are limited based on available information..."
    ✓ Find the fact or remove the sentence.

21. SYCOPHANTIC TONE — Respond directly without flattery.
    ✗ "Great question! You're absolutely right!"
    ✓ Just answer the question.

FILLER AND HEDGING:
22. FILLER PHRASES — Use concise alternatives.
    "In order to" → "To" | "Due to the fact that" → "Because"
    "At this point in time" → "Now" | "It is important to note that" → drop it
    "The system has the ability to" → "The system can"

23. EXCESSIVE HEDGING — Reduce stacked qualifiers.
    ✗ "could potentially possibly be argued that... might have some effect"
    ✓ "may affect"

24. GENERIC CONCLUSIONS — End with a specific fact or plan.
    ✗ "The future looks bright. Exciting times lie ahead."
    ✓ "The company plans to open two more locations next year."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART B — ADD PERSONALITY AND SOUL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Sterile, voiceless writing is just as obvious as AI slop. After removing the patterns above, inject humanity:

- VARY RHYTHM: Mix short punchy sentences (5-8 words) with longer ones. Don't make every sentence the same length.
- HAVE OPINIONS: Don't just report facts — react to them. "I genuinely don't know how to feel about this" beats neutral listing.
- ACKNOWLEDGE COMPLEXITY: "This is impressive but also kind of unsettling" beats "This is impressive."
- USE FIRST PERSON when it fits: "I keep coming back to..." or "Here's what gets me..."
- LET SOME MESS IN: Perfect structure feels algorithmic. Tangents and asides are human.
- BE SPECIFIC ABOUT FEELINGS: Not "this is concerning" but "there's something unsettling about..."
- START sentences with "And" or "But" occasionally — real humans do this.
- USE CASUAL CONNECTORS naturally: "honestly", "look", "the thing is", "basically"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PART C — TWO-PASS AUDIT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After your first rewrite, ask: "What still makes this obviously AI-generated?"
List any remaining tells briefly, then do a second pass to fix them.
The final output should be the post-audit version.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

HUMANIZE_ITERATION_EXTRAS = {
    2: """
ROUND 2 — PREVIOUS REWRITE STILL DETECTED AS AI. Be MORE aggressive:
- Make sentences even shorter and choppier
- Add more personal opinion markers ("I'd say", "in my experience")
- Use even more informal phrasing
- Split paragraphs into shorter chunks
- Add a conversational aside or two
""",
    3: """
ROUND 3 — TEXT STILL READS AS AI AFTER 2 ROUNDS. Maximum human voice:
- Rewrite from scratch in a completely different voice
- Use colloquial language and slang where appropriate
- Add personal anecdotes or hypothetical examples
- Make it sound like a blog post or casual email, not an essay
- Every sentence should feel like someone talking, not writing
""",
}

HUMANIZE_PROMPT_FORMAT = """
Return a JSON object with this EXACT structure:
{
  "humanized_text": "the full rewritten text (post-audit, final version)",
  "changes": [
    {"original": "the original AI sentence", "rewritten": "the humanized version", "patterns_fixed": ["ai_vocabulary", "filler_phrases"]}
  ],
  "audit_notes": "Brief bullets of what was still AI-sounding after the first pass and what was fixed in the second pass"
}

Only include sentences that were actually changed in the "changes" array.
The "humanized_text" must be the complete final text, not just the changed sentences.

SENTENCES AND THEIR LABELS:
"""


# --- Image Analysis Prompt ---

IMAGE_ANALYSIS_PROMPT = """You are an expert AI image detection system. Analyse the provided image and determine whether it was generated by an AI (e.g. Midjourney, DALL-E, Stable Diffusion, Firefly) or captured/created by a human.

Score the image from 0-100 where:
- 0-30  = Likely created by a human (photograph, hand-drawn, etc.)
- 31-60 = Uncertain / mixed signals
- 61-100 = Likely AI-generated

First, classify the IMAGE TYPE — this is critical for choosing the right humanisation strategy:
- "photograph" — a realistic photo of a person, place, object, or scene
- "graphic_design" — a marketing banner, poster, advertisement, or promotional graphic with brand text, UI elements, or illustrated characters
- "illustration" — digital art, character art, concept art, or stylised artwork without brand/UI elements
- "ui_screenshot" — a screenshot of an app, website, or software interface
- "mixed" — a composite combining photography with graphic design or illustration elements

Check for ALL of these known AI image patterns:

TEXTURE & DETAIL PATTERNS:
1. texture_soup - Surfaces look hyper-detailed but structurally incoherent
2. perfect_symmetry - Unnaturally perfect bilateral symmetry in faces, architecture, or organic forms
3. uncanny_smoothness - Skin, surfaces, or materials that are impossibly smooth / blemish-free
4. repetitive_patterns - Tiling artefacts or repeated elements in backgrounds, crowds, foliage
5. inconsistent_lighting - Light sources that do not agree; shadows pointing in different directions
6. impossible_reflections - Reflections in eyes, glasses, or surfaces that do not match the scene

STRUCTURAL PATTERNS:
7. malformed_hands - Extra, missing, or deformed fingers; fused or melted-looking hands
8. text_gibberish - Text in signs, labels, books that is illegible, misspelt, or nonsensical
9. ear_deformity - Ears with unnatural structure or missing anatomical details
10. jewellery_artifacts - Necklaces, rings, or earrings that melt into skin or have broken geometry
11. background_incoherence - Background objects that are blurry blobs or contradict perspective
12. floating_elements - Objects that appear to defy gravity without context

STYLE & COMPOSITION PATTERNS:
13. painterly_haze - A soft dreamy glow or haze that sits over everything
14. oversaturation - Colours that are richer/more vivid than reality in a stylised way
15. dramatic_lighting - Cinematic studio-style lighting on subjects in everyday settings
16. stock_photo_composition - Perfectly centred subjects, clean backgrounds typical of AI training data
17. generic_aesthetic - Subjects look like idealized archetypes rather than real individuals
18. depth_of_field_abuse - Excessive bokeh or shallow depth of field applied unnaturally

METADATA PATTERNS:
19. no_exif_noise - Image appears too clean / noiseless; no grain or compression artefacts
20. watermark_remnants - Faint or partially removed watermarks from training data

Provide a detailed plain-English description of what the image shows, capturing:
- For graphic_design/mixed: brand name, colour palette, layout structure, key UI elements, character description, typography style
- For photograph: subject, setting, lighting, composition
- For illustration: style, subject, colour palette, mood

Return a JSON object with this EXACT structure:
{
  "overall_score": 85,
  "image_type": "graphic_design",
  "patterns_found": ["texture_soup", "perfect_symmetry", "malformed_hands"],
  "summary": "2-3 sentence explanation of why this image appears AI-generated, citing the most prominent patterns.",
  "description": "A promotional marketing banner for 'CareerCraft AI' featuring a purple colour scheme, an illustrated female character in business attire, LinkedIn-style UI mockup elements, skill badges, and bold white brand text centered on a light background."
}

Rules:
- "overall_score" must be a number 0-100
- "image_type" must be one of: photograph, graphic_design, illustration, ui_screenshot, mixed
- "patterns_found" must use the exact snake_case names listed above
- "description" must be detailed enough to faithfully recreate the image's content, style, and structure
- Be precise: only flag patterns that are genuinely present
"""

IMAGE_HUMANIZE_SYSTEM = """You are an expert prompt engineer specialising in making AI-generated images score LOWER on AI detection tools. Your goal is to produce prompts targeting under 30% AI detection score.

You will be given the image type, description, and detected AI patterns. You MUST apply the strategy matching the image type.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRATEGY A: PHOTOGRAPH (image_type = photograph)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Apply ALL four techniques:
1. IMPERFECTIONS: skin pores, freckles, asymmetric features, blemishes, wrinkled fabric, scuff marks, wear and tear
2. NATURAL LIGHTING: one real light source with direction (e.g. "soft overcast window light from left"), ambient colour cast, realistic shadows
3. CONTEXTUAL STORYTELLING: candid mid-action moment, specific real-world clutter, subject not posed or looking at camera
4. CAMERA SETTINGS: real camera body + lens (e.g. "Fujifilm X-T4, 35mm f/2"), ISO grain, chromatic aberration, JPEG artefacts, natural vignetting

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRATEGY B: GRAPHIC DESIGN / MIXED / ILLUSTRATION (image_type = graphic_design, mixed, illustration)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CRITICAL: Preserve the original design's purpose, brand identity, layout, and content. Do NOT convert to a photograph.
Apply these design-specific humanisation techniques:
1. HAND-CRAFTED FEEL: describe it as "hand-drawn vector illustration", "editorial flat design", "indie brand graphic", "hand-lettered layout" -- avoid "digital render" or "3D"
2. IMPERFECT TYPOGRAPHY: slightly irregular letter spacing, mixed font weights, organic baseline, as if manually composed
3. MUTED HUMAN COLOUR PALETTE: replace neon/glowing colours with muted, desaturated equivalents (e.g. "dusty mauve" instead of "electric purple", "warm off-white" instead of "pure white")
4. ILLUSTRATION IMPERFECTIONS: slight line weight variation, subtle ink bleed effect, mild paper texture or canvas grain overlay, uneven fill areas
5. COMPOSITIONAL ASYMMETRY: slightly off-balance layout, elements not pixel-perfect aligned, slight rotation on secondary elements
6. REAL-WORLD ANALOGY: describe as "scanned from a printed brand leaflet", "photographed agency mood board pinned to cork board", "torn from a design magazine"
7. PRESERVE KEY BRAND ELEMENTS: keep the same brand name text, same colour family (just muted), same layout structure, same character/subject type

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRATEGY C: UI SCREENSHOT (image_type = ui_screenshot)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Describe as a real screenshot from a slightly older OS or browser version
2. Add minor UI inconsistencies: misaligned padding, slightly different font rendering
3. Include real-world context: taskbar, notification badge, partial browser chrome
4. Add screen photography artefacts if shown as photo: slight glare, moiré pattern, slight angle

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
UNIVERSAL RULES (all types):
- NEVER use: perfect, beautiful, stunning, breathtaking, cinematic, dramatic, ultra-detailed, hyperrealistic, 8K, masterpiece, glowing, neon
- ALWAYS fix every detected AI pattern specifically
- The prompt must be at least 120 words
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Return a JSON object:
{
  "prompt": "The full detailed generation prompt applying the correct strategy",
  "changes_summary": "Which strategy was used and what specific AI patterns were eliminated"
}
"""


async def analyse_image_data(image_b64: str, mime_type: str, filename: str) -> ImageAnalysisResponse:
    """Analyse an image for AI-generation patterns using vision LLM."""

    messages = [
        {
            "role": "system",
            "content": "You must respond with valid JSON only. No markdown, no explanation."
        },
        {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{image_b64}"
                    }
                },
                {
                    "type": "text",
                    "text": IMAGE_ANALYSIS_PROMPT
                }
            ]
        }
    ]

    try:
        raw = chat_messages(messages, model="claude-sonnet-4-6", max_tokens=2048, temperature=0.0)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image analysis failed: {str(e)}")

    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines if not l.strip().startswith("```")]
        text = "\n".join(lines)

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        from utils.chat import _clean_json_string
        try:
            result = json.loads(_clean_json_string(text))
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Invalid image analysis response: {e}")

    overall = float(result.get("overall_score", 50))
    result_id = str(uuid.uuid4())

    # Persist original image to disk immediately (needed for humanize + display)
    ext = mime_type.split("/")[-1].replace("jpeg", "jpg")
    orig_filename = f"original_{result_id}.{ext}"
    orig_path = IMAGES_DIR / orig_filename
    try:
        orig_path.write_bytes(base64.b64decode(image_b64))
    except Exception:
        pass

    image_url = f"/api/images/{orig_filename}"

    response = ImageAnalysisResponse(
        id=result_id,
        overall_score=round(overall, 1),
        confidence_label=get_confidence_label(overall),
        patterns_found=result.get("patterns_found", []),
        summary=result.get("summary", "Analysis complete."),
        description=result.get("description", ""),
        image_type=result.get("image_type", "photograph"),
        filename=filename,
        image_url=image_url,
        image_mime=mime_type,
    )

    response_dict = response.model_dump()
    # Also store the local path for humanize to use
    response_dict["original_image_path"] = str(orig_path)
    results_store[result_id] = response_dict

    # Persist metadata to disk (no image blob — just the URL + meta)
    try:
        meta_path = IMAGES_DIR / f"meta_{result_id}.json"
        with open(meta_path, "w") as mf:
            json.dump(response_dict, mf)
    except Exception:
        pass

    return response


@app.post("/api/analyze/image", response_model=ImageAnalysisResponse)
async def analyze_image_endpoint(file: UploadFile = File(...)):
    """Upload an image and analyse it for AI-generation patterns."""
    allowed_types = {"image/jpeg", "image/png", "image/webp"}
    content_type = file.content_type or "image/jpeg"
    if content_type not in allowed_types:
        guessed, _ = mimetypes.guess_type(file.filename or "")
        if guessed in allowed_types:
            content_type = guessed
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image type '{content_type}'. Supported: JPEG, PNG, WebP"
            )

    raw_bytes = await file.read()
    if len(raw_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large. Maximum size is 20MB.")

    # Base64 encoding inflates size by ~33%, so 3.75MB raw → ~5MB base64
    # Compress to stay under the 5MB API limit after encoding
    MAX_API_BYTES = 3_700_000
    if len(raw_bytes) > MAX_API_BYTES:
        from PIL import Image as PILImage
        img = PILImage.open(io.BytesIO(raw_bytes)).convert("RGB")
        # Resize if very large (e.g. 8000x6000 → proportionally smaller)
        max_dim = 4096
        if max(img.size) > max_dim:
            img.thumbnail((max_dim, max_dim), PILImage.LANCZOS)
        # Compress as JPEG with decreasing quality until under limit
        for quality in (85, 75, 65, 50):
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality)
            if buf.tell() <= MAX_API_BYTES:
                break
        raw_bytes = buf.getvalue()
        content_type = "image/jpeg"

    image_b64 = base64.b64encode(raw_bytes).decode("utf-8")
    return await analyse_image_data(image_b64, content_type, file.filename or "image")


class ImageHumanizeRequest(BaseModel):
    result_id: str


def humanise_postprocess(input_path: str, output_path: str) -> None:
    """
    Apply real-world image degradation to reduce AI detector scores.
    Targets the pixel-level statistics and frequency artifacts that detectors measure.
    Steps:
      1. Subtle Poisson-like shot noise (mimics real camera sensor noise)
      2. Slight chromatic aberration (1-2px lateral RGB channel shift)
      3. Mild geometric lens distortion (barrel distortion ~0.5%)
      4. Slight colour temperature variation (warm/cool cast)
      5. JPEG re-compression at 78-85% quality (adds authentic DCT blocks)
    """
    from PIL import Image, ImageFilter
    import numpy as np

    img = Image.open(input_path).convert("RGB")
    arr = np.array(img, dtype=np.float32)

    # 1. Poisson-like shot noise — scales with pixel brightness (real sensor behaviour)
    noise_scale = random.uniform(0.018, 0.032)
    shot_noise = np.random.poisson(arr * noise_scale) / noise_scale * 0.15
    arr = np.clip(arr + shot_noise, 0, 255)

    # 2. Chromatic aberration — shift R channel right/down, B channel left/up by 1-2px
    from PIL import Image as PILImage
    img_noisy = PILImage.fromarray(arr.astype(np.uint8))
    r, g, b = img_noisy.split()
    shift_x = random.randint(1, 2)
    shift_y = random.randint(0, 1)
    # Shift red channel slightly right/down
    r_shifted = PILImage.new("L", r.size, 0)
    r_shifted.paste(r, (shift_x, shift_y))
    # Shift blue channel slightly left/up
    b_shifted = PILImage.new("L", b.size, 0)
    b_shifted.paste(b, (-shift_x, -shift_y))
    img_ca = PILImage.merge("RGB", (r_shifted, g, b_shifted))
    arr = np.array(img_ca, dtype=np.float32)

    # 3. Barrel lens distortion (subtle, ~0.4-0.7%)
    h, w = arr.shape[:2]
    cx, cy = w / 2.0, h / 2.0
    k = random.uniform(0.004, 0.007)  # barrel distortion coefficient
    y_coords, x_coords = np.mgrid[0:h, 0:w].astype(np.float32)
    x_norm = (x_coords - cx) / cx
    y_norm = (y_coords - cy) / cy
    r_sq = x_norm ** 2 + y_norm ** 2
    x_dist = x_norm * (1 + k * r_sq) * cx + cx
    y_dist = y_norm * (1 + k * r_sq) * cy + cy
    x_dist = np.clip(x_dist, 0, w - 1).astype(np.float32)
    y_dist = np.clip(y_dist, 0, h - 1).astype(np.float32)
    # Bilinear sampling
    x0 = np.floor(x_dist).astype(int)
    y0 = np.floor(y_dist).astype(int)
    x1 = np.clip(x0 + 1, 0, w - 1)
    y1 = np.clip(y0 + 1, 0, h - 1)
    dx = (x_dist - x0)[..., np.newaxis]
    dy = (y_dist - y0)[..., np.newaxis]
    distorted = (
        arr[y0, x0] * (1 - dx) * (1 - dy) +
        arr[y0, x1] * dx * (1 - dy) +
        arr[y1, x0] * (1 - dx) * dy +
        arr[y1, x1] * dx * dy
    )
    arr = np.clip(distorted, 0, 255)

    # 4. Slight colour temperature shift (warm or cool cast, subtle)
    temp_direction = random.choice(["warm", "cool", "neutral"])
    if temp_direction == "warm":
        arr[:, :, 0] = np.clip(arr[:, :, 0] * random.uniform(1.01, 1.03), 0, 255)  # boost red
        arr[:, :, 2] = np.clip(arr[:, :, 2] * random.uniform(0.97, 0.99), 0, 255)  # reduce blue
    elif temp_direction == "cool":
        arr[:, :, 2] = np.clip(arr[:, :, 2] * random.uniform(1.01, 1.03), 0, 255)  # boost blue
        arr[:, :, 0] = np.clip(arr[:, :, 0] * random.uniform(0.97, 0.99), 0, 255)  # reduce red

    # 5. Very subtle vignette (darkens edges slightly, mimics real lens falloff)
    vy, vx = np.mgrid[0:h, 0:w].astype(np.float32)
    vx_norm = (vx - cx) / cx
    vy_norm = (vy - cy) / cy
    vignette = 1.0 - random.uniform(0.04, 0.08) * (vx_norm ** 2 + vy_norm ** 2)
    vignette = np.clip(vignette, 0.85, 1.0)[..., np.newaxis]
    arr = np.clip(arr * vignette, 0, 255)

    # 6. JPEG re-compression at 78-85% quality (introduces authentic DCT block artifacts)
    final_img = Image.fromarray(arr.astype(np.uint8), "RGB")
    quality = random.randint(78, 85)
    buf = io.BytesIO()
    final_img.save(buf, format="JPEG", quality=quality, optimize=True)
    buf.seek(0)
    # Save as PNG but with JPEG-compressed data baked in (re-decode then save)
    result_img = Image.open(buf).convert("RGB")
    result_img.save(output_path, format="PNG", optimize=True)


def _run_humanize_job(job_id: str, result_id: str, analysis: dict):
    """Background task (sync): generate a humanised image and store result in jobs_store."""
    try:
        description = analysis.get("description", "")
        patterns = analysis.get("patterns_found", [])
        original_score = analysis.get("overall_score", 50)

        image_type = analysis.get("image_type", "photograph")

        # Build pattern-specific fix guidance
        pattern_fixes = {
            "texture_soup": "→ Replace chaotic texture blending with a single coherent real-world surface material",
            "perfect_symmetry": "→ Deliberately break symmetry: off-centre composition, uneven framing, candid angle",
            "uncanny_smoothness": "→ Add skin pores, fabric weave, surface grain, material roughness",
            "repetitive_patterns": "→ Introduce variation and irregularity in any repeated elements",
            "inconsistent_lighting": "→ Specify a single real light source with consistent direction and shadows",
            "impossible_reflections": "→ Remove or correct any reflections to match real physics",
            "malformed_hands": "→ Keep hands out of frame or describe 'hands naturally at sides, not visible'",
            "text_gibberish": "→ Remove all text OR specify exact legible text content explicitly",
            "ear_deformity": "→ Describe hair covering ears or keep face at angle where ears are not prominent",
            "jewellery_artifacts": "→ Remove jewellery or describe it simply: 'plain silver stud earrings'",
            "background_incoherence": "→ Describe a specific real-world background with named location details",
            "floating_elements": "→ Ensure all objects are grounded with contact shadows and physical support",
            "painterly_haze": "→ Use sharp clarity with no soft-focus glow or artistic blur",
            "oversaturation": "→ Replace vivid/neon colours with muted, desaturated, natural tones",
            "dramatic_lighting": "→ Replace with flat ambient or natural diffused lighting from one source",
            "stock_photo_composition": "→ Use candid framing -- subject not looking at camera, caught mid-task",
            "generic_aesthetic": "→ Add hyper-specific real-world details to break the generic idealised look",
            "depth_of_field_abuse": "→ Use deeper depth of field -- keep more of the scene in focus",
            "no_exif_noise": "→ Specify camera sensor noise, ISO grain, and real photographic artefacts",
            "watermark_remnants": "→ Ensure no watermark-like elements appear anywhere",
        }

        # Graphic design / illustration / mixed: add design-preservation guidance
        if image_type in ("graphic_design", "mixed", "illustration"):
            design_fixes = {
                "texture_soup": "→ Use flat, clean vector fills with slight paper grain texture overlay",
                "perfect_symmetry": "→ Slightly off-balance layout, elements not pixel-perfect, minor rotation on secondary items",
                "uncanny_smoothness": "→ Add subtle ink bleed, slight line weight variation, mild canvas grain",
                "oversaturation": "→ Desaturate all colours to muted equivalents (e.g. dusty mauve, warm beige, slate blue)",
                "dramatic_lighting": "→ Use flat editorial lighting or no lighting effect at all",
                "stock_photo_composition": "→ Asymmetric layout, white space variation, organic element placement",
                "generic_aesthetic": "→ Add brand-specific idiosyncrasies and real-world printing artefacts",
                "no_exif_noise": "→ Add subtle paper texture, slight print halftone, mild scan grain",
                "painterly_haze": "→ Use crisp editorial line work with no glow or haze",
            }
            for k, v in design_fixes.items():
                pattern_fixes[k] = v

        pattern_guidance = ""
        if patterns:
            pattern_guidance = "\n\nSPECIFIC PATTERNS TO FIX:\n"
            for p in patterns:
                if p in pattern_fixes:
                    pattern_guidance += f"- {p.replace('_', ' ').title()}: {pattern_fixes[p]}\n"

        # Strategy-specific instructions
        if image_type in ("graphic_design", "mixed", "illustration"):
            strategy_instruction = f"""IMAGE TYPE: {image_type} — USE STRATEGY B (design preservation)

CRITICAL: This is a {image_type}. Do NOT convert it to a photograph. Keep the same:
- Brand name and any text content (reproduce exactly: {description[:200] if description else 'see description'})
- Overall layout structure and composition
- Subject type (illustrated character, mascot, etc.)
- Colour family (just muted/desaturated versions)
- Purpose (marketing banner, poster, etc.)

Apply Strategy B: hand-crafted feel, muted palette, slight imperfections, real-world print/scan analogy."""
        elif image_type == "ui_screenshot":
            strategy_instruction = "IMAGE TYPE: ui_screenshot — USE STRATEGY C (screenshot realism)"
        else:
            strategy_instruction = "IMAGE TYPE: photograph — USE STRATEGY A (candid photography)"

        humanize_prompt = f"""Original image description:
{description}

{strategy_instruction}

Detected AI patterns: {', '.join(p.replace('_', ' ') for p in patterns) if patterns else 'none specific'}
Original AI detection score: {original_score}/100 — TARGET: reduce to below 30/100
{pattern_guidance}

Craft a detailed generation prompt that:
1. Applies the correct strategy for this image type
2. Fixes every detected pattern listed above
3. Preserves the original image's content, purpose, and structure
4. Is at least 120 words
5. Does NOT use: perfect, beautiful, stunning, cinematic, dramatic, ultra-detailed, hyperrealistic, 8K, masterpiece, glowing, neon
"""

        prompt_result = chat_json(humanize_prompt, model="claude-sonnet-4-6", system=IMAGE_HUMANIZE_SYSTEM)
        new_prompt = prompt_result.get("prompt", description)
        changes_summary = prompt_result.get("changes_summary", "Applied anti-AI humanisation rules.")

        output_filename = f"humanized_{result_id}.png"
        output_path = str(IMAGES_DIR / output_filename)

        generate_image(
            prompt=new_prompt,
            model="gemini-image",
            size="1024x1024",
            output=output_path,
        )

        # Post-process: apply real-world degradation to reduce AI detector fingerprints
        try:
            pp_filename = f"humanized_{result_id}.png"
            pp_path = str(IMAGES_DIR / pp_filename)
            humanise_postprocess(output_path, pp_path)
        except Exception as pp_err:
            # If post-processing fails, keep the raw generated image
            pass

        # Re-analyse new image for score using sync chat call
        new_score = original_score
        try:
            with open(output_path, "rb") as f:
                new_image_b64 = base64.b64encode(f.read()).decode("utf-8")
            # Use chat_messages directly (sync) for re-analysis
            reanalysis_messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{new_image_b64}"},
                        },
                        {"type": "text", "text": IMAGE_ANALYSIS_PROMPT},
                    ],
                }
            ]
            raw = chat_messages(reanalysis_messages, model="claude-sonnet-4-6")
            if raw:
                import re as _re
                json_match = _re.search(r'\{.*\}', raw, _re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    new_score = float(parsed.get("overall_score", original_score))
        except Exception:
            pass

        result = {
            "result_id": result_id,
            "original_score": original_score,
            "new_score": new_score,
            "improvement": round(original_score - new_score, 1) if original_score > new_score else 0,
            "humanized_image_url": f"/api/images/{output_filename}",
            "prompt_used": new_prompt,
            "changes_summary": changes_summary,
        }
        results_store[f"humanized-img-{result_id}"] = result
        jobs_store[job_id] = {"status": "done", "result": result}

    except Exception as e:
        jobs_store[job_id] = {"status": "error", "error": str(e)}


@app.post("/api/humanize/image")
async def humanize_image_endpoint(request: ImageHumanizeRequest, background_tasks: BackgroundTasks):
    """Start a background job to regenerate an image as less AI-looking. Returns a job_id to poll."""
    result_id = request.result_id

    # Load analysis from memory or disk
    analysis = results_store.get(result_id)
    if not analysis:
        meta_path = IMAGES_DIR / f"meta_{result_id}.json"
        if meta_path.exists():
            try:
                with open(meta_path, "r") as f:
                    analysis = json.load(f)
                results_store[result_id] = analysis
            except Exception:
                pass

    if not analysis:
        raise HTTPException(
            status_code=404,
            detail="Analysis result not found. Please re-upload and analyse the image."
        )
    if analysis.get("input_type") != "image":
        raise HTTPException(status_code=400, detail="This result is not an image analysis.")

    job_id = str(uuid.uuid4())
    jobs_store[job_id] = {"status": "processing"}

    # Run in background so proxy doesn't time out
    background_tasks.add_task(_run_humanize_job, job_id, result_id, analysis)

    return {"job_id": job_id, "status": "processing"}


@app.get("/api/humanize/image/status/{job_id}")
async def humanize_image_status(job_id: str):
    """Poll this endpoint to check if the humanize job is done."""
    job = jobs_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    if job["status"] == "done":
        return {"status": "done", "result": job["result"]}
    if job["status"] == "error":
        raise HTTPException(status_code=500, detail=f"Image humanization failed: {job['error']}")
    return {"status": "processing"}


@app.get("/api/results/image/{result_id}")
def get_image_result(result_id: str):
    if result_id not in results_store:
        # Try loading from disk (survives backend restarts)
        meta_path = IMAGES_DIR / f"meta_{result_id}.json"
        if meta_path.exists():
            try:
                with open(meta_path, "r") as f:
                    results_store[result_id] = json.load(f)
            except Exception:
                pass
    if result_id not in results_store:
        raise HTTPException(status_code=404, detail="Result not found")
    return results_store[result_id]


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ai-content-detector", "version": "2.1.0"}


@app.post("/api/analyze/text")
async def analyze_text_endpoint(request: TextAnalysisRequest, background_tasks: BackgroundTasks):
    """Start text analysis as a background job. Returns a job_id to poll."""
    job_id = str(uuid.uuid4())
    jobs_store[job_id] = {"status": "processing"}

    async def _run_analysis(jid: str, text: str):
        try:
            result = await analyze_text(text)
            jobs_store[jid] = {"status": "done", "result": result.model_dump()}
        except Exception as e:
            detail = getattr(e, 'detail', str(e))
            jobs_store[jid] = {"status": "error", "error": detail}

    background_tasks.add_task(_run_analysis, job_id, request.text)
    return {"job_id": job_id, "status": "processing"}


@app.get("/api/analyze/text/status/{job_id}")
async def analyze_text_status(job_id: str):
    job = jobs_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/api/upload-file")
async def upload_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """Extract text from uploaded .txt, .md, .docx, or .pdf files and analyze."""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in (".txt", ".md", ".docx", ".pdf"):
        raise HTTPException(status_code=400, detail="Unsupported file type. Please upload .txt, .md, .docx, or .pdf")

    raw = await file.read()

    if ext in (".txt", ".md"):
        text = raw.decode("utf-8", errors="replace")
    elif ext == ".docx":
        import docx
        doc = docx.Document(io.BytesIO(raw))
        text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    elif ext == ".pdf":
        import fitz
        pdf = fitz.open(stream=raw, filetype="pdf")
        text = "\n".join(page.get_text() for page in pdf)
        pdf.close()
    else:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    text = text.strip()
    if len(text) < 10:
        raise HTTPException(status_code=400, detail="Could not extract enough text from file")
    text = text[:50000]

    job_id = str(uuid.uuid4())
    jobs_store[job_id] = {"status": "processing"}

    async def _run(jid, txt, fname):
        try:
            result = await analyze_text(txt)
            rd = result.model_dump()
            rd["input_type"] = "file"
            rd["source_file"] = fname
            results_store[rd["id"]] = rd
            jobs_store[jid] = {"status": "done", "result": rd}
        except Exception as e:
            jobs_store[jid] = {"status": "error", "error": getattr(e, 'detail', str(e))}

    background_tasks.add_task(_run, job_id, text, file.filename)
    return {"job_id": job_id, "status": "processing"}


@app.post("/api/extract-url")
async def extract_url(request: URLExtractRequest, background_tasks: BackgroundTasks = None):
    """Fetch text content from a URL and analyze it."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (AI Content Detector Bot)"}
        resp = requests.get(request.url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.Timeout:
        raise HTTPException(status_code=400, detail="The website took too long to respond. Please try a different URL.")
    except requests.ConnectionError:
        raise HTTPException(status_code=400, detail="Could not connect to that website. Please check the URL and try again.")
    except requests.RequestException as e:
        status = getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
        if status == 403:
            raise HTTPException(status_code=400, detail="This website blocked our request. Please try copying and pasting the text directly instead.")
        elif status == 404:
            raise HTTPException(status_code=400, detail="Page not found. Please check the URL and try again.")
        elif status and status >= 500:
            raise HTTPException(status_code=400, detail="The website is experiencing issues. Please try again later or paste the text directly.")
        raise HTTPException(status_code=400, detail="Could not fetch that URL. Please try a different one or paste the text directly.")

    # Extract text from HTML
    from html.parser import HTMLParser

    class TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.text_parts = []
            self._skip = False

        def handle_starttag(self, tag, attrs):
            if tag in ("script", "style", "nav", "header", "footer"):
                self._skip = True

        def handle_endtag(self, tag):
            if tag in ("script", "style", "nav", "header", "footer"):
                self._skip = False

        def handle_data(self, data):
            if not self._skip:
                stripped = data.strip()
                if stripped:
                    self.text_parts.append(stripped)

    extractor = TextExtractor()
    extractor.feed(resp.text)
    extracted_text = " ".join(extractor.text_parts)

    if len(extracted_text) < 10:
        raise HTTPException(status_code=400, detail="We couldn't extract readable text from this URL. The page may require JavaScript or a login. Please try a different URL or paste the text directly.")

    extracted_text = extracted_text[:50000]

    job_id = str(uuid.uuid4())
    jobs_store[job_id] = {"status": "processing"}
    url = request.url

    async def _run(jid, txt, src_url):
        try:
            result = await analyze_text(txt)
            rd = result.model_dump()
            rd["input_type"] = "url"
            rd["source_url"] = src_url
            results_store[rd["id"]] = rd
            jobs_store[jid] = {"status": "done", "result": rd}
        except Exception as e:
            jobs_store[jid] = {"status": "error", "error": getattr(e, 'detail', str(e))}

    background_tasks.add_task(_run, job_id, extracted_text, url)
    return {"job_id": job_id, "status": "processing"}


@app.get("/api/results/{result_id}", response_model=AnalysisResponse)
def get_result(result_id: str):
    if result_id not in results_store:
        raise HTTPException(status_code=404, detail="Result not found")
    return results_store[result_id]


@app.post("/api/humanize")
async def humanize_text_endpoint(request: HumanizeRequest, background_tasks: BackgroundTasks):
    """Start text humanization as a background job. Returns a job_id to poll."""
    job_id = str(uuid.uuid4())
    jobs_store[job_id] = {"status": "processing"}

    async def _run_humanize(jid: str, text: str, result_id: Optional[str], iteration: int):
        try:
            # Get or create analysis
            analysis = None
            if result_id and result_id in results_store:
                analysis = results_store[result_id]
            else:
                analysis_result = await analyze_text(text)
                analysis = analysis_result.model_dump()

            # Build the prompt with labeled sentences (include detected patterns as hints)
            sentences_info = ""
            for s in analysis.get("sentences", []):
                label_tag = "AI-GENERATED" if s["label"] == "ai" else "HUMAN-WRITTEN"
                patterns = s.get("patterns", [])
                pattern_hint = f" [patterns: {', '.join(patterns)}]" if patterns else ""
                sentences_info += f"[{label_tag}]{pattern_hint} {s['text']}\n"

            # Build iteration-aware prompt
            prompt = HUMANIZE_PROMPT_BASE
            iteration_extra = HUMANIZE_ITERATION_EXTRAS.get(min(iteration, 3))
            if iteration_extra:
                prompt += iteration_extra
            prompt += HUMANIZE_PROMPT_FORMAT + sentences_info

            result = chat_json(prompt, model="claude-sonnet-4-6")

            if not result or "humanized_text" not in result:
                jobs_store[jid] = {"status": "error", "error": "Invalid humanization response"}
                return

            humanized_text = result.get("humanized_text", text)
            changes = result.get("changes", [])
            audit_notes = result.get("audit_notes", "")

            # Fallback: reconstruct humanized text from changes if LLM didn't apply them
            if changes and humanized_text == text:
                patched = text
                for change in changes:
                    if change.get("original") and change.get("rewritten"):
                        patched = patched.replace(change["original"], change["rewritten"])
                humanized_text = patched

            # Re-analyse the humanized text to get the new AI score
            original_score = analysis.get("overall_score", 0)
            new_score = original_score
            new_patterns = []
            try:
                reanalysis = await analyze_text(humanized_text)
                reanalysis_dict = reanalysis.model_dump()
                new_score = reanalysis_dict.get("overall_score", original_score)
                new_patterns = reanalysis_dict.get("patterns_found", [])
            except Exception:
                pass

            response = {
                "original": text,
                "humanized": humanized_text,
                "changes": changes,
                "audit_notes": audit_notes,
                "result_id": analysis.get("id", ""),
                "original_score": original_score,
                "new_score": new_score,
                "improvement": round(original_score - new_score, 1) if original_score > new_score else 0,
                "iteration": iteration,
                "original_patterns": analysis.get("patterns_found", []),
                "remaining_patterns": new_patterns,
            }

            store_key = f"humanized-{analysis.get('id', '')}"
            results_store[store_key] = response

            jobs_store[jid] = {"status": "done", "result": response}
        except Exception as e:
            jobs_store[jid] = {"status": "error", "error": f"Humanization failed: {str(e)}"}

    background_tasks.add_task(_run_humanize, job_id, request.text, request.result_id, request.iteration)
    return {"job_id": job_id, "status": "processing"}


@app.get("/api/humanize/status/{job_id}")
async def humanize_text_status(job_id: str):
    job = jobs_store.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)