from sqlalchemy import (
    Column, String, DateTime, Integer, Float, Boolean,
    Text, ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum

from .base import Base


class AuditStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Audit(Base):
    __tablename__ = "audits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    connected_account_id = Column(UUID(as_uuid=True), ForeignKey("connected_accounts.id"), nullable=False)
    status = Column(SAEnum(AuditStatus), default=AuditStatus.PENDING, nullable=False)
    celery_task_id = Column(String(255))

    # Summary stats (populated when completed)
    total_ads = Column(Integer, default=0)
    avg_coherence_score = Column(Float)
    total_wasted_spend_monthly = Column(Float)
    ads_below_average_lp_experience = Column(Integer, default=0)

    error_message = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    user = relationship("User", back_populates="audits")
    connected_account = relationship("ConnectedAccount", back_populates="audits")
    ad_page_pairs = relationship("AdPagePair", back_populates="audit", cascade="all, delete-orphan")


class AdPagePair(Base):
    """One ad (RSA) paired with its landing page — the core unit of the audit."""
    __tablename__ = "ad_page_pairs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    audit_id = Column(UUID(as_uuid=True), ForeignKey("audits.id"), nullable=False)

    # Ad data
    campaign_name = Column(String(255))
    ad_group_name = Column(String(255))
    ad_headlines = Column(JSON)       # list[str]
    ad_descriptions = Column(JSON)    # list[str]
    final_url = Column(Text)
    keywords = Column(JSON)           # list[KeywordData dict]

    # Scraped page data
    page_title = Column(Text)
    page_h1 = Column(Text)
    page_h2s = Column(JSON)
    meta_description = Column(Text)
    above_fold_text = Column(Text)
    cta_texts = Column(JSON)
    offer_mentions = Column(JSON)
    page_load_time_ms = Column(Integer)
    mobile_friendly = Column(Boolean)
    screenshot_path = Column(Text)
    scrape_error = Column(Text)

    # Scoring (populated by LLM)
    overall_score = Column(Integer)
    headline_match_score = Column(Integer)
    headline_match_diagnosis = Column(Text)
    offer_consistency_score = Column(Integer)
    offer_consistency_diagnosis = Column(Text)
    cta_alignment_score = Column(Integer)
    cta_alignment_diagnosis = Column(Text)
    keyword_relevance_score = Column(Integer)
    keyword_relevance_diagnosis = Column(Text)
    tone_continuity_score = Column(Integer)
    tone_continuity_diagnosis = Column(Text)
    top_recommendations = Column(JSON)  # list[str]

    # Wasted spend
    estimated_monthly_waste = Column(Float)
    waste_type = Column(String(50))  # "cpc_savings" | "conversion_lift"
    additional_conversions_monthly = Column(Float)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    audit = relationship("Audit", back_populates="ad_page_pairs")
