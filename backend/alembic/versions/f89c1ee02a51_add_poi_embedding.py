"""add poi_embedding

Revision ID: f89c1ee02a51
Revises: c89fe6fa9315
Create Date: 2026-11-02 10:37:35.925190

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'f89c1ee02a51'
down_revision: Union[str, Sequence[str], None] = 'c89fe6fa9315'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "poi_embedding",
        sa.Column("poi_id", sa.BigInteger(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(), nullable=False),
        sa.Column("document", sa.Text(), nullable=False),
        sa.Column("embedding", Vector(768), nullable=False),
        sa.Column("embedded_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("poi_id"),
        sa.ForeignKeyConstraint(["poi_id"], ["poi.id"], ondelete="CASCADE"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("poi_embedding")
