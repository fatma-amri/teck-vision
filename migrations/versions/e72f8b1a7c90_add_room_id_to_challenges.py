"""Add room id to challenges

Revision ID: e72f8b1a7c90
Revises: d4c7a2b5f001
Create Date: 2026-05-07
"""

import sqlalchemy as sa
from alembic import op


revision = "e72f8b1a7c90"
down_revision = "d4c7a2b5f001"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    challenge_cols = [c["name"] for c in inspector.get_columns("challenges")]

    if "room_id" not in challenge_cols:
        op.add_column("challenges", sa.Column("room_id", sa.Integer(), nullable=True))


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    challenge_cols = [c["name"] for c in inspector.get_columns("challenges")]

    if "room_id" in challenge_cols:
        op.drop_column("challenges", "room_id")
