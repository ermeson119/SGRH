"""Adiciona tabela Curso e ajusta Capacitacao

Revision ID: 92efd982d0e8
Revises: 4bcdaa5d060a
Create Date: 2025-04-22 21:15:14.248382

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '92efd982d0e8'
down_revision = '4bcdaa5d060a'
branch_labels = None
depends_on = None


def upgrade():
    # Criar a tabela curso
    op.create_table(
        'curso',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=100), nullable=False),
        sa.Column('duracao', sa.String(length=50), nullable=False),
        sa.Column('tipo', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Adicionar a coluna curso_id como nullable
    op.add_column('capacitacao', sa.Column('curso_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'capacitacao', 'curso', ['curso_id'], ['id'])

    # ### end Alembic commands ###


def downgrade():
    op.drop_constraint(None, 'capacitacao', type_='foreignkey')
    op.drop_column('capacitacao', 'curso_id')
    op.drop_table('curso')
    # ### end Alembic commands ###
