"""add user identities and nullable password

Revision ID: 21a43930d4c2
Revises: c7d41ea9b2f0
Create Date: 2026-10-24 13:11:25.587230

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '21a43930d4c2'
down_revision: Union[str, Sequence[str], None] = 'c7d41ea9b2f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "password_hash",
                    existing_type=sa.String(255), nullable=True)
    op.create_table(
        "user_identities",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("user_id", sa.UUID(),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_user_id", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("provider", "provider_user_id"),
    )
    op.create_index("ix_user_identities_user_id", "user_identities", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_identities_user_id", table_name="user_identities")
    op.drop_table("user_identities")
    op.alter_column("users", "password_hash",
                    existing_type=sa.String(255), nullable=False)
