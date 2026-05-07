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
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    rooms_cols = [c["name"] for c in inspector.get_columns("rooms")]
    if "aws_challenge_id" not in rooms_cols:
        op.add_column(
            "rooms", sa.Column("aws_challenge_id", sa.String(length=64), nullable=True)
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    rooms_cols = [c["name"] for c in inspector.get_columns("rooms")]
    if "aws_challenge_id" in rooms_cols:
        op.drop_column("rooms", "aws_challenge_id")
