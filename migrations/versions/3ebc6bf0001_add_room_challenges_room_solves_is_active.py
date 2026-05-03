"""Add room_challenges, room_solves tables and is_active to rooms

Revision ID: 3ebc6bf0001
Revises: aab1813x0001
Branch Labels: None
Depends On: None

"""
import sqlalchemy as sa
from alembic import op

revision = "3ebc6bf0001"
down_revision = "aab1813x0001"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # Add is_active to rooms if missing
    rooms_cols = [c["name"] for c in inspector.get_columns("rooms")]
    if "is_active" not in rooms_cols:
        op.add_column("rooms", sa.Column("is_active", sa.Boolean(), nullable=True, server_default="1"))

    # Create room_challenges
    if "room_challenges" not in inspector.get_table_names():
        op.create_table(
            "room_challenges",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("room_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("question", sa.Text(), nullable=True),
            sa.Column("answer", sa.Text(), nullable=False),
            sa.Column("points", sa.Integer(), nullable=True),
            sa.Column("difficulty", sa.String(32), nullable=True),
            sa.Column("position", sa.Integer(), nullable=True),
            sa.ForeignKeyConstraint(["room_id"], ["rooms.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )

    # Create room_solves
    if "room_solves" not in inspector.get_table_names():
        op.create_table(
            "room_solves",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("challenge_id", sa.Integer(), nullable=False),
            sa.Column("solved_at", sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["challenge_id"], ["room_challenges.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("user_id", "challenge_id"),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "room_solves" in inspector.get_table_names():
        op.drop_table("room_solves")
    if "room_challenges" in inspector.get_table_names():
        op.drop_table("room_challenges")
