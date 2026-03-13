import json
import uuid
import re
import sys
import os
import base64
import mimetypes
from typing import Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
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

# Directory for generated/humanised images
IMAGES_DIR = Path(os.path.dirname(os.path.abspath(__file__))) / "generated_images"
IMAGES_DIR.mkdir(exist_ok=True)
app.mount("/api/images", StaticFiles(directory=str(IMAGES_DIR)), name="generated_images")


# --- Models ---

class TextAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=50000)

class URLExtractRequest(BaseModel):
    url: str

class HumanizeRequest(BaseModel):
    text: str = Field(..., min_length=10, max_length=50000)
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
    input_type: str = "image"
    filename: str             # original uploaded filename
    image_data: str           # base64 of original image (for display)
    image_mime: str           # e.g. image/jpeg


class ImageHumanizeResponse(BaseModel):
    result_id: str
    original_score: float
    new_score: float
    improvement: float
    humanized_image_url: str  # relative URL served by /api/images/
    humanized_image_data: str # base64 for immediate display
    prompt_used: str
    changes_summary: str


# --- Helpers ---

def split_sentences(text: str) -> list[str]:
    """Split text into sentences."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return [s.strip() for s in sentences if s.strip()]

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


async def analyze_text(text: str) -> AnalysisResponse:
    """Analyze text for AI content using LLM with 24-pattern detection."""
    sentences = split_sentences(text)
    if not sentences:
        raise HTTPException(status_code=400, detail="No valid sentences found in input")

    prompt = ANALYSIS_PROMPT + text

    try:
        result = chat_json(prompt, model="ninja-standard")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    if not result or "sentences" not in result:
        raise HTTPException(status_code=500, detail="Invalid analysis response")

    result_id = str(uuid.uuid4())
    sentence_results = []
    for s in result.get("sentences", []):
        score = float(s.get("score", 50))
        sentence_results.append(SentenceResult(
            text=s.get("text", ""),
            score=score,
            label=s.get("label", "ai" if score >= 50 else "human"),
            patterns=s.get("patterns", []),
        ))

    overall = float(result.get("overall_score", 50))
    summary = result.get("summary", "Analysis complete.")
    patterns_found = result.get("patterns_found", [])

    response = AnalysisResponse(
        id=result_id,
        overall_score=round(overall, 1),
        confidence_label=get_confidence_label(overall),
        sentences=sentence_results,
        summary=summary,
        input_type="text",
        word_count=len(text.split()),
        patterns_found=patterns_found,
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

Provide a brief plain-English description of what the image shows (used as the seed for regeneration).

Return a JSON object with this EXACT structure:
{
  "overall_score": 85,
  "patterns_found": ["texture_soup", "perfect_symmetry", "malformed_hands"],
  "summary": "2-3 sentence explanation of why this image appears AI-generated, citing the most prominent patterns.",
  "description": "A photorealistic portrait of a young woman with long auburn hair, wearing a white blouse, soft studio lighting, blurred green background."
}

Rules:
- "overall_score" must be a number 0-100
- "patterns_found" must use the exact snake_case names listed above
- "description" should be detailed enough to regenerate a similar image
- Be precise: only flag patterns that are genuinely present
"""

IMAGE_HUMANIZE_SYSTEM = """You are an expert prompt engineer specialising in making AI-generated images look more authentically human.

Given an image description and its detected AI patterns, craft a new image generation prompt that will produce a result that looks LESS AI-generated.

Apply these anti-AI rules:
- Add natural imperfections: slight asymmetry, real skin texture, natural lighting variation
- Avoid cinematic/dramatic lighting - use flat, natural, or ambient light instead
- Request authentic grain/noise like a real camera would have
- Avoid overly saturated colours - request muted, natural tones
- For portraits: add minor natural features (pores, slight asymmetry, natural hair flyaways)
- Request candid/documentary framing rather than stock-photo composition
- Avoid "perfect" or "beautiful" descriptors - use specific, grounded descriptors instead
- Add specificity that AI training data lacks (e.g. specific time of day, specific real-world imperfections)
- Reference real photographic styles (e.g. "shot on 35mm film", "documentary photo", "street photography")

Return a JSON object:
{
  "prompt": "The full image generation prompt to use",
  "changes_summary": "Brief description of what was changed to make it look less AI-generated"
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
        raw = chat_messages(messages, model="ninja-standard", max_tokens=2048, temperature=0.0)
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

    response = ImageAnalysisResponse(
        id=result_id,
        overall_score=round(overall, 1),
        confidence_label=get_confidence_label(overall),
        patterns_found=result.get("patterns_found", []),
        summary=result.get("summary", "Analysis complete."),
        description=result.get("description", ""),
        filename=filename,
        image_data=image_b64,
        image_mime=mime_type,
    )

    results_store[result_id] = response.model_dump()
    return response


@app.post("/api/analyze/image", response_model=ImageAnalysisResponse)
async def analyze_image_endpoint(file: UploadFile = File(...)):
    """Upload an image and analyse it for AI-generation patterns."""
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    content_type = file.content_type or "image/jpeg"
    if content_type not in allowed_types:
        guessed, _ = mimetypes.guess_type(file.filename or "")
        if guessed in allowed_types:
            content_type = guessed
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image type '{content_type}'. Supported: JPEG, PNG, WebP, GIF"
            )

    raw_bytes = await file.read()
    if len(raw_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image too large. Maximum size is 10MB.")

    image_b64 = base64.b64encode(raw_bytes).decode("utf-8")
    return await analyse_image_data(image_b64, content_type, file.filename or "image")


@app.post("/api/humanize/image")
async def humanize_image_endpoint(result_id: str = Form(...)):
    """Regenerate an analysed image to look less AI-generated."""
    if result_id not in results_store:
        raise HTTPException(status_code=404, detail="Analysis result not found.")

    analysis = results_store[result_id]

    if analysis.get("input_type") != "image":
        raise HTTPException(status_code=400, detail="This result is not an image analysis.")

    description = analysis.get("description", "")
    patterns = analysis.get("patterns_found", [])
    original_score = analysis.get("overall_score", 50)

    humanize_prompt = f"""Original image description:
{description}

Detected AI patterns: {', '.join(patterns) if patterns else 'none specific'}
Original AI score: {original_score}/100

Craft a new image generation prompt that will produce a similar image but looking MORE human/authentic and LESS AI-generated.
"""

    try:
        prompt_result = chat_json(humanize_prompt, model="ninja-standard", system=IMAGE_HUMANIZE_SYSTEM)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Prompt generation failed: {str(e)}")

    new_prompt = prompt_result.get("prompt", description)
    changes_summary = prompt_result.get("changes_summary", "Applied anti-AI humanisation rules.")

    output_filename = f"humanized_{result_id}.png"
    output_path = str(IMAGES_DIR / output_filename)

    try:
        generate_image(
            prompt=new_prompt,
            model="gemini-image",
            size="1024x1024",
            output=output_path,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {str(e)}")

    with open(output_path, "rb") as f:
        new_image_b64 = base64.b64encode(f.read()).decode("utf-8")

    new_score = original_score
    try:
        reanalysis = await analyse_image_data(new_image_b64, "image/png", output_filename)
        new_score = reanalysis.overall_score
    except Exception:
        pass

    response = {
        "result_id": result_id,
        "original_score": original_score,
        "new_score": new_score,
        "improvement": round(original_score - new_score, 1) if original_score > new_score else 0,
        "humanized_image_url": f"/api/images/{output_filename}",
        "humanized_image_data": new_image_b64,
        "prompt_used": new_prompt,
        "changes_summary": changes_summary,
    }

    results_store[f"humanized-img-{result_id}"] = response
    return response


@app.get("/api/results/image/{result_id}")
def get_image_result(result_id: str):
    if result_id not in results_store:
        raise HTTPException(status_code=404, detail="Result not found")
    return results_store[result_id]


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ai-content-detector", "version": "2.1.0"}


@app.post("/api/analyze/text", response_model=AnalysisResponse)
async def analyze_text_endpoint(request: TextAnalysisRequest):
    return await analyze_text(request.text)


@app.post("/api/extract-url")
async def extract_url(request: URLExtractRequest):
    """Fetch text content from a URL and analyze it."""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (AI Content Detector Bot)"}
        resp = requests.get(request.url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch URL: {str(e)}")

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
        raise HTTPException(status_code=400, detail="Could not extract enough text from URL")

    extracted_text = extracted_text[:50000]

    result = await analyze_text(extracted_text)
    result_dict = result.model_dump()
    result_dict["input_type"] = "url"
    result_dict["source_url"] = request.url
    results_store[result_dict["id"]] = result_dict
    return result_dict


@app.get("/api/results/{result_id}", response_model=AnalysisResponse)
def get_result(result_id: str):
    if result_id not in results_store:
        raise HTTPException(status_code=404, detail="Result not found")
    return results_store[result_id]


@app.post("/api/humanize")
async def humanize_text(request: HumanizeRequest):
    """Rewrite AI-flagged sentences using the full 24-pattern humanizer + iteration support + two-pass audit."""
    # Get or create analysis
    analysis = None
    if request.result_id and request.result_id in results_store:
        analysis = results_store[request.result_id]
    else:
        analysis_result = await analyze_text(request.text)
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
    iteration_extra = HUMANIZE_ITERATION_EXTRAS.get(min(request.iteration, 3))
    if iteration_extra:
        prompt += iteration_extra
    prompt += HUMANIZE_PROMPT_FORMAT + sentences_info

    try:
        result = chat_json(prompt, model="ninja-standard")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Humanization failed: {str(e)}")

    if not result or "humanized_text" not in result:
        raise HTTPException(status_code=500, detail="Invalid humanization response")

    humanized_text = result.get("humanized_text", request.text)
    changes = result.get("changes", [])
    audit_notes = result.get("audit_notes", "")

    # Fallback: reconstruct humanized text from changes if LLM didn't apply them
    if changes and humanized_text == request.text:
        patched = request.text
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
        "original": request.text,
        "humanized": humanized_text,
        "changes": changes,
        "audit_notes": audit_notes,
        "result_id": analysis.get("id", ""),
        "original_score": original_score,
        "new_score": new_score,
        "improvement": round(original_score - new_score, 1) if original_score > new_score else 0,
        "iteration": request.iteration,
        "original_patterns": analysis.get("patterns_found", []),
        "remaining_patterns": new_patterns,
    }

    store_key = f"humanized-{analysis.get('id', '')}"
    results_store[store_key] = response

    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)