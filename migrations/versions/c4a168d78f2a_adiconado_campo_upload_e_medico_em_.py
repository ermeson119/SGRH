"""adiconado campo upload e medico em atestdo

Revision ID: c4a168d78f2a
Revises: 460f96441767
Create Date: 2025-05-05 16:09:34.454239

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4a168d78f2a'
down_revision = '460f96441767'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('atestado', schema=None) as batch_op:
        # Primeiro adiciona as colunas como nullable
        batch_op.add_column(sa.Column('medico', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('arquivo', sa.String(length=255), nullable=True))

    # Atualiza os registros existentes
    op.execute("UPDATE atestado SET medico = 'Médico não registrado' WHERE medico IS NULL")

    # Agora altera a coluna medico para NOT NULL
    with op.batch_alter_table('atestado', schema=None) as batch_op:
        batch_op.alter_column('medico',
                            existing_type=sa.String(length=200),
                            nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('atestado', schema=None) as batch_op:
        batch_op.drop_column('arquivo')
        batch_op.drop_column('medico')

    # ### end Alembic commands ###
