"""Add tabela RegistrationRequest

Revision ID: 4438b40c1595
Revises: 915db0d93d3c
Create Date: 2025-04-24 15:25:00.000000
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4438b40c1595'
down_revision = '915db0d93d3c'
branch_labels = None
depends_on = None

def upgrade():
    # Criar a tabela registration_requests
    op.create_table('registration_requests',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=100), nullable=False),
        sa.Column('password', sa.String(length=255), nullable=True),
        sa.Column('auth_method', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_registration_requests_email'), 'registration_requests', ['email'], unique=False)

    # Adicionar colunas status e is_admin à tabela users
    # Passo 1: Adicionar as colunas sem NOT NULL
    op.add_column('users', sa.Column('status', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('is_admin', sa.Boolean(), nullable=True))

    # Passo 2: Definir valores padrão para os registros existentes
    op.execute("UPDATE users SET status = 'pending' WHERE status IS NULL")
    op.execute("UPDATE users SET is_admin = FALSE WHERE is_admin IS NULL")

    # Passo 3: Aplicar a restrição NOT NULL
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('status', nullable=False)
        batch_op.alter_column('is_admin', nullable=False)

def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('is_admin')
        batch_op.drop_column('status')

    op.drop_index(op.f('ix_registration_requests_email'), table_name='registration_requests')
    op.drop_table('registration_requests')