"""
LLM-based coherence scoring using Groq API (Llama 3.3 70B).
"""

import json
import logging
import re
from typing import Any, Optional

from groq import Groq

from config import get_settings
from prompts.coherence_prompt import build_prompt

logger = logging.getLogger(__name__)

MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 1024


def _extract_json(text: str) -> dict:
    """
    Extract JSON from the model response.
    Handles cases where the model wraps JSON in markdown code fences.
    """
    # Strip markdown code fences if present
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

    return json.loads(text)


def _validate_score_response(data: dict) -> dict:
    """
    Validate and clamp the LLM response to expected schema.
    Returns a cleaned dict with safe defaults for missing fields.
    """
    def clamp(val, lo=0, hi=100) -> int:
        try:
            return max(lo, min(hi, int(val)))
        except (TypeError, ValueError):
            return 50

    def get_dim(key: str) -> dict:
        dim = data.get(key, {})
        return {
            "score": clamp(dim.get("score", 50)),
            "diagnosis": str(dim.get("diagnosis", "No diagnosis provided.")),
        }

    dims = ["headline_match", "offer_consistency", "cta_alignment", "keyword_relevance", "tone_continuity"]
    weights = [0.30, 0.25, 0.20, 0.15, 0.10]

    cleaned_dims = {d: get_dim(d) for d in dims}

    # Recalculate overall score from weighted components (don't trust LLM math)
    calculated_overall = sum(
        cleaned_dims[d]["score"] * w for d, w in zip(dims, weights)
    )
    # Use LLM's stated overall_score as a sanity check; if wildly off, use calculated
    llm_overall = clamp(data.get("overall_score", calculated_overall))
    overall = llm_overall if abs(llm_overall - calculated_overall) < 15 else int(calculated_overall)

    recs = data.get("top_recommendations", [])
    if not isinstance(recs, list):
        recs = []
    recs = [str(r) for r in recs[:3]]

    return {
        "overall_score": overall,
        **cleaned_dims,
        "top_recommendations": recs,
    }


class CoherenceScorer:
    def __init__(self):
        self._client = Groq(api_key=get_settings().groq_api_key)

    def score(self, ad_data: dict[str, Any], page_data: dict[str, Any]) -> dict[str, Any]:
        """
        Synchronous scoring call (runs inside Celery worker).
        Returns validated score dict.
        """
        messages = build_prompt(ad_data, page_data)

        try:
            response = self._client.chat.completions.create(
                model=MODEL,
                messages=messages,
                max_tokens=MAX_TOKENS,
                temperature=0.1,  # Low temperature for consistent, deterministic scoring
                response_format={"type": "json_object"},
            )
            raw_content = response.choices[0].message.content
            data = _extract_json(raw_content)
            return _validate_score_response(data)

        except json.JSONDecodeError as exc:
            logger.error("Groq returned invalid JSON: %s", exc)
            return _fallback_score("LLM returned invalid JSON")
        except Exception as exc:
            logger.error("Groq scoring error: %s", exc)
            return _fallback_score(str(exc))


def _fallback_score(reason: str) -> dict:
    """Return a neutral score when the LLM call fails."""
    neutral = {"score": 50, "diagnosis": f"Scoring unavailable: {reason}"}
    return {
        "overall_score": 50,
        "headline_match": neutral,
        "offer_consistency": neutral,
        "cta_alignment": neutral,
        "keyword_relevance": neutral,
        "tone_continuity": neutral,
        "top_recommendations": ["Scoring failed — please re-run the audit."],
    }
