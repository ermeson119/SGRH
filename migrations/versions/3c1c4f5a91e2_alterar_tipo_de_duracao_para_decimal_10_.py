"""Alterar tipo de duracao para DECIMAL(10,1) na tabela curso

Revision ID: 3c1c4f5a91e2
Revises: fix_pessoa_folha_sequence
Create Date: [data de criação original]

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '3c1c4f5a91e2'
down_revision = 'fix_pessoa_folha_sequence'
branch_labels = None
depends_on = None

def upgrade():
    # Alterar a coluna duracao para DECIMAL(10,1) com conversão explícita
    op.alter_column(
        'curso',
        'duracao',
        existing_type=sa.Float(),
        type_=sa.DECIMAL(10, 1),
        postgresql_using='duracao::numeric(10,1)',
        existing_nullable=False
    )

def downgrade():
    # Reverter para FLOAT, se necessário
    op.alter_column(
        'curso',
        'duracao',
        existing_type=sa.DECIMAL(10, 1),
        type_=sa.Float(),
        postgresql_using='duracao::double precision',
        existing_nullable=False
    )