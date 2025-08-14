"""Add UX enhancements database schema

Revision ID: ux_enhancements_001
Revises: 81502a5683af
Create Date: 2025-08-14 12:00:00.000000

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'ux_enhancements_001'
down_revision = '81502a5683af'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add UX enhancements tables."""
    
    # Create image_processing_results table
    op.create_table('image_processing_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('original_image_path', sa.String(length=500), nullable=False),
        sa.Column('processed_image_path', sa.String(length=500), nullable=True),
        sa.Column('processing_method', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('confidence_score', sa.Integer(), nullable=True),
        sa.Column('processing_time_ms', sa.Integer(), nullable=True),
        sa.Column('quality_issues', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('person_count', sa.Integer(), nullable=True),
        sa.Column('quality_score', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    
    # Create indexes for image_processing_results
    op.create_index('idx_image_processing_user', 'image_processing_results', ['user_id'])
    op.create_index('idx_image_processing_status', 'image_processing_results', ['status'])
    op.create_index('idx_image_processing_created', 'image_processing_results', ['created_at'])
    op.create_index('idx_image_processing_method', 'image_processing_results', ['processing_method'])
    
    # Create image_corrections table
    op.create_table('image_corrections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('processing_result_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('correction_action', sa.String(length=50), nullable=False),
        sa.Column('crop_coordinates', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('rejection_reason', sa.String(length=200), nullable=True),
        sa.Column('suggested_modifications', sa.Text(), nullable=True),
        sa.Column('final_image_path', sa.String(length=500), nullable=True),
        sa.Column('correction_time_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['processing_result_id'], ['image_processing_results.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    
    # Create indexes for image_corrections
    op.create_index('idx_image_correction_result', 'image_corrections', ['processing_result_id'])
    op.create_index('idx_image_correction_user', 'image_corrections', ['user_id'])
    op.create_index('idx_image_correction_action', 'image_corrections', ['correction_action'])
    op.create_index('idx_image_correction_created', 'image_corrections', ['created_at'])
    
    # Create prerequisite_check_results table
    op.create_table('prerequisite_check_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('operation_name', sa.String(length=100), nullable=False),
        sa.Column('checker_name', sa.String(length=100), nullable=False),
        sa.Column('check_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('resolution_steps', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('check_time_ms', sa.Integer(), nullable=True),
        sa.Column('confidence_score', sa.Integer(), nullable=True),
        sa.Column('cached', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    
    # Create indexes for prerequisite_check_results
    op.create_index('idx_prerequisite_user', 'prerequisite_check_results', ['user_id'])
    op.create_index('idx_prerequisite_operation', 'prerequisite_check_results', ['operation_name'])
    op.create_index('idx_prerequisite_checker', 'prerequisite_check_results', ['checker_name'])
    op.create_index('idx_prerequisite_status', 'prerequisite_check_results', ['status'])
    op.create_index('idx_prerequisite_type', 'prerequisite_check_results', ['check_type'])
    op.create_index('idx_prerequisite_created', 'prerequisite_check_results', ['created_at'])
    op.create_index('idx_prerequisite_operation_user', 'prerequisite_check_results', ['operation_name', 'user_id'])
    
    # Create tooltip_interactions table
    op.create_table('tooltip_interactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('element_id', sa.String(length=200), nullable=False),
        sa.Column('tooltip_content_id', sa.String(length=200), nullable=True),
        sa.Column('interaction_type', sa.String(length=50), nullable=False),
        sa.Column('page_context', sa.String(length=200), nullable=True),
        sa.Column('tooltip_title', sa.String(length=500), nullable=True),
        sa.Column('tooltip_description', sa.Text(), nullable=True),
        sa.Column('display_time_ms', sa.Integer(), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    
    # Create indexes for tooltip_interactions
    op.create_index('idx_tooltip_user', 'tooltip_interactions', ['user_id'])
    op.create_index('idx_tooltip_element', 'tooltip_interactions', ['element_id'])
    op.create_index('idx_tooltip_interaction', 'tooltip_interactions', ['interaction_type'])
    op.create_index('idx_tooltip_session', 'tooltip_interactions', ['session_id'])
    op.create_index('idx_tooltip_created', 'tooltip_interactions', ['created_at'])
    op.create_index('idx_tooltip_context', 'tooltip_interactions', ['page_context'])
    
    # Create ux_audit_logs table
    op.create_table('ux_audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_context', sa.String(length=200), nullable=True),
        sa.Column('event_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('workflow_step', sa.String(length=100), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE')
    )
    
    # Create indexes for ux_audit_logs
    op.create_index('idx_ux_audit_user', 'ux_audit_logs', ['user_id'])
    op.create_index('idx_ux_audit_event', 'ux_audit_logs', ['event_type'])
    op.create_index('idx_ux_audit_session', 'ux_audit_logs', ['session_id'])
    op.create_index('idx_ux_audit_context', 'ux_audit_logs', ['event_context'])
    op.create_index('idx_ux_audit_created', 'ux_audit_logs', ['created_at'])
    op.create_index('idx_ux_audit_success', 'ux_audit_logs', ['success'])
    op.create_index('idx_ux_audit_workflow', 'ux_audit_logs', ['workflow_step'])


def downgrade() -> None:
    """Remove UX enhancements tables."""
    
    # Drop tables in reverse order to handle foreign key constraints
    op.drop_table('ux_audit_logs')
    op.drop_table('tooltip_interactions')
    op.drop_table('prerequisite_check_results')
    op.drop_table('image_corrections')
    op.drop_table('image_processing_results')