"""Add PALD boundary enforcement tables

Revision ID: acaec84fad99
Revises: c746af805e67
Create Date: 2025-08-22 11:51:02.324946

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'acaec84fad99'
down_revision = 'c746af805e67'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create survey_responses table
    op.create_table('survey_responses',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('survey_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('survey_version', sa.String(length=50), nullable=False),
    sa.Column('completed_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_survey_completed', 'survey_responses', ['completed_at'], unique=False)
    op.create_index('idx_survey_user', 'survey_responses', ['user_id'], unique=False)
    op.create_index('idx_survey_version', 'survey_responses', ['survey_version'], unique=False)
    
    # Create onboarding_progress table
    op.create_table('onboarding_progress',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('current_step', sa.String(length=100), nullable=False),
    sa.Column('completed_steps', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('step_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('progress_percentage', sa.Float(), nullable=False),
    sa.Column('started_at', sa.DateTime(), nullable=False),
    sa.Column('completed_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_onboarding_progress', 'onboarding_progress', ['progress_percentage'], unique=False)
    op.create_index('idx_onboarding_step', 'onboarding_progress', ['current_step'], unique=False)
    op.create_index('idx_onboarding_user', 'onboarding_progress', ['user_id'], unique=False)
    
    # Create user_preferences table
    op.create_table('user_preferences',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('category', sa.String(length=100), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_preferences_category', 'user_preferences', ['category'], unique=False)
    op.create_index('idx_preferences_user', 'user_preferences', ['user_id'], unique=False)
    op.create_index('idx_preferences_user_category', 'user_preferences', ['user_id', 'category'], unique=False)
    
    # Create schema_versions table
    op.create_table('schema_versions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('version', sa.String(length=50), nullable=False),
    sa.Column('schema_content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('checksum', sa.String(length=64), nullable=False),
    sa.Column('file_path', sa.String(length=500), nullable=True),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('version')
    )
    op.create_index('idx_schema_active', 'schema_versions', ['is_active'], unique=False)
    op.create_index('idx_schema_checksum', 'schema_versions', ['checksum'], unique=False)
    op.create_index('idx_schema_version', 'schema_versions', ['version'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_schema_version', table_name='schema_versions')
    op.drop_index('idx_schema_checksum', table_name='schema_versions')
    op.drop_index('idx_schema_active', table_name='schema_versions')
    op.drop_table('schema_versions')
    
    op.drop_index('idx_preferences_user_category', table_name='user_preferences')
    op.drop_index('idx_preferences_user', table_name='user_preferences')
    op.drop_index('idx_preferences_category', table_name='user_preferences')
    op.drop_table('user_preferences')
    
    op.drop_index('idx_onboarding_user', table_name='onboarding_progress')
    op.drop_index('idx_onboarding_step', table_name='onboarding_progress')
    op.drop_index('idx_onboarding_progress', table_name='onboarding_progress')
    op.drop_table('onboarding_progress')
    
    op.drop_index('idx_survey_version', table_name='survey_responses')
    op.drop_index('idx_survey_user', table_name='survey_responses')
    op.drop_index('idx_survey_completed', table_name='survey_responses')
    op.drop_table('survey_responses')