"""Migrate to Firestore - drop documents/cursors, update chunks

Revision ID: 4d5e6f7a8b9c
Revises: 3a4f5b6c7d8e
Create Date: 2026-02-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY


# revision identifiers, used by Alembic.
revision: str = '4d5e6f7a8b9c'
down_revision: Union[str, Sequence[str], None] = '3a4f5b6c7d8e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Migrate document metadata to Firestore.
    
    WARNING: This migration will:
    - Drop all existing documents and ingestion_cursors data
    - Require full re-sync of all connectors
    - Break existing document_id references in chunks
    """
    
    # 1. Drop foreign key constraint from document_chunks to documents
    op.drop_constraint('document_chunks_document_id_fkey', 'document_chunks', type_='foreignkey')
    
    # 2. Rename document_id to doc_id and change to TEXT
    op.alter_column('document_chunks', 'document_id',
                   new_column_name='doc_id',
                   type_=sa.Text(),
                   existing_type=UUID(as_uuid=True),
                   nullable=False)
    
    # 3. Add new columns to document_chunks
    op.add_column('document_chunks', sa.Column('tenant_id', sa.Text(), nullable=False, server_default='default-tenant'))
    op.add_column('document_chunks', sa.Column('classification_level', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('document_chunks', sa.Column('category_ids', ARRAY(sa.Text()), nullable=False, server_default='{}'))
    
    # Remove server defaults after backfilling
    op.alter_column('document_chunks', 'tenant_id', server_default=None)
    op.alter_column('document_chunks', 'classification_level', server_default=None)
    op.alter_column('document_chunks', 'category_ids', server_default=None)
    
    # 4. Create indexes on document_chunks
    op.create_index('idx_chunk_tenant_doc', 'document_chunks', ['tenant_id', 'doc_id'])
    op.create_index('idx_chunk_tenant_classification', 'document_chunks', ['tenant_id', 'classification_level'])
    op.create_index('idx_chunk_category_ids', 'document_chunks', ['category_ids'], postgresql_using='gin')
    
    # 5. Drop old tables
    op.drop_table('documents')
    op.drop_table('ingestion_cursors')


def downgrade() -> None:
    """
    Downgrade is not supported for this migration.
    Would require recreating documents table and migrating data back from Firestore.
    """
    raise NotImplementedError(
        "Downgrade from Firestore migration is not supported. "
        "Document metadata is now in Firestore and cannot be automatically restored to Postgres."
    )
