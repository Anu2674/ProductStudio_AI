"""create generations table

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "generations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("project_id", sa.Integer(), sa.ForeignKey("projects.id"), nullable=False),
        sa.Column("source_image_id", sa.Integer(), sa.ForeignKey("images.id"), nullable=False),
        sa.Column("generation_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("prompt", sa.String(), nullable=True),
        sa.Column("negative_prompt", sa.String(), nullable=True),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.Column("result_storage_path", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade():
    op.drop_table("generations")
