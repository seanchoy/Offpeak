"""add photo attribution to poi_photo_cache


Revision ID: c89fe6fa9315
Revises: 21a43930d4c2
Create Date: 2026-10-25 16:55:06.608906

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c89fe6fa9315'
down_revision: Union[str, Sequence[str], None] = '21a43930d4c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("poi_photo_cache", sa.Column("author_name", sa.Text(), nullable=True))
    op.add_column("poi_photo_cache", sa.Column("author_uri", sa.Text(), nullable=True))
    op.add_column("poi_photo_cache", sa.Column("google_maps_uri", sa.Text(), nullable=True))
    pass


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("poi_photo_cache", "google_maps_uri")
    op.drop_column("poi_photo_cache", "author_uri")
    op.drop_column("poi_photo_cache", "author_name")
    pass
