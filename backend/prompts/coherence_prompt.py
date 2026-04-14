"""
Prompt template for Llama 3.3 (via Groq API) coherence scoring.

Usage:
    from prompts.coherence_prompt import build_prompt
    messages = build_prompt(ad_data, page_data)
    # Pass messages to Groq chat completions API
"""

import json
from typing import Any


SYSTEM_PROMPT = """You are a conversion rate optimization (CRO) expert who specializes in Google Ads campaign optimization. Your job is to evaluate how well an ad's message aligns with its landing page — a concept called "message match" or "ad coherence."

Poor message match is one of the most common and expensive mistakes in paid search. When a visitor clicks an ad and the landing page doesn't immediately reinforce what the ad promised, they leave — wasting the advertiser's spend.

You will be given:
1. The ad copy (headlines and descriptions) from a Google Responsive Search Ad
2. The keywords the ad group targets (including Quality Score data if available)
3. Structured content extracted from the landing page

Your task is to score the ad-to-page coherence across 5 dimensions and provide specific, actionable diagnoses.

SCORING DIMENSIONS:
1. Headline Match (30% weight): Does the landing page H1/title immediately reflect the primary message of the ad headlines? Would a visitor know they're in the right place?
2. Offer Consistency (25% weight): If the ad mentions a specific offer (discount, free trial, free shipping, etc.), is that exact offer prominently visible above the fold on the landing page?
3. CTA Alignment (20% weight): Does the landing page's primary call-to-action logically continue the ad's call to action? If the ad says "Get a Free Quote," does the page have a quote form visible?
4. Keyword Relevance (15% weight): Are the target keywords naturally present in the landing page content? This directly affects Google's Quality Score landing page experience component.
5. Visual/Tone Continuity (10% weight): Based on the ad copy's tone (urgent, professional, casual, luxury, playful), does the page content match that tone?

SCORING RULES:
- Score each dimension 0-100 (0 = completely misaligned, 100 = perfect alignment)
- Overall score = (headline_match * 0.30) + (offer_consistency * 0.25) + (cta_alignment * 0.20) + (keyword_relevance * 0.15) + (tone_continuity * 0.10)
- Be specific in diagnoses — quote actual text from the ad and page, not generic advice
- If data is missing (e.g. no QS data, no offers in ad), score that dimension at 50 and note the reason
- Recommendations must be concrete and implementable — not vague like "improve your landing page"

You MUST respond with valid JSON only. No markdown, no commentary outside the JSON structure."""


def build_prompt(ad_data: dict[str, Any], page_data: dict[str, Any]) -> list[dict]:
    """
    Build the messages array for the Groq chat completions call.

    ad_data keys: campaign_name, ad_group_name, ad_headlines, ad_descriptions,
                  final_url, keywords
    page_data keys: url, page_title, h1, h2s, meta_description, above_fold_text,
                    cta_texts, offer_mentions, load_time_ms, mobile_friendly
    """
    # Format keywords for the prompt — include QS data if available
    keywords_summary = _format_keywords(ad_data.get("keywords", []))

    user_content = f"""ANALYZE THIS AD-TO-PAGE PAIR:

## AD COPY
Campaign: {ad_data.get('campaign_name', 'Unknown')}
Ad Group: {ad_data.get('ad_group_name', 'Unknown')}

Headlines:
{_format_list(ad_data.get('ad_headlines', []))}

Descriptions:
{_format_list(ad_data.get('ad_descriptions', []))}

## KEYWORDS TARGETED
{keywords_summary}

## LANDING PAGE CONTENT
URL: {page_data.get('url', '')}
Page Title: {page_data.get('page_title', '(none)')}
H1: {page_data.get('h1', '(none)')}
H2s: {_format_list(page_data.get('h2s', []))}
Meta Description: {page_data.get('meta_description', '(none)')}

Above-the-Fold Text (first viewport):
{page_data.get('above_fold_text', '(empty)')[:2000]}

CTA Buttons Found: {_format_inline_list(page_data.get('cta_texts', []))}
Promotional Offers Detected: {_format_inline_list(page_data.get('offer_mentions', []))}
Mobile Friendly: {page_data.get('mobile_friendly', 'unknown')}
Page Load Time: {page_data.get('load_time_ms', 'unknown')}ms

## REQUIRED OUTPUT FORMAT
Respond with this exact JSON structure (no other text):
{{
    "overall_score": <integer 0-100>,
    "headline_match": {{
        "score": <integer 0-100>,
        "diagnosis": "<specific explanation referencing actual ad and page text>"
    }},
    "offer_consistency": {{
        "score": <integer 0-100>,
        "diagnosis": "<specific explanation>"
    }},
    "cta_alignment": {{
        "score": <integer 0-100>,
        "diagnosis": "<specific explanation>"
    }},
    "keyword_relevance": {{
        "score": <integer 0-100>,
        "diagnosis": "<specific explanation>"
    }},
    "tone_continuity": {{
        "score": <integer 0-100>,
        "diagnosis": "<specific explanation>"
    }},
    "top_recommendations": [
        "<specific, actionable recommendation 1>",
        "<specific, actionable recommendation 2>",
        "<specific, actionable recommendation 3>"
    ]
}}"""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]


def _format_list(items: list[str]) -> str:
    if not items:
        return "  (none)"
    return "\n".join(f"  - {item}" for item in items)


def _format_inline_list(items: list[str]) -> str:
    if not items:
        return "(none)"
    return ", ".join(f'"{item}"' for item in items[:10])


def _format_keywords(keywords: list[dict]) -> str:
    if not keywords:
        return "  (no keyword data available)"

    lines = []
    for kw in keywords[:20]:  # Cap at 20 to keep prompt size reasonable
        qs = kw.get("quality_score")
        lpe = kw.get("landing_page_experience", "UNKNOWN")
        text = kw.get("keyword_text", "")
        match = kw.get("match_type", "")

        qs_str = f"QS: {qs}/10" if qs else "QS: N/A"
        lpe_str = f"Landing Page Exp: {lpe}"

        # Flag below-average LPE prominently
        flag = " ⚠️ BELOW AVERAGE LPE" if lpe == "BELOW_AVERAGE" else ""
        lines.append(f"  [{match}] \"{text}\" — {qs_str}, {lpe_str}{flag}")

    return "\n".join(lines)
