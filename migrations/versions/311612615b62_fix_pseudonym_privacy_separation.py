"""fix_pseudonym_privacy_separation

Revision ID: 311612615b62
Revises: 0f0a4b52c7f6
Create Date: 2025-08-23 01:02:39.503061

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '311612615b62'
down_revision = '0f0a4b52c7f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Check if pseudonym_mappings table already exists
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'pseudonym_mappings' not in inspector.get_table_names():
        # Create pseudonym_mappings table for secure user-pseudonym association
        op.create_table('pseudonym_mappings',
            sa.Column('mapping_id', sa.UUID(), nullable=False),
            sa.Column('user_id', sa.UUID(), nullable=False),
            sa.Column('pseudonym_id', sa.UUID(), nullable=False),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('created_by', sa.String(length=100), nullable=False),
            sa.Column('access_level', sa.String(length=50), nullable=False),
            sa.ForeignKeyConstraint(['pseudonym_id'], ['pseudonyms.pseudonym_id'], ),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
            sa.PrimaryKeyConstraint('mapping_id')
        )
        op.create_index('idx_pseudonym_mapping_user', 'pseudonym_mappings', ['user_id'], unique=False)
        op.create_index('idx_pseudonym_mapping_pseudonym', 'pseudonym_mappings', ['pseudonym_id'], unique=False)
        op.create_index('idx_pseudonym_mapping_created', 'pseudonym_mappings', ['created_at'], unique=False)
        op.create_index('idx_pseudonym_mapping_unique_user', 'pseudonym_mappings', ['user_id'], unique=True)
        op.create_index('idx_pseudonym_mapping_unique_pseudonym', 'pseudonym_mappings', ['pseudonym_id'], unique=True)

    # Check if user_id column still exists in pseudonyms table
    pseudonym_columns = [col['name'] for col in inspector.get_columns('pseudonyms')]
    
    if 'user_id' in pseudonym_columns:
        # Migrate existing data from pseudonyms.user_id to pseudonym_mappings
        # First, create mappings for existing pseudonyms
        op.execute("""
            INSERT INTO pseudonym_mappings (mapping_id, user_id, pseudonym_id, created_at, created_by, access_level)
            SELECT 
                gen_random_uuid(),
                user_id,
                pseudonym_id,
                created_at,
                'migration_script',
                'admin_only'
            FROM pseudonyms
            WHERE user_id IS NOT NULL
            ON CONFLICT DO NOTHING
        """)

        # Remove the foreign key constraint from pseudonyms table
        try:
            op.drop_constraint('pseudonyms_user_id_fkey', 'pseudonyms', type_='foreignkey')
        except Exception:
            pass  # Constraint might not exist or have different name
        
        # Drop the old index if it exists
        pseudonym_indexes = [idx['name'] for idx in inspector.get_indexes('pseudonyms')]
        if 'idx_pseudonym_user' in pseudonym_indexes:
            op.drop_index('idx_pseudonym_user', table_name='pseudonyms')
        
        # Drop the user_id column from pseudonyms table
        op.drop_column('pseudonyms', 'user_id')
    
    # Add new indexes for pseudonyms table if they don't exist
    pseudonym_indexes = [idx['name'] for idx in inspector.get_indexes('pseudonyms')]
    if 'idx_pseudonym_hash' not in pseudonym_indexes:
        op.create_index('idx_pseudonym_hash', 'pseudonyms', ['pseudonym_hash'], unique=False)


def downgrade() -> None:
    # Add back user_id column to pseudonyms table
    op.add_column('pseudonyms', sa.Column('user_id', sa.UUID(), nullable=True))
    
    # Restore data from pseudonym_mappings back to pseudonyms.user_id
    op.execute("""
        UPDATE pseudonyms 
        SET user_id = pm.user_id
        FROM pseudonym_mappings pm
        WHERE pseudonyms.pseudonym_id = pm.pseudonym_id
    """)
    
    # Make user_id not nullable after data restoration
    op.alter_column('pseudonyms', 'user_id', nullable=False)
    
    # Restore foreign key constraint
    op.create_foreign_key('pseudonyms_user_id_fkey', 'pseudonyms', 'users', ['user_id'], ['id'])
    
    # Restore old index
    op.create_index('idx_pseudonym_user', 'pseudonyms', ['user_id'], unique=False)
    
    # Drop new index
    op.drop_index('idx_pseudonym_hash', table_name='pseudonyms')
    
    # Drop pseudonym_mappings table
    op.drop_index('idx_pseudonym_mapping_unique_pseudonym', table_name='pseudonym_mappings')
    op.drop_index('idx_pseudonym_mapping_unique_user', table_name='pseudonym_mappings')
    op.drop_index('idx_pseudonym_mapping_created', table_name='pseudonym_mappings')
    op.drop_index('idx_pseudonym_mapping_pseudonym', table_name='pseudonym_mappings')
    op.drop_index('idx_pseudonym_mapping_user', table_name='pseudonym_mappings')
    op.drop_table('pseudonym_mappings')