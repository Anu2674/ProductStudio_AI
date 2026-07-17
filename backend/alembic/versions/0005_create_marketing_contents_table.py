"""create marketing_contents table

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "marketing_contents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("source_image_id", sa.Integer(), sa.ForeignKey("images.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("bullet_points", sa.JSON(), nullable=False),
        sa.Column("social_caption", sa.String(), nullable=False),
        sa.Column("seo_keywords", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("marketing_contents")
