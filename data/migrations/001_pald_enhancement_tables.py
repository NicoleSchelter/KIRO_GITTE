"""Add PALD enhancement tables

Revision ID: 001_pald_enhancement
Revises: base
Create Date: 2025-01-16 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_pald_enhancement'
down_revision = 'base'
branch_labels = None
depends_on = None


def upgrade():
    # Create schema_field_candidates table
    op.create_table('schema_field_candidates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('field_name', sa.String(length=255), nullable=False),
        sa.Column('field_category', sa.String(length=100), nullable=True),
        sa.Column('mention_count', sa.Integer(), nullable=False, default=1),
        sa.Column('first_detected', sa.DateTime(), nullable=False),
        sa.Column('last_mentioned', sa.DateTime(), nullable=False),
        sa.Column('threshold_reached', sa.Boolean(), nullable=False, default=False),
        sa.Column('added_to_schema', sa.Boolean(), nullable=False, default=False),
        sa.Column('schema_version_added', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_schema_field_name', 'schema_field_candidates', ['field_name'])
    op.create_index('idx_schema_field_threshold', 'schema_field_candidates', ['threshold_reached'])
    op.create_index('idx_schema_field_added', 'schema_field_candidates', ['added_to_schema'])
    op.create_index('idx_schema_field_category', 'schema_field_candidates', ['field_category'])

    # Create pald_processing_logs table
    op.create_table('pald_processing_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('processing_stage', sa.String(length=100), nullable=False),
        sa.Column('operation', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_pald_log_session', 'pald_processing_logs', ['session_id'])
    op.create_index('idx_pald_log_stage', 'pald_processing_logs', ['processing_stage'])
    op.create_index('idx_pald_log_status', 'pald_processing_logs', ['status'])
    op.create_index('idx_pald_log_created', 'pald_processing_logs', ['created_at'])

    # Create bias_analysis_jobs table
    op.create_table('bias_analysis_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('pald_data', sa.JSON(), nullable=False),
        sa.Column('analysis_types', sa.JSON(), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, default=5),
        sa.Column('status', sa.String(length=50), nullable=False, default='pending'),
        sa.Column('retry_count', sa.Integer(), nullable=False, default=0),
        sa.Column('max_retries', sa.Integer(), nullable=False, default=3),
        sa.Column('scheduled_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_bias_job_session', 'bias_analysis_jobs', ['session_id'])
    op.create_index('idx_bias_job_status', 'bias_analysis_jobs', ['status'])
    op.create_index('idx_bias_job_scheduled', 'bias_analysis_jobs', ['scheduled_at'])
    op.create_index('idx_bias_job_priority', 'bias_analysis_jobs', ['priority'])

    # Create bias_analysis_results table
    op.create_table('bias_analysis_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_id', sa.String(length=255), nullable=False),
        sa.Column('analysis_type', sa.String(length=100), nullable=False),
        sa.Column('bias_detected', sa.Boolean(), nullable=False),
