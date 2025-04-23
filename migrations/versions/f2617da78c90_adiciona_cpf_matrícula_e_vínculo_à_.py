"""Adiciona CPF, Matrícula e Vínculo à tabela Pessoa

Revision ID: f2617da78c90
Revises: 92efd982d0e8
Create Date: 2025-04-23 11:24:41.591484

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f2617da78c90'
down_revision = '92efd982d0e8'
branch_labels = None
depends_on = None


def upgrade():
    # Adiciona as colunas com valores padrão
    op.add_column('pessoa', sa.Column('cpf', sa.String(length=14), nullable=False, server_default='000.000.000-00'))
    op.add_column('pessoa', sa.Column('matricula', sa.String(length=20), nullable=False, server_default='MAT-000'))
    op.add_column('pessoa', sa.Column('vinculo', sa.String(length=50), nullable=False, server_default='Desconhecido'))

    # Opcional: atualiza os valores padrão com lógica personalizada
    op.execute("UPDATE pessoa SET matricula = 'MAT-' || id WHERE matricula = 'MAT-000'")

def downgrade():
    # Remove as colunas no caso de rollback
    op.drop_column('pessoa', 'vinculo')
    op.drop_column('pessoa', 'matricula')
    op.drop_column('pessoa', 'cpf')
