"""corrigido id do PessoaFolha para autoincrement

Revision ID: 2fff14beb459
Revises: 9560e9b43352
Create Date: 2025-05-06 17:50:53.462993

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2fff14beb459'
down_revision = '9560e9b43352'
branch_labels = None
depends_on = None

def upgrade():
    # Create a sequence for the id column
    op.execute("CREATE SEQUENCE IF NOT EXISTS pessoa_folha_id_seq")
    
    # Add the id column if it doesn't exist
    op.add_column('pessoa_folha', sa.Column('id', sa.Integer(), nullable=True))
    
    # Populate NULL ids with sequence values
    op.execute("""
        UPDATE pessoa_folha
        SET id = nextval('pessoa_folha_id_seq')
        WHERE id IS NULL
    """)
    
    # Set the sequence to the maximum id
    op.execute("""
        SELECT setval('pessoa_folha_id_seq', (SELECT COALESCE(MAX(id), 1) FROM pessoa_folha))
    """)
    
    # Make id NOT NULL and set as primary key
    with op.batch_alter_table('pessoa_folha', schema=None) as batch_op:
        batch_op.alter_column('id', existing_type=sa.Integer(), nullable=False)
        batch_op.drop_constraint('pessoa_folha_pkey', type_='primary')
        batch_op.create_primary_key('pessoa_folha_pkey', ['id'])

def downgrade():
    with op.batch_alter_table('pessoa_folha', schema=None) as batch_op:
        batch_op.drop_constraint('pessoa_folha_pkey', type_='primary')
        batch_op.create_primary_key('pessoa_folha_pkey', ['pessoa_id', 'folha_id'])
        batch_op.drop_column('id')
    
    op.execute("DROP SEQUENCE IF EXISTS pessoa_folha_id_seq")