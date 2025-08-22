"""
PALD Boundary Enforcement Migration
Creates new tables for proper data separation and migrates existing mixed data.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = '001_pald_boundary'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """Create new tables for PALD boundary enforcement."""
    
    # Create survey_responses table
    op.create_table(
        'survey_responses',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('survey_data', JSONB, nullable=False),
        sa.Column('survey_version', sa.String(50), nullable=False, default='1.0'),
        sa.Column('completed_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    
    # Create onboarding_progress table
    op.create_table(
        'onboarding_progress',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('current_step', sa.String(100), nullable=False),
        sa.Column('completed_steps', JSONB, nullable=False, default=[]),
        sa.Column('step_data', JSONB, nullable=True),
        sa.Column('progress_percentage', sa.Float, nullable=False, default=0.0),
        sa.Column('started_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime, nullable=True),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    
    # Create user_preferences table
    op.create_table(
        'user_preferences',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('preferences', JSONB, nullable=False),
        sa.Column('category', sa.String(100), nullable=False, default='general'),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    
    # Create schema_versions table
    op.create_table(
        'schema_versions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('version', sa.String(50), unique=True, nullable=False),
        sa.Column('schema_content', JSONB, nullable=False),
        sa.Column('checksum', sa.String(64), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=False),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    
    # Create schema_field_candidates table
    op.create_table(
        'schema_field_candidates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('field_name', sa.String(255), nullable=False),
        sa.Column('field_path', sa.String(500), nullable=False),
        sa.Column('detection_context', sa.Text, nullable=True),
        sa.Column('occurrence_count', sa.Integer, nullable=False, default=1),
        sa.Column('example_values', JSONB, nullable=True),
        sa.Column('proposed_type', sa.String(100), nullable=True),
        sa.Column('confidence_score', sa.Float, nullable=True),
        sa.Column('review_status', sa.String(50), nullable=False, default='pending'),
        sa.Column('approved_at', sa.DateTime, nullable=True),
        sa.Column('rejected_at', sa.DateTime, nullable=True),
        sa.Column('rejection_reason', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
    )
    
    # Create indexes for performance
    op.create_index('idx_survey_user', 'survey_responses', ['user_id'])
    op.create_index('idx_survey_completed', 'survey_responses', ['completed_at'])
    op.create_index('idx_survey_version', 'survey_responses', ['survey_version'])
    
    op.create_index('idx_onboarding_user', 'onboarding_progress', ['user_id'])
    op.create_index('idx_onboarding_step', 'onboarding_progress', ['current_step'])
    op.create_index('idx_onboarding_progress', 'onboarding_progress', ['progress_percentage'])
    
    op.create_index('idx_preferences_user', 'user_preferences', ['user_id'])
    op.create_index('idx_preferences_category', 'user_preferences', ['category'])
    op.create_index('idx_preferences_user_category', 'user_preferences', ['user_id', 'category'])
    
    op.create_index('idx_schema_version', 'schema_versions', ['version'])
    op.create_index('idx_schema_active', 'schema_versions', ['is_active'])
    op.create_index('idx_schema_checksum', 'schema_versions', ['checksum'])
    
    op.create_index('idx_candidate_field', 'schema_field_candidates', ['field_name'])
    op.create_index('idx_candidate_path', 'schema_field_candidates', ['field_path'])
    op.create_index('idx_candidate_status', 'schema_field_candidates', ['review_status'])
    op.create_index('idx_candidate_count', 'schema_field_candidates', ['occurrence_count'])
    op.create_index('idx_candidate_confidence', 'schema_field_candidates', ['confidence_score'])


def downgrade():
    """Drop tables created for PALD boundary enforcement."""
    
    # Drop indexes first
    op.drop_index('idx_candidate_confidence')
    op.drop_index('idx_candidate_count')
    op.drop_index('idx_candidate_status')
    op.drop_index('idx_candidate_path')
    op.drop_index('idx_candidate_field')
    
    op.drop_index('idx_schema_checksum')
    op.drop_index('idx_schema_active')
    op.drop_index('idx_schema_version')
    
    op.drop_index('idx_preferences_user_category')
    op.drop_index('idx_preferences_category')
    op.drop_index('idx_preferences_user')
    
    op.drop_index('idx_onboarding_progress')
    op.drop_index('idx_onboarding_step')
    op.drop_index('idx_onboarding_user')
    
    op.drop_index('idx_survey_version')
    op.drop_index('idx_survey_completed')
    op.drop_index('idx_survey_user')
    
    # Drop tables
    op.drop_table('schema_field_candidates')
    op.drop_table('schema_versions')
    op.drop_table('user_preferences')
    op.drop_table('onboarding_progress')
    op.drop_table('survey_responses')