import json
import uuid
import re
import sys
import os
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import requests

# Add parent dir to path so we can import utils
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.chat import chat_json, chat

app = FastAPI(title="AI Content Authenticity Detector", version="1.0.0")

# CORS setup — allow all origins for MVP (cross-sandbox testing requires it)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory results store
results_store: dict = {}


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

class AnalysisResponse(BaseModel):
    id: str
    overall_score: float
    confidence_label: str
    sentences: list[SentenceResult]
    summary: str
    input_type: str
    word_count: int


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

ANALYSIS_PROMPT = """You are an AI content detection expert. Analyze the following text and determine if it was written by AI or a human.

For EACH sentence, provide a score from 0-100 where:
- 0-30 = Likely written by a human
- 31-60 = Uncertain / mixed signals
- 61-100 = Likely AI-generated

Consider these signals:
- Repetitive phrasing or structure
- Overly formal or generic language
- Lack of personal anecdotes or specific details
- Perfect grammar with no colloquialisms
- Hedging language like "It's important to note"
- List-heavy or bullet-point-oriented writing
- Transitions like "Furthermore", "Moreover", "In conclusion"

Return a JSON object with this exact structure:
{
  "sentences": [
    {"text": "the sentence text", "score": 85, "label": "ai"},
    {"text": "another sentence", "score": 20, "label": "human"}
  ],
  "overall_score": 72.5,
  "summary": "A 2-3 sentence plain-language explanation of findings"
}

The "label" field should be "ai" if score >= 50, otherwise "human".
The "overall_score" should be the weighted average of all sentence scores.

TEXT TO ANALYZE:
"""


async def analyze_text(text: str) -> AnalysisResponse:
    """Analyze text for AI content using LLM."""
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
        sentence_results.append(SentenceResult(
            text=s.get("text", ""),
            score=float(s.get("score", 50)),
            label=s.get("label", "ai" if float(s.get("score", 50)) >= 50 else "human"),
        ))

    overall = float(result.get("overall_score", 50))
    summary = result.get("summary", "Analysis complete.")

    response = AnalysisResponse(
        id=result_id,
        overall_score=round(overall, 1),
        confidence_label=get_confidence_label(overall),
        sentences=sentence_results,
        summary=summary,
        input_type="text",
        word_count=len(text.split()),
    )

    # Store for later retrieval
    results_store[result_id] = response.model_dump()

    return response


# --- Endpoints ---

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "ai-content-detector"}


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

    # Extract text from HTML (basic approach)
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

    # Truncate to 50k chars
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


# --- Humanize ---

HUMANIZE_PROMPT_BASE = """You are an expert ghostwriter who makes AI-generated text sound authentically human. Your rewrites MUST be UNDETECTABLE by AI content detectors. The goal is to score BELOW 15% on AI detection.

REWRITING RULES:
1. ONLY rewrite sentences marked [AI-GENERATED] — keep [HUMAN-WRITTEN] sentences exactly as-is
2. Preserve the original meaning but COMPLETELY rephrase — don't just swap synonyms

CRITICAL TECHNIQUES — apply ALL of these aggressively:
- Use contractions everywhere (it's, don't, we're, that's, won't, I'd, can't, shouldn't)
- ELIMINATE all formal transitions: "Furthermore" "Moreover" "Additionally" "In conclusion" "It is important to note" — replace with nothing or casual connectors
- Vary sentence length DRAMATICALLY — mix very short (3-6 words) with medium ones. No uniform length.
- Use casual/conversational tone: "honestly", "look", "the thing is", "basically", "pretty much"
- Start sentences with "And", "But", "So", "Look," — real humans do this constantly
- Use specific/concrete examples instead of vague generalities
- Break compound sentences into 2-3 shorter ones
- Use dashes — like this — and ellipses for natural pauses
- Drop ALL hedging phrases ("It should be noted", "It is worth mentioning", "One could argue")
- Use active voice always. Never passive.
- Add occasional sentence fragments. For emphasis. Like this.
- Use rhetorical questions occasionally
- Include first-person perspective where appropriate ("I think", "from what I've seen")
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
Return a JSON object with this exact structure:
{
  "humanized_text": "the full text with AI sentences rewritten",
  "changes": [
    {"original": "the original AI sentence", "rewritten": "the humanized version", "technique": "technique_name"}
  ]
}

Technique names to use: "contraction_injection", "transition_removal", "sentence_splitting", "casual_connector", "active_voice", "specificity", "fragment_emphasis", "rhetorical_question", "personal_voice", "structure_variation"

Only include sentences that were actually changed in the "changes" array.

SENTENCES AND THEIR LABELS:
"""


@app.post("/api/humanize")
async def humanize_text(request: HumanizeRequest):
    """Rewrite AI-flagged sentences to sound more human."""
    # Get or create analysis
    analysis = None
    if request.result_id and request.result_id in results_store:
        analysis = results_store[request.result_id]
    else:
        # Analyze the text first
        analysis_result = await analyze_text(request.text)
        analysis = analysis_result.model_dump()

    # Build the prompt with labeled sentences
    sentences_info = ""
    for s in analysis.get("sentences", []):
        label_tag = "AI-GENERATED" if s["label"] == "ai" else "HUMAN-WRITTEN"
        sentences_info += f"[{label_tag}] {s['text']}\n"

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

    # Fallback: if LLM returned changes but didn't apply them in humanized_text,
    # reconstruct the humanized text by applying the changes manually
    if changes and humanized_text == request.text:
        patched = request.text
        for change in changes:
            if change.get("original") and change.get("rewritten"):
                patched = patched.replace(change["original"], change["rewritten"])
        humanized_text = patched

    # Re-analyse the humanized text to get the new AI score
    original_score = analysis.get("overall_score", 0)
    new_score = original_score
    try:
        reanalysis = await analyze_text(humanized_text)
        reanalysis_dict = reanalysis.model_dump()
        new_score = reanalysis_dict.get("overall_score", original_score)
    except Exception:
        pass  # If re-analysis fails, just return without new score

    response = {
        "original": request.text,
        "humanized": humanized_text,
        "changes": changes,
        "result_id": analysis.get("id", ""),
        "original_score": original_score,
        "new_score": new_score,
        "improvement": round(original_score - new_score, 1) if original_score > new_score else 0,
        "iteration": request.iteration,
    }

    # Store alongside original
    store_key = f"humanized-{analysis.get('id', '')}"
    results_store[store_key] = response

    return response


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
