"""alteração no campo motivo para observacao na tabela atestado

Revision ID: 5975d47a30a7
Revises: 097b845495d1
Create Date: 2025-06-06 17:54:00
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '5975d47a30a7'
down_revision = '097b845495d1'
branch_labels = None
depends_on = None

def upgrade():
    # Adiciona a coluna observacao como anulável
    with op.batch_alter_table('atestado', schema=None) as batch_op:
        batch_op.add_column(sa.Column('observacao', sa.String(length=200), nullable=True))

    # Copia os dados de motivo para observacao
    op.execute("UPDATE atestado SET observacao = motivo WHERE motivo IS NOT NULL")

    # Torna a coluna observacao NOT NULL
    with op.batch_alter_table('atestado', schema=None) as batch_op:
        batch_op.alter_column('observacao', nullable=False)

    # Remove a coluna motivo
    with op.batch_alter_table('atestado', schema=None) as batch_op:
        batch_op.drop_column('motivo')

def downgrade():
    # Reverte as alterações: adiciona motivo, copia observacao para motivo, remove observacao
    with op.batch_alter_table('atestado', schema=None) as batch_op:
        batch_op.add_column(sa.Column('motivo', sa.String(length=200), nullable=True))

    op.execute("UPDATE atestado SET motivo = observacao WHERE observacao IS NOT NULL")

    with op.batch_alter_table('atestado', schema=None) as batch_op:
        batch_op.alter_column('motivo', nullable=False)
        batch_op.drop_column('observacao')