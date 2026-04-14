"""initial schema

Revision ID: 20260413210127
Revises:
Create Date: 2026-04-13 21:01:27.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260413210127"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("google_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("google_id"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "connected_accounts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("google_ads_customer_id", sa.String(50), nullable=False),
        sa.Column("account_name", sa.String(255), nullable=True),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "audits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("connected_account_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "completed", "failed", name="auditstatus"),
            nullable=False,
        ),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("total_ads", sa.Integer(), nullable=True),
        sa.Column("avg_coherence_score", sa.Float(), nullable=True),
        sa.Column("total_wasted_spend_monthly", sa.Float(), nullable=True),
        sa.Column("ads_below_average_lp_experience", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["connected_account_id"], ["connected_accounts.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "ad_page_pairs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("audit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("campaign_name", sa.String(255), nullable=True),
        sa.Column("ad_group_name", sa.String(255), nullable=True),
        sa.Column("ad_headlines", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("ad_descriptions", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("final_url", sa.Text(), nullable=True),
        sa.Column("keywords", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("page_title", sa.Text(), nullable=True),
        sa.Column("page_h1", sa.Text(), nullable=True),
        sa.Column("page_h2s", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("meta_description", sa.Text(), nullable=True),
        sa.Column("above_fold_text", sa.Text(), nullable=True),
        sa.Column("cta_texts", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("offer_mentions", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("page_load_time_ms", sa.Integer(), nullable=True),
        sa.Column("mobile_friendly", sa.Boolean(), nullable=True),
        sa.Column("screenshot_path", sa.Text(), nullable=True),
        sa.Column("scrape_error", sa.Text(), nullable=True),
        sa.Column("overall_score", sa.Integer(), nullable=True),
        sa.Column("headline_match_score", sa.Integer(), nullable=True),
        sa.Column("headline_match_diagnosis", sa.Text(), nullable=True),
        sa.Column("offer_consistency_score", sa.Integer(), nullable=True),
        sa.Column("offer_consistency_diagnosis", sa.Text(), nullable=True),
        sa.Column("cta_alignment_score", sa.Integer(), nullable=True),
        sa.Column("cta_alignment_diagnosis", sa.Text(), nullable=True),
        sa.Column("keyword_relevance_score", sa.Integer(), nullable=True),
        sa.Column("keyword_relevance_diagnosis", sa.Text(), nullable=True),
        sa.Column("tone_continuity_score", sa.Integer(), nullable=True),
        sa.Column("tone_continuity_diagnosis", sa.Text(), nullable=True),
        sa.Column("top_recommendations", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("estimated_monthly_waste", sa.Float(), nullable=True),
        sa.Column("waste_type", sa.String(50), nullable=True),
        sa.Column("additional_conversions_monthly", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["audit_id"], ["audits.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("ad_page_pairs")
    op.drop_table("audits")
    op.execute("DROP TYPE IF EXISTS auditstatus")
    op.drop_table("connected_accounts")
    op.drop_table("users")
