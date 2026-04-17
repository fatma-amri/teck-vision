"""Add rooms and room_instances tables

Revision ID: aab1813x0001
Revises: 48d8250d19bd
Create Date: 2026-04-17 00:00:00.000000

"""
import sqlalchemy as sa
from alembic import op

revision = "aab1813x0001"
down_revision = "48d8250d19bd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rooms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("difficulty", sa.String(32), nullable=True),
        sa.Column("duration", sa.Integer(), nullable=True),
        sa.Column("target_ip", sa.String(45), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )

    # Create room_instances only if it doesn't exist
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "room_instances" not in inspector.get_table_names():
        op.create_table(
            "room_instances",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("team_id", sa.Integer(), nullable=True),
            sa.Column("category", sa.String(80), nullable=False),
            sa.Column("machine_ip", sa.String(15), nullable=True),
            sa.Column("is_active", sa.Boolean(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("duration_minutes", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["team_id"], ["teams.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "room_instances" in inspector.get_table_names():
        op.drop_table("room_instances")
    op.drop_table("rooms")
