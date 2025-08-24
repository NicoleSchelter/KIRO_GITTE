"""
Add uniqueness constraint to study consent records for idempotency.

Revision ID: add_consent_uniqueness
Revises: previous_migration
Create Date: 2025-01-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'add_consent_uniqueness'
down_revision = None  # Update this with the actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    """Add uniqueness constraint to study_consent_records."""
    
    # Add unique constraint on (pseudonym_id, consent_type, version)
    # This ensures idempotent consent writes
    op.create_index(
        'idx_study_consent_unique',
        'study_consent_records',
        ['pseudonym_id', 'consent_type', 'version'],
        unique=True
    )
    
    # Add index for performance on common queries
    op.create_index(
        'idx_study_consent_pseudonym_granted',
        'study_consent_records', 
        ['pseudonym_id', 'granted_at'],
        postgresql_where=sa.text('granted = true AND revoked_at IS NULL')
    )


def downgrade():
    """Remove uniqueness constraint from study_consent_records."""
    
    op.drop_index('idx_study_consent_unique', table_name='study_consent_records')
    op.drop_index('idx_study_consent_pseudonym_granted', table_name='study_consent_records')