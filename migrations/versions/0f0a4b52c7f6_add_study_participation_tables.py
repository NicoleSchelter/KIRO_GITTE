"""add_study_participation_tables

Revision ID: 0f0a4b52c7f6
Revises: acaec84fad99
Create Date: 2025-08-23 00:47:05.104803

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '0f0a4b52c7f6'
down_revision = 'acaec84fad99'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create pseudonyms table
    op.create_table('pseudonyms',
        sa.Column('pseudonym_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('pseudonym_text', sa.String(length=255), nullable=False),
        sa.Column('pseudonym_hash', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('pseudonym_id'),
        sa.UniqueConstraint('pseudonym_text')
    )
    op.create_index('idx_pseudonym_user', 'pseudonyms', ['user_id'], unique=False)
    op.create_index('idx_pseudonym_text', 'pseudonyms', ['pseudonym_text'], unique=False)
    op.create_index('idx_pseudonym_active', 'pseudonyms', ['is_active'], unique=False)

    # Create study_consent_records table
    op.create_table('study_consent_records',
        sa.Column('consent_id', sa.UUID(), nullable=False),
        sa.Column('pseudonym_id', sa.UUID(), nullable=False),
        sa.Column('consent_type', sa.String(length=100), nullable=False),
        sa.Column('granted', sa.Boolean(), nullable=False),
        sa.Column('version', sa.String(length=20), nullable=False),
        sa.Column('granted_at', sa.DateTime(), nullable=False),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['pseudonym_id'], ['pseudonyms.pseudonym_id'], ),
        sa.PrimaryKeyConstraint('consent_id')
    )
    op.create_index('idx_study_consent_pseudonym_type', 'study_consent_records', ['pseudonym_id', 'consent_type'], unique=False)
    op.create_index('idx_study_consent_granted_at', 'study_consent_records', ['granted_at'], unique=False)

    # Create study_survey_responses table
    op.create_table('study_survey_responses',
        sa.Column('response_id', sa.UUID(), nullable=False),
        sa.Column('pseudonym_id', sa.UUID(), nullable=False),
        sa.Column('survey_version', sa.String(length=20), nullable=False),
        sa.Column('responses', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['pseudonym_id'], ['pseudonyms.pseudonym_id'], ),
        sa.PrimaryKeyConstraint('response_id')
    )
    op.create_index('idx_study_survey_pseudonym', 'study_survey_responses', ['pseudonym_id'], unique=False)
    op.create_index('idx_study_survey_version', 'study_survey_responses', ['survey_version'], unique=False)
    op.create_index('idx_study_survey_completed', 'study_survey_responses', ['completed_at'], unique=False)

    # Create study_pald_data table
    op.create_table('study_pald_data',
        sa.Column('pald_id', sa.UUID(), nullable=False),
        sa.Column('pseudonym_id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('pald_content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('pald_type', sa.String(length=20), nullable=False),
        sa.Column('consistency_score', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['pseudonym_id'], ['pseudonyms.pseudonym_id'], ),
        sa.PrimaryKeyConstraint('pald_id')
    )
    op.create_index('idx_study_pald_pseudonym', 'study_pald_data', ['pseudonym_id'], unique=False)
    op.create_index('idx_study_pald_session', 'study_pald_data', ['session_id'], unique=False)
    op.create_index('idx_study_pald_type', 'study_pald_data', ['pald_type'], unique=False)
    op.create_index('idx_study_pald_created', 'study_pald_data', ['created_at'], unique=False)

    # Create generated_images table
    op.create_table('generated_images',
        sa.Column('image_id', sa.UUID(), nullable=False),
        sa.Column('pseudonym_id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('image_path', sa.String(length=500), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=False),
        sa.Column('pald_source_id', sa.UUID(), nullable=True),
        sa.Column('generation_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['pseudonym_id'], ['pseudonyms.pseudonym_id'], ),
        sa.ForeignKeyConstraint(['pald_source_id'], ['study_pald_data.pald_id'], ),
        sa.PrimaryKeyConstraint('image_id')
    )
    op.create_index('idx_generated_image_pseudonym', 'generated_images', ['pseudonym_id'], unique=False)
    op.create_index('idx_generated_image_session', 'generated_images', ['session_id'], unique=False)
    op.create_index('idx_generated_image_created', 'generated_images', ['created_at'], unique=False)
    op.create_index('idx_generated_image_pald_source', 'generated_images', ['pald_source_id'], unique=False)

    # Create chat_messages table
    op.create_table('chat_messages',
        sa.Column('message_id', sa.UUID(), nullable=False),
        sa.Column('pseudonym_id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('message_type', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('pald_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['pseudonym_id'], ['pseudonyms.pseudonym_id'], ),
        sa.PrimaryKeyConstraint('message_id')
    )
    op.create_index('idx_chat_pseudonym', 'chat_messages', ['pseudonym_id'], unique=False)
    op.create_index('idx_chat_session', 'chat_messages', ['session_id'], unique=False)
    op.create_index('idx_chat_timestamp', 'chat_messages', ['timestamp'], unique=False)
    op.create_index('idx_chat_type', 'chat_messages', ['message_type'], unique=False)

    # Create feedback_records table
    op.create_table('feedback_records',
        sa.Column('feedback_id', sa.UUID(), nullable=False),
        sa.Column('pseudonym_id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('image_id', sa.UUID(), nullable=True),
        sa.Column('feedback_text', sa.Text(), nullable=False),
        sa.Column('feedback_pald', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('round_number', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['pseudonym_id'], ['pseudonyms.pseudonym_id'], ),
        sa.ForeignKeyConstraint(['image_id'], ['generated_images.image_id'], ),
        sa.PrimaryKeyConstraint('feedback_id')
    )
    op.create_index('idx_feedback_pseudonym', 'feedback_records', ['pseudonym_id'], unique=False)
    op.create_index('idx_feedback_session', 'feedback_records', ['session_id'], unique=False)
    op.create_index('idx_feedback_image', 'feedback_records', ['image_id'], unique=False)
    op.create_index('idx_feedback_round', 'feedback_records', ['round_number'], unique=False)
    op.create_index('idx_feedback_created', 'feedback_records', ['created_at'], unique=False)

    # Create interaction_logs table
    op.create_table('interaction_logs',
        sa.Column('log_id', sa.UUID(), nullable=False),
        sa.Column('pseudonym_id', sa.UUID(), nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('interaction_type', sa.String(length=50), nullable=False),
        sa.Column('prompt', sa.Text(), nullable=True),
        sa.Column('response', sa.Text(), nullable=True),
        sa.Column('model_used', sa.String(length=100), nullable=False),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('token_usage', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['pseudonym_id'], ['pseudonyms.pseudonym_id'], ),
        sa.PrimaryKeyConstraint('log_id')
    )
    op.create_index('idx_interaction_pseudonym', 'interaction_logs', ['pseudonym_id'], unique=False)
    op.create_index('idx_interaction_session', 'interaction_logs', ['session_id'], unique=False)
    op.create_index('idx_interaction_type', 'interaction_logs', ['interaction_type'], unique=False)
    op.create_index('idx_interaction_model', 'interaction_logs', ['model_used'], unique=False)
    op.create_index('idx_interaction_timestamp', 'interaction_logs', ['timestamp'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order to handle foreign key constraints
    op.drop_index('idx_interaction_timestamp', table_name='interaction_logs')
    op.drop_index('idx_interaction_model', table_name='interaction_logs')
    op.drop_index('idx_interaction_type', table_name='interaction_logs')
    op.drop_index('idx_interaction_session', table_name='interaction_logs')
    op.drop_index('idx_interaction_pseudonym', table_name='interaction_logs')
    op.drop_table('interaction_logs')

    op.drop_index('idx_feedback_created', table_name='feedback_records')
    op.drop_index('idx_feedback_round', table_name='feedback_records')
    op.drop_index('idx_feedback_image', table_name='feedback_records')
    op.drop_index('idx_feedback_session', table_name='feedback_records')
    op.drop_index('idx_feedback_pseudonym', table_name='feedback_records')
    op.drop_table('feedback_records')

    op.drop_index('idx_chat_type', table_name='chat_messages')
    op.drop_index('idx_chat_timestamp', table_name='chat_messages')
    op.drop_index('idx_chat_session', table_name='chat_messages')
    op.drop_index('idx_chat_pseudonym', table_name='chat_messages')
    op.drop_table('chat_messages')

    op.drop_index('idx_generated_image_pald_source', table_name='generated_images')
    op.drop_index('idx_generated_image_created', table_name='generated_images')
    op.drop_index('idx_generated_image_session', table_name='generated_images')
    op.drop_index('idx_generated_image_pseudonym', table_name='generated_images')
    op.drop_table('generated_images')

    op.drop_index('idx_study_pald_created', table_name='study_pald_data')
    op.drop_index('idx_study_pald_type', table_name='study_pald_data')
    op.drop_index('idx_study_pald_session', table_name='study_pald_data')
    op.drop_index('idx_study_pald_pseudonym', table_name='study_pald_data')
    op.drop_table('study_pald_data')

    op.drop_index('idx_study_survey_completed', table_name='study_survey_responses')
    op.drop_index('idx_study_survey_version', table_name='study_survey_responses')
    op.drop_index('idx_study_survey_pseudonym', table_name='study_survey_responses')
    op.drop_table('study_survey_responses')

    op.drop_index('idx_study_consent_granted_at', table_name='study_consent_records')
    op.drop_index('idx_study_consent_pseudonym_type', table_name='study_consent_records')
    op.drop_table('study_consent_records')

    op.drop_index('idx_pseudonym_active', table_name='pseudonyms')
    op.drop_index('idx_pseudonym_text', table_name='pseudonyms')
    op.drop_index('idx_pseudonym_user', table_name='pseudonyms')
    op.drop_table('pseudonyms')