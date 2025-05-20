"""initial schema

Revision ID: 7960c45348f1
Revises:
Create Date: 2024-03-19 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7960c45348f1'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Criar tabela users
    op.create_table('users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(), nullable=False),
        sa.Column('password', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('phone', sa.String(), nullable=True),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )

    # Criar tabela services
    op.create_table('services',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.DECIMAL(10,2), nullable=True),
        sa.Column('active', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Criar tabela appointments
    op.create_table('appointments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('service_id', sa.Integer(), nullable=True),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('time', sa.Time(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.String(), nullable=True),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('price', sa.DECIMAL(10,2), nullable=True),
        sa.Column('image_path', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )

    # Criar tabela config
    op.create_table('config',
        sa.Column('weekday', sa.Integer(), nullable=False),
        sa.Column('max_appointments', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('weekday')
    )

    # Criar tabela gallery
    op.create_table('gallery',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('before_path', sa.String(), nullable=False),
        sa.Column('after_path', sa.String(), nullable=False),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Criar tabela auth_tokens
    op.create_table('auth_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.String(), nullable=False),
        sa.Column('expires_at', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )

def downgrade():
    op.drop_table('auth_tokens')
    op.drop_table('gallery')
    op.drop_table('config')
    op.drop_table('appointments')
    op.drop_table('services')
    op.drop_table('users')
