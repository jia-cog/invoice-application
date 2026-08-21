"""Shared-schema multi-tenancy: tenants, memberships and tenant_id scoping.

Existing data is migrated into one tenant per user, with that user as owner.

Revision ID: 0002
Revises: 0001
"""
import re

import sqlalchemy as sa
from alembic import op

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def _slugify(value, fallback):
    slug = re.sub(r'[^a-z0-9]+', '-', (value or '').lower()).strip('-')
    return slug or fallback


def _backfill_tenants(bind):
    """Create one tenant per existing user and point their rows at it."""
    users = bind.execute(sa.text(
        'SELECT id, username, company_name FROM "user" ORDER BY id'
    )).fetchall()

    taken = set()
    for user_id, username, company_name in users:
        name = company_name or username
        base = _slugify(name, f'tenant-{user_id}')
        slug, counter = base, 2
        while slug in taken:
            slug = f'{base}-{counter}'
            counter += 1
        taken.add(slug)

        tenant_id = bind.execute(
            sa.text('INSERT INTO tenant (name, slug, created_at) '
                    'VALUES (:name, :slug, NOW()) RETURNING id'),
            {'name': name, 'slug': slug},
        ).scalar()

        bind.execute(
            sa.text('INSERT INTO tenant_membership (tenant_id, user_id, role, created_at) '
                    "VALUES (:tenant_id, :user_id, 'owner', NOW())"),
            {'tenant_id': tenant_id, 'user_id': user_id},
        )
        for table in ('invoice', 'report'):
            bind.execute(
                sa.text(f'UPDATE {table} SET tenant_id = :tenant_id WHERE user_id = :user_id'),
                {'tenant_id': tenant_id, 'user_id': user_id},
            )


def upgrade():
    op.create_table(
        'tenant',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('slug', sa.String(length=80), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
    )
    op.create_table(
        'tenant_membership',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenant.id']),
        sa.ForeignKeyConstraint(['user_id'], ['user.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'user_id', name='uq_membership_tenant_user'),
    )
    op.create_index('ix_tenant_membership_tenant_id', 'tenant_membership', ['tenant_id'])
    op.create_index('ix_tenant_membership_user_id', 'tenant_membership', ['user_id'])

    # Added nullable, backfilled, then made mandatory.
    op.add_column('invoice', sa.Column('tenant_id', sa.Integer(), nullable=True))
    op.add_column('report', sa.Column('tenant_id', sa.Integer(), nullable=True))

    _backfill_tenants(op.get_bind())

    op.alter_column('invoice', 'tenant_id', nullable=False)
    op.alter_column('report', 'tenant_id', nullable=False)
    op.create_foreign_key('fk_invoice_tenant_id', 'invoice', 'tenant', ['tenant_id'], ['id'])
    op.create_foreign_key('fk_report_tenant_id', 'report', 'tenant', ['tenant_id'], ['id'])
    op.create_index('ix_invoice_tenant_id', 'invoice', ['tenant_id'])
    op.create_index('ix_report_tenant_id', 'report', ['tenant_id'])

    # Invoice numbers are only unique within a tenant.
    op.drop_constraint('invoice_invoice_number_key', 'invoice', type_='unique')
    op.create_unique_constraint('uq_invoice_tenant_number', 'invoice',
                                ['tenant_id', 'invoice_number'])


def downgrade():
    op.drop_constraint('uq_invoice_tenant_number', 'invoice', type_='unique')
    op.create_unique_constraint('invoice_invoice_number_key', 'invoice', ['invoice_number'])
    op.drop_index('ix_report_tenant_id', table_name='report')
    op.drop_index('ix_invoice_tenant_id', table_name='invoice')
    op.drop_constraint('fk_report_tenant_id', 'report', type_='foreignkey')
    op.drop_constraint('fk_invoice_tenant_id', 'invoice', type_='foreignkey')
    op.drop_column('report', 'tenant_id')
    op.drop_column('invoice', 'tenant_id')
    op.drop_index('ix_tenant_membership_user_id', table_name='tenant_membership')
    op.drop_index('ix_tenant_membership_tenant_id', table_name='tenant_membership')
    op.drop_table('tenant_membership')
    op.drop_table('tenant')
