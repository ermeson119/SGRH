"""Add arquivo column to exame table

Revision ID: 460f96441767
Revises: c4e83c2ab377
Create Date: 2025-05-05 14:47:25.356533

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '460f96441767'
down_revision = 'c4e83c2ab377'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('exame', schema=None) as batch_op:
        batch_op.add_column(sa.Column('arquivo', sa.String(length=255), nullable=True))
        batch_op.drop_index('ix_exame_pessoa_id')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('exame', schema=None) as batch_op:
        batch_op.create_index('ix_exame_pessoa_id', ['pessoa_id'], unique=False)
        batch_op.drop_column('arquivo')

    # ### end Alembic commands ###
