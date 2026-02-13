"""Add s3_url and file_size_bytes to documents

Revision ID: 3a4f5b6c7d8e
Revises: bb3d0be1990b
Create Date: 2026-02-02 12:52:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a4f5b6c7d8e'
down_revision: Union[str, Sequence[str], None] = 'bb3d0be1990b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add s3_url column
    op.add_column('documents', sa.Column('s3_url', sa.String(), nullable=True))
    
    # Add file_size_bytes column
    op.add_column('documents', sa.Column('file_size_bytes', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove file_size_bytes column
    op.drop_column('documents', 'file_size_bytes')
    
    # Remove s3_url column
    op.drop_column('documents', 's3_url')
