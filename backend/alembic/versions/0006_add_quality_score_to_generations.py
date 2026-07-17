"""add quality_score to generations

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-14
"""
from alembic import op
import sqlalchemy as sa

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("generations", sa.Column("quality_score", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("generations", "quality_score")
