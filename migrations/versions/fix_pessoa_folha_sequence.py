"""fix pessoa folha sequence

Revision ID: fix_pessoa_folha_sequence
Revises: 295f0f24f4cf
Create Date: 2025-05-06 19:15:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'fix_pessoa_folha_sequence'
down_revision = '295f0f24f4cf'
branch_labels = None
depends_on = None


def upgrade():
    # Drop the existing sequence if it exists
    op.execute("DROP SEQUENCE IF EXISTS pessoa_folha_id_seq")
    
    # Create a new sequence
    op.execute("CREATE SEQUENCE pessoa_folha_id_seq")
    
    # Set the sequence to the maximum id
    op.execute("""
        SELECT setval('pessoa_folha_id_seq', COALESCE((SELECT MAX(id) FROM pessoa_folha), 0))
    """)
    
    # Alter the table to use the sequence
    op.execute("""
        ALTER TABLE pessoa_folha 
        ALTER COLUMN id SET DEFAULT nextval('pessoa_folha_id_seq')
    """)


def downgrade():
    # Remove the default value
    op.execute("""
        ALTER TABLE pessoa_folha 
        ALTER COLUMN id DROP DEFAULT
    """)
    
    # Drop the sequence
    op.execute("DROP SEQUENCE IF EXISTS pessoa_folha_id_seq") 