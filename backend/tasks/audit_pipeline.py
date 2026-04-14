"""
Celery audit pipeline.

Full flow:
  1. Pull ad data from Google Ads API
  2. Scrape unique landing pages (bounded concurrency)
  3. Score each ad-page pair with the LLM
  4. Calculate wasted spend
  5. Persist results and update audit status
"""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from celery import Celery
from sqlalchemy import select

from config import get_settings
from database import AsyncSessionLocal
from models import Audit, AdPagePair, AuditStatus, ConnectedAccount
from services.google_ads import GoogleAdsService
from services.page_scraper import scrape_pages_batch
from services.coherence_scorer import CoherenceScorer
from services.spend_calculator import estimate_wasted_spend, calculate_audit_totals
from services.token_encryption import decrypt_token

logger = logging.getLogger(__name__)
settings = get_settings()

celery_app = Celery(
    "adcoherence",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.timezone = "UTC"


def _run_async(coro):
    """Run an async coroutine from a sync Celery task."""
    return asyncio.get_event_loop().run_until_complete(coro)


@celery_app.task(bind=True, name="tasks.run_audit", max_retries=2)
def run_audit(self, audit_id: str):
    """
    Main Celery task. Takes an audit UUID string and runs the full pipeline.
    """
    logger.info("Starting audit %s", audit_id)
    _run_async(_run_audit_async(audit_id, self))


async def _run_audit_async(audit_id: str, task):
    async with AsyncSessionLocal() as db:
        # 1. Load audit + connected account
        result = await db.execute(
            select(Audit).where(Audit.id == audit_id)
        )
        audit = result.scalar_one_or_none()
        if not audit:
            logger.error("Audit %s not found", audit_id)
            return

        result = await db.execute(
            select(ConnectedAccount).where(ConnectedAccount.id == audit.connected_account_id)
        )
        account = result.scalar_one_or_none()
        if not account:
            await _fail_audit(db, audit, "Connected account not found")
            return

        audit.status = AuditStatus.RUNNING
        await db.commit()

        try:
            refresh_token = decrypt_token(account.encrypted_refresh_token)

            # 2. Pull ad data
            logger.info("Fetching Google Ads data for account %s", account.google_ads_customer_id)
            ads_service = GoogleAdsService(
                developer_token=settings.google_ads_developer_token,
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                refresh_token=refresh_token,
            )
            ads = await ads_service.fetch_all_ad_data(account.google_ads_customer_id)
            logger.info("Fetched %d ads", len(ads))

            if not ads:
                await _fail_audit(db, audit, "No enabled ads found in this account")
                return

            # 3. Scrape unique landing pages
            unique_urls = list({ad["final_url"] for ad in ads})
            logger.info("Scraping %d unique landing pages", len(unique_urls))
            scraped_pages = await scrape_pages_batch(unique_urls, concurrency=3)

            # 4. Score + calculate waste for each ad
            scorer = CoherenceScorer()
            pair_summaries = []

            for ad in ads:
                url = ad["final_url"]
                page = scraped_pages.get(url)
                if not page:
                    continue

                page_data = {
                    "url": page.url,
                    "page_title": page.page_title,
                    "h1": page.h1,
                    "h2s": page.h2s,
                    "meta_description": page.meta_description,
                    "above_fold_text": page.above_fold_text,
                    "cta_texts": page.cta_texts,
                    "offer_mentions": page.offer_mentions,
                    "load_time_ms": page.load_time_ms,
                    "mobile_friendly": page.mobile_friendly,
                }

                # LLM scoring (sync call inside async context — Groq client is sync)
                loop = asyncio.get_event_loop()
                score_result = await loop.run_in_executor(
                    None, scorer.score, ad, page_data
                )

                # Wasted spend
                waste = estimate_wasted_spend(ad.get("keywords", []), score_result["overall_score"])

                # Persist this pair
                pair = AdPagePair(
                    audit_id=audit.id,
                    campaign_name=ad["campaign_name"],
                    ad_group_name=ad["ad_group_name"],
                    ad_headlines=ad["ad_headlines"],
                    ad_descriptions=ad["ad_descriptions"],
                    final_url=url,
                    keywords=ad.get("keywords", []),
                    page_title=page.page_title,
                    page_h1=page.h1,
                    page_h2s=page.h2s,
                    meta_description=page.meta_description,
                    above_fold_text=page.above_fold_text,
                    cta_texts=page.cta_texts,
                    offer_mentions=page.offer_mentions,
                    page_load_time_ms=page.load_time_ms,
                    mobile_friendly=page.mobile_friendly,
                    screenshot_path=None,  # TODO: upload to Supabase Storage
                    scrape_error=page.error,
                    overall_score=score_result["overall_score"],
                    headline_match_score=score_result["headline_match"]["score"],
                    headline_match_diagnosis=score_result["headline_match"]["diagnosis"],
                    offer_consistency_score=score_result["offer_consistency"]["score"],
                    offer_consistency_diagnosis=score_result["offer_consistency"]["diagnosis"],
                    cta_alignment_score=score_result["cta_alignment"]["score"],
                    cta_alignment_diagnosis=score_result["cta_alignment"]["diagnosis"],
                    keyword_relevance_score=score_result["keyword_relevance"]["score"],
                    keyword_relevance_diagnosis=score_result["keyword_relevance"]["diagnosis"],
                    tone_continuity_score=score_result["tone_continuity"]["score"],
                    tone_continuity_diagnosis=score_result["tone_continuity"]["diagnosis"],
                    top_recommendations=score_result["top_recommendations"],
                    estimated_monthly_waste=waste.estimated_monthly_waste,
                    waste_type=waste.waste_type,
                    additional_conversions_monthly=waste.additional_conversions_monthly,
                )
                db.add(pair)

                pair_summaries.append({
                    "overall_score": score_result["overall_score"],
                    "estimated_monthly_waste": waste.estimated_monthly_waste,
                    "additional_conversions_monthly": waste.additional_conversions_monthly,
                    "landing_page_experience": _worst_lpe(ad.get("keywords", [])),
                })

            await db.flush()

            # 5. Update audit summary
            totals = calculate_audit_totals(pair_summaries)
            audit.status = AuditStatus.COMPLETED
            audit.total_ads = len(ads)
            audit.avg_coherence_score = totals["avg_coherence_score"]
            audit.total_wasted_spend_monthly = totals["total_wasted_spend_monthly"]
            audit.ads_below_average_lp_experience = sum(
                1 for p in pair_summaries if p.get("landing_page_experience") == "BELOW_AVERAGE"
            )
            audit.completed_at = datetime.now(timezone.utc)
            await db.commit()
            logger.info("Audit %s completed successfully", audit_id)

        except Exception as exc:
            logger.exception("Audit %s failed: %s", audit_id, exc)
            await _fail_audit(db, audit, str(exc))


async def _fail_audit(db, audit: Audit, message: str):
    audit.status = AuditStatus.FAILED
    audit.error_message = message
    await db.commit()


def _worst_lpe(keywords: list[dict]) -> str:
    """Return the worst landing page experience across all keywords."""
    priority = {"BELOW_AVERAGE": 0, "AVERAGE": 1, "ABOVE_AVERAGE": 2, "UNKNOWN": 3, "UNSPECIFIED": 4}
    lpes = [kw.get("landing_page_experience", "UNKNOWN") for kw in keywords]
    return min(lpes, key=lambda x: priority.get(x, 99), default="UNKNOWN")
