"""Add AWS challenge id to rooms

Revision ID: d4c7a2b5f001
Revises: 3ebc6bf0001
Create Date: 2026-05-06
"""

from alembic import op
import sqlalchemy as sa


revision = "d4c7a2b5f001"
down_revision = "3ebc6bf0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("rooms", sa.Column("aws_challenge_id", sa.String(length=64), nullable=True))


def downgrade():
    op.drop_column("rooms", "aws_challenge_id")
