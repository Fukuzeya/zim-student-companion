"""Add document tracking for RAG system

Revision ID: 001_add_document_tracking
Revises:
Create Date: 2026-01-24

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSON


# revision identifiers, used by Alembic.
revision = '001_add_document_tracking'
down_revision = None  # Update this to your latest migration ID
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create uploaded_documents table
    op.create_table(
        'uploaded_documents',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('original_filename', sa.String(500), nullable=False),
        sa.Column('file_path', sa.String(1000), nullable=False),
        sa.Column('file_size', sa.Integer, nullable=False),
        sa.Column('file_hash', sa.String(64), nullable=False, index=True),
        sa.Column('mime_type', sa.String(100)),

        # Document metadata
        sa.Column('document_type', sa.String(50), nullable=False, index=True),
        sa.Column('subject', sa.String(100), index=True),
        sa.Column('grade', sa.String(20)),
        sa.Column('education_level', sa.String(20), default='secondary'),
        sa.Column('year', sa.Integer),
        sa.Column('paper_number', sa.String(20)),
        sa.Column('term', sa.String(20)),

        # Processing status
        sa.Column('status', sa.String(20), nullable=False, default='pending', index=True),
        sa.Column('chunks_created', sa.Integer, default=0),
        sa.Column('chunks_indexed', sa.Integer, default=0),
        sa.Column('processing_progress', sa.Float, default=0.0),

        # Error tracking
        sa.Column('error_message', sa.Text),
        sa.Column('retry_count', sa.Integer, default=0),

        # Processing metadata
        sa.Column('processing_metadata', JSON, default={}),
        sa.Column('vector_store_collection', sa.String(100)),

        # Timestamps
        sa.Column('uploaded_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column('processing_started_at', sa.DateTime(timezone=True)),
        sa.Column('processed_at', sa.DateTime(timezone=True)),
        sa.Column('processing_time_ms', sa.Integer),

        # Uploader tracking
        sa.Column('uploaded_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),

        # Soft delete
        sa.Column('is_deleted', sa.Boolean, default=False, index=True),
        sa.Column('deleted_at', sa.DateTime(timezone=True)),
    )

    # Create document_processing_logs table
    op.create_table(
        'document_processing_logs',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('document_id', UUID(as_uuid=True), sa.ForeignKey('uploaded_documents.id', ondelete='CASCADE'), nullable=False, index=True),

        # Log details
        sa.Column('stage', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('message', sa.Text),
        sa.Column('details', JSON, default={}),

        # Timing
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column('duration_ms', sa.Integer),
    )

    # Create indexes for better query performance
    op.create_index('idx_documents_status_type', 'uploaded_documents', ['status', 'document_type'])
    op.create_index('idx_documents_subject_status', 'uploaded_documents', ['subject', 'status'])
    op.create_index('idx_logs_document_stage', 'document_processing_logs', ['document_id', 'stage'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_logs_document_stage')
    op.drop_index('idx_documents_subject_status')
    op.drop_index('idx_documents_status_type')

    # Drop tables
    op.drop_table('document_processing_logs')
    op.drop_table('uploaded_documents')
