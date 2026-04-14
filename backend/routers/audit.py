"""
Audit endpoints:
  POST /audits                → trigger a new audit
  GET  /audits/{id}          → get audit status + summary
  GET  /audits/{id}/pairs    → get paginated ad-page pairs (sorted by waste / score)
  GET  /audits/latest        → get most recent audit for the user's account
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from database import get_db
from models import Audit, AdPagePair, AuditStatus, ConnectedAccount, User
from routers.auth import get_current_user
from tasks.audit_pipeline import run_audit

router = APIRouter(prefix="/audits", tags=["audits"])

AUDIT_COOLDOWN_DAYS = 7  # MVP: one audit per account per 7 days


@router.post("")
async def trigger_audit(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Trigger a new audit for a connected account."""
    account_id: str = body.get("account_id", "")
    if not account_id:
        raise HTTPException(status_code=400, detail="account_id required")

    # Verify this account belongs to the current user
    result = await db.execute(
        select(ConnectedAccount).where(
            ConnectedAccount.id == account_id,
            ConnectedAccount.user_id == current_user.id,
        )
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Enforce cooldown
    cooldown_start = datetime.now(timezone.utc) - timedelta(days=AUDIT_COOLDOWN_DAYS)
    result = await db.execute(
        select(Audit).where(
            Audit.connected_account_id == account_id,
            Audit.status == AuditStatus.COMPLETED,
            Audit.completed_at >= cooldown_start,
        )
    )
    recent_audit = result.scalar_one_or_none()
    if recent_audit:
        next_allowed = recent_audit.completed_at + timedelta(days=AUDIT_COOLDOWN_DAYS)
        raise HTTPException(
            status_code=429,
            detail=f"Audit cooldown active. Next audit allowed after {next_allowed.isoformat()}",
        )

    # Create audit record
    audit = Audit(
        user_id=current_user.id,
        connected_account_id=account_id,
        status=AuditStatus.PENDING,
    )
    db.add(audit)
    await db.flush()  # Get the ID before committing

    # Dispatch Celery task
    task = run_audit.delay(str(audit.id))
    audit.celery_task_id = task.id
    await db.commit()

    return {"audit_id": str(audit.id), "status": AuditStatus.PENDING}


@router.get("/latest")
async def get_latest_audit(
    account_id: str = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the most recent audit for an account."""
    result = await db.execute(
        select(Audit)
        .where(
            Audit.connected_account_id == account_id,
            Audit.user_id == current_user.id,
        )
        .order_by(Audit.created_at.desc())
        .limit(1)
    )
    audit = result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="No audits found for this account")
    return _serialize_audit(audit)


@router.get("/{audit_id}")
async def get_audit(
    audit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get audit status and summary stats."""
    result = await db.execute(
        select(Audit).where(
            Audit.id == audit_id,
            Audit.user_id == current_user.id,
        )
    )
    audit = result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")
    return _serialize_audit(audit)


@router.get("/{audit_id}/pairs")
async def get_audit_pairs(
    audit_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    sort: str = Query("waste", regex="^(waste|score)$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(25, ge=1, le=100),
):
    """
    Get ad-page pairs for an audit.
    Sorted by estimated_monthly_waste desc (default) or overall_score asc.
    """
    # Verify audit ownership
    result = await db.execute(
        select(Audit).where(Audit.id == audit_id, Audit.user_id == current_user.id)
    )
    audit = result.scalar_one_or_none()
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    order_col = (
        AdPagePair.estimated_monthly_waste.desc().nullslast()
        if sort == "waste"
        else AdPagePair.overall_score.asc().nullslast()
    )

    result = await db.execute(
        select(AdPagePair)
        .where(AdPagePair.audit_id == audit_id)
        .order_by(order_col)
        .offset(offset)
        .limit(limit)
    )
    pairs = result.scalars().all()

    # Get total count
    count_result = await db.execute(
        select(func.count()).where(AdPagePair.audit_id == audit_id)
    )
    total = count_result.scalar()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "pairs": [_serialize_pair(p) for p in pairs],
    }


def _serialize_audit(audit: Audit) -> dict:
    return {
        "id": str(audit.id),
        "status": audit.status,
        "total_ads": audit.total_ads,
        "avg_coherence_score": audit.avg_coherence_score,
        "total_wasted_spend_monthly": audit.total_wasted_spend_monthly,
        "ads_below_average_lp_experience": audit.ads_below_average_lp_experience,
        "error_message": audit.error_message,
        "created_at": audit.created_at.isoformat() if audit.created_at else None,
        "completed_at": audit.completed_at.isoformat() if audit.completed_at else None,
    }


def _serialize_pair(pair: AdPagePair) -> dict:
    return {
        "id": str(pair.id),
        "campaign_name": pair.campaign_name,
        "ad_group_name": pair.ad_group_name,
        "ad_headlines": pair.ad_headlines,
        "ad_descriptions": pair.ad_descriptions,
        "final_url": pair.final_url,
        "keywords": pair.keywords,
        "page_title": pair.page_title,
        "page_h1": pair.page_h1,
        "page_h2s": pair.page_h2s,
        "cta_texts": pair.cta_texts,
        "offer_mentions": pair.offer_mentions,
        "mobile_friendly": pair.mobile_friendly,
        "page_load_time_ms": pair.page_load_time_ms,
        "screenshot_path": pair.screenshot_path,
        "scrape_error": pair.scrape_error,
        "overall_score": pair.overall_score,
        "headline_match": {"score": pair.headline_match_score, "diagnosis": pair.headline_match_diagnosis},
        "offer_consistency": {"score": pair.offer_consistency_score, "diagnosis": pair.offer_consistency_diagnosis},
        "cta_alignment": {"score": pair.cta_alignment_score, "diagnosis": pair.cta_alignment_diagnosis},
        "keyword_relevance": {"score": pair.keyword_relevance_score, "diagnosis": pair.keyword_relevance_diagnosis},
        "tone_continuity": {"score": pair.tone_continuity_score, "diagnosis": pair.tone_continuity_diagnosis},
        "top_recommendations": pair.top_recommendations,
        "estimated_monthly_waste": pair.estimated_monthly_waste,
        "waste_type": pair.waste_type,
        "additional_conversions_monthly": pair.additional_conversions_monthly,
    }
