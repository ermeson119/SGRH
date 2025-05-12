"""Corrigir coluna duracao da tabela curso

Revision ID: fix_curso_duracao
Revises: 3c1c4f5a91e2
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'fix_curso_duracao'
down_revision = '3c1c4f5a91e2'
branch_labels = None
depends_on = None

def upgrade():
    # Criar coluna temporária
    op.add_column('curso', sa.Column('duracao_temp', sa.DECIMAL(10, 1), nullable=True))
    
    # Atualizar a coluna temporária com os dados convertidos
    op.execute("""
        UPDATE curso 
        SET duracao_temp = CASE 
            WHEN CAST(duracao AS TEXT) ~ '^[0-9]+(\.[0-9]+)?$' THEN CAST(duracao AS DECIMAL(10,1))
            ELSE 0.0
        END
    """)
    
    # Remover a coluna antiga
    op.drop_column('curso', 'duracao')
    
    # Renomear a coluna temporária
    op.alter_column('curso', 'duracao_temp', new_column_name='duracao', nullable=False)

def downgrade():
    # Criar coluna temporária
    op.add_column('curso', sa.Column('duracao_temp', sa.Float(), nullable=True))
    
    # Atualizar a coluna temporária com os dados convertidos
    op.execute("""
        UPDATE curso 
        SET duracao_temp = CAST(duracao AS FLOAT)
    """)
    
    # Remover a coluna antiga
    op.drop_column('curso', 'duracao')
    
    # Renomear a coluna temporária
    op.alter_column('curso', 'duracao_temp', new_column_name='duracao', nullable=False) 