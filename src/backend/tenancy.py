"""Tenant resolution and scoping helpers.

The active tenant is carried in the ``tenant_id`` claim of the access token, so every
request is unambiguously scoped to a single tenant. ``tenant_required`` validates that
claim against the caller's memberships on each request, so revoking a membership takes
effect immediately even while an old token is still valid.
"""

import re
from functools import wraps

from flask import g, jsonify
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required

from models import Tenant, TenantMembership, User

TENANT_CLAIM = 'tenant_id'


def slugify(value, fallback='tenant'):
    """Turn a tenant name into a URL-safe slug."""
    slug = re.sub(r'[^a-z0-9]+', '-', (value or '').lower()).strip('-')
    return slug or fallback


def unique_slug(value, fallback='tenant'):
    """Return a slug that is not yet taken, appending a counter when needed."""
    base = slugify(value, fallback)
    slug = base
    counter = 2
    while Tenant.query.filter_by(slug=slug).first():
        slug = f'{base}-{counter}'
        counter += 1
    return slug


def tenant_required(fn):
    """Require a valid access token whose tenant claim matches a membership of the caller.

    Populates ``g.user``, ``g.tenant_id`` and ``g.membership``.
    """
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user_id = int(get_jwt_identity())
        tenant_id = get_jwt().get(TENANT_CLAIM)

        if tenant_id is None:
            return jsonify({'error': 'Token is not scoped to a tenant; log in again'}), 401

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        membership = TenantMembership.query.filter_by(user_id=user_id, tenant_id=tenant_id).first()
        if not membership:
            return jsonify({'error': 'No access to this tenant'}), 403

        g.user = user
        g.tenant_id = tenant_id
        g.membership = membership
        return fn(*args, **kwargs)

    return wrapper


def current_tenant_id():
    """Id of the tenant the current request is scoped to."""
    return g.tenant_id


def current_user():
    """User making the current request."""
    return g.user


def tenant_query(model):
    """Query for ``model`` restricted to the active tenant."""
    return model.query.filter_by(tenant_id=g.tenant_id)
