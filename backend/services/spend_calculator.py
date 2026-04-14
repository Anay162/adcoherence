"""
Wasted spend estimation based on Quality Score + coherence score.

Logic:
  - Google penalizes/rewards CPCs based on Quality Score relative to QS 5 (baseline)
  - For keywords with BELOW_AVERAGE landing page experience, fixing the page
    conservatively adds 2 QS points, reducing CPC by the multiplier difference
  - For ads with low coherence scores but AVERAGE LPE, estimate conversion lift
"""

from dataclasses import dataclass
from typing import Optional

# CPC multipliers relative to QS 5 (the "average" baseline).
# Source: industry-standard estimates widely used in PPC analysis.
QS_CPC_MULTIPLIERS = {
    1: 4.00,
    2: 2.50,
    3: 1.67,
    4: 1.25,
    5: 1.00,
    6: 0.83,
    7: 0.71,
    8: 0.63,
    9: 0.56,
    10: 0.50,
}

MICROS_PER_DOLLAR = 1_000_000


@dataclass
class WastedSpendResult:
    waste_type: str  # "cpc_savings" | "conversion_lift" | "none"
    estimated_monthly_waste: float  # dollars
    additional_conversions_monthly: Optional[float] = None
    explanation: str = ""


def qs_to_cpc_multiplier(qs: int) -> float:
    return QS_CPC_MULTIPLIERS.get(max(1, min(10, qs)), 1.0)


def estimate_wasted_spend(keywords: list[dict], coherence_score: int) -> WastedSpendResult:
    """
    Estimate monthly wasted spend for an ad-to-page pair.

    keywords: list of keyword dicts (from Google Ads service output)
    coherence_score: 0-100 overall coherence score
    """
    total_cpc_savings = 0.0
    total_additional_conversions = 0.0
    below_avg_keywords = 0

    for kw in keywords:
        lpe = kw.get("landing_page_experience", "UNKNOWN")
        qs = kw.get("quality_score")
        clicks = kw.get("clicks_30d", 0) or 0
        avg_cpc_micros = kw.get("avg_cpc_micros", 0) or 0
        conversions = kw.get("conversions_30d", 0.0) or 0.0

        avg_cpc = avg_cpc_micros / MICROS_PER_DOLLAR

        if lpe == "BELOW_AVERAGE" and qs is not None and clicks > 0 and avg_cpc > 0:
            below_avg_keywords += 1
            current_qs = max(1, min(10, qs))
            potential_qs = min(current_qs + 2, 10)  # Conservative: assume fixing page adds 2 QS points

            current_multiplier = qs_to_cpc_multiplier(current_qs)
            potential_multiplier = qs_to_cpc_multiplier(potential_qs)

            # Savings per click = current_cpc * (1 - potential_multiplier / current_multiplier)
            savings_per_click = avg_cpc * (1 - potential_multiplier / current_multiplier)
            monthly_savings = savings_per_click * clicks
            total_cpc_savings += monthly_savings

        elif coherence_score < 60 and conversions > 0:
            # Even without QS penalty, poor coherence hurts conversion rate
            # Estimate 15% CVR improvement from better alignment
            total_additional_conversions += conversions * 0.15

    if total_cpc_savings > 0.50:  # Only report if savings > $0.50/month (avoid noise)
        return WastedSpendResult(
            waste_type="cpc_savings",
            estimated_monthly_waste=round(total_cpc_savings, 2),
            explanation=(
                f"{below_avg_keywords} keyword(s) have Below Average landing page experience. "
                f"Improving this page to Average+ could save ~${total_cpc_savings:.0f}/month "
                f"by raising Quality Score by 1-2 points."
            ),
        )

    if total_additional_conversions > 0.1:
        return WastedSpendResult(
            waste_type="conversion_lift",
            estimated_monthly_waste=0.0,
            additional_conversions_monthly=round(total_additional_conversions, 1),
            explanation=(
                f"Coherence score is {coherence_score}/100. Better message match could "
                f"improve conversion rate by ~15%, yielding ~{total_additional_conversions:.1f} "
                f"additional conversions/month."
            ),
        )

    return WastedSpendResult(
        waste_type="none",
        estimated_monthly_waste=0.0,
        explanation="No significant waste detected for this ad-page pair.",
    )


def calculate_audit_totals(pairs: list[dict]) -> dict:
    """
    Aggregate wasted spend across all ad-page pairs for the audit summary.
    pairs: list of dicts with keys: estimated_monthly_waste, overall_score,
           additional_conversions_monthly
    """
    total_waste = sum(p.get("estimated_monthly_waste") or 0.0 for p in pairs)
    total_extra_conversions = sum(p.get("additional_conversions_monthly") or 0.0 for p in pairs)
    scores = [p["overall_score"] for p in pairs if p.get("overall_score") is not None]
    avg_score = sum(scores) / len(scores) if scores else 0.0

    # Estimate savings from fixing the worst 5 pairs
    sorted_by_waste = sorted(pairs, key=lambda p: p.get("estimated_monthly_waste") or 0.0, reverse=True)
    top5_savings = sum(p.get("estimated_monthly_waste") or 0.0 for p in sorted_by_waste[:5])

    return {
        "total_wasted_spend_monthly": round(total_waste, 2),
        "total_additional_conversions_monthly": round(total_extra_conversions, 1),
        "avg_coherence_score": round(avg_score, 1),
        "top5_potential_savings": round(top5_savings, 2),
    }
