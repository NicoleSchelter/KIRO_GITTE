"""Initial database schema with users, consent, PALD, audit logs, and FL updates

Revision ID: 81502a5683af
Revises: 
Create Date: 2025-08-10 17:33:45.608854

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '81502a5683af'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table('users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('username', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=50), nullable=False),
        sa.Column('pseudonym', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('pseudonym')
    )
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=False)
    op.create_index(op.f('ix_users_pseudonym'), 'users', ['pseudonym'], unique=False)

    # Create PALD schema versions table
    op.create_table('pald_schema_versions',
        sa.Column('version', sa.String(length=50), nullable=False),
        sa.Column('schema_content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('migration_notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('version')
    )

    # Create consent records table
    op.create_table('consent_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('consent_type', sa.String(length=100), nullable=False),
        sa.Column('consent_given', sa.Boolean(), nullable=False),
        sa.Column('consent_version', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('consent_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('withdrawn_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_consent_user_type', 'consent_records', ['user_id', 'consent_type'], unique=False)
    op.create_index('idx_consent_timestamp', 'consent_records', ['timestamp'], unique=False)

    # Create PALD attribute candidates table
    op.create_table('pald_attribute_candidates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('attribute_name', sa.String(length=255), nullable=False),
        sa.Column('attribute_category', sa.String(length=100), nullable=True),
        sa.Column('mention_count', sa.Integer(), nullable=False, server_default=sa.text('1')),
        sa.Column('first_detected', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('last_mentioned', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('threshold_reached', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('added_to_schema', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('schema_version_added', sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_attribute_name', 'pald_attribute_candidates', ['attribute_name'], unique=False)
    op.create_index('idx_attribute_threshold', 'pald_attribute_candidates', ['threshold_reached'], unique=False)
    op.create_index('idx_attribute_added', 'pald_attribute_candidates', ['added_to_schema'], unique=False)

    # Create PALD data table
    op.create_table('pald_data',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('pald_content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('schema_version', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('is_validated', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('validation_errors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['schema_version'], ['pald_schema_versions.version'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_pald_user', 'pald_data', ['user_id'], unique=False)
    op.create_index('idx_pald_schema_version', 'pald_data', ['schema_version'], unique=False)
    op.create_index('idx_pald_validated', 'pald_data', ['is_validated'], unique=False)

    # Create audit logs table
    op.create_table('audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('request_id', sa.String(length=255), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('operation', sa.String(length=100), nullable=False),
        sa.Column('model_used', sa.String(length=100), nullable=True),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('output_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('token_usage', sa.Integer(), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('parent_log_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default=sa.text("'initialized'")),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('finalized_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_log_id'], ['audit_logs.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_audit_request_id', 'audit_logs', ['request_id'], unique=False)
    op.create_index('idx_audit_user', 'audit_logs', ['user_id'], unique=False)
    op.create_index('idx_audit_operation', 'audit_logs', ['operation'], unique=False)
    op.create_index('idx_audit_status', 'audit_logs', ['status'], unique=False)
    op.create_index('idx_audit_created_at', 'audit_logs', ['created_at'], unique=False)
    op.create_index('idx_audit_parent', 'audit_logs', ['parent_log_id'], unique=False)

    # Create federated learning updates table
    op.create_table('fl_updates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('update_data', sa.LargeBinary(), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=False),
        sa.Column('aggregation_round', sa.Integer(), nullable=True),
        sa.Column('submitted_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('processed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('update_size_bytes', sa.Integer(), nullable=True),
        sa.Column('privacy_budget_used', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_fl_user', 'fl_updates', ['user_id'], unique=False)
    op.create_index('idx_fl_model_version', 'fl_updates', ['model_version'], unique=False)
    op.create_index('idx_fl_round', 'fl_updates', ['aggregation_round'], unique=False)
    op.create_index('idx_fl_processed', 'fl_updates', ['processed'], unique=False)
    op.create_index('idx_fl_submitted_at', 'fl_updates', ['submitted_at'], unique=False)

    # Create system metadata table
    op.create_table('system_metadata',
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('key')
    )

    # Insert initial PALD schema version
    op.execute("""
        INSERT INTO pald_schema_versions (version, schema_content, is_active, migration_notes)
        VALUES (
            '1.0.0',
            '{"type": "object", "properties": {"learning_style": {"type": "string", "enum": ["visual", "auditory", "kinesthetic", "reading"]}, "difficulty_preference": {"type": "string", "enum": ["beginner", "intermediate", "advanced"]}, "interaction_style": {"type": "string", "enum": ["formal", "casual", "encouraging", "direct"]}, "embodiment_preferences": {"type": "object", "properties": {"appearance": {"type": "string"}, "personality": {"type": "string"}, "voice_tone": {"type": "string"}}}, "subject_interests": {"type": "array", "items": {"type": "string"}}, "accessibility_needs": {"type": "array", "items": {"type": "string"}}}, "required": ["learning_style", "difficulty_preference", "interaction_style"]}',
            true,
            'Initial PALD schema with basic learning preferences and embodiment attributes'
        )
    """)

    # Insert system metadata
    op.execute("""
        INSERT INTO system_metadata (key, value)
        VALUES 
            ('database_version', '1.0.0'),
            ('schema_initialized', 'true'),
            ('pald_threshold_mentions', '10'),
            ('audit_retention_days', '365')
    """)


def downgrade() -> None:
    # Drop tables in reverse order due to foreign key constraints
    op.drop_table('system_metadata')
    op.drop_table('fl_updates')
    op.drop_table('audit_logs')
    op.drop_table('pald_data')
    op.drop_table('pald_attribute_candidates')
    op.drop_table('consent_records')
    op.drop_table('pald_schema_versions')
    op.drop_table('users')