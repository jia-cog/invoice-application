"""Baseline schema as it existed before multi-tenancy.

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=80), nullable=False),
        sa.Column('email', sa.String(length=120), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('company_name', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username'),
    )
    op.create_table(
        'invoice',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_number', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('customer_name', sa.String(length=200), nullable=False),
        sa.Column('customer_email', sa.String(length=120), nullable=True),
        sa.Column('customer_address', sa.Text(), nullable=True),
        sa.Column('issue_date', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=True),
        sa.Column('subtotal', sa.Float(), nullable=True),
        sa.Column('tax_rate', sa.Float(), nullable=True),
        sa.Column('tax_amount', sa.Float(), nullable=True),
        sa.Column('total_amount', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('invoice_number'),
    )
    op.create_table(
        'invoice_item',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('invoice_id', sa.Integer(), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=False),
        sa.Column('quantity', sa.Float(), nullable=False),
        sa.Column('unit_price', sa.Float(), nullable=False),
        sa.Column('total', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoice.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_table(
        'report',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('report_type', sa.String(length=50), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('data', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade():
    op.drop_table('report')
    op.drop_table('invoice_item')
    op.drop_table('invoice')
    op.drop_table('user')
