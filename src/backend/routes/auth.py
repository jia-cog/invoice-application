from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from models import db, Tenant, TenantMembership, User
from tenancy import TENANT_CLAIM, tenant_required, unique_slug

auth_bp = Blueprint('auth', __name__)


def _token_for(user, tenant_id):
    return create_access_token(identity=str(user.id),
                               additional_claims={TENANT_CLAIM: tenant_id})


def _default_tenant_id(user, requested_slug=None):
    """Resolve which tenant a login should be scoped to.

    Uses the requested tenant when the user is a member of it, otherwise the oldest
    membership. Returns ``None`` when the user has no access to the requested tenant.
    """
    memberships = TenantMembership.query.filter_by(user_id=user.id).order_by(
        TenantMembership.created_at.asc(), TenantMembership.id.asc()
    ).all()

    if requested_slug:
        tenant = Tenant.query.filter_by(slug=requested_slug).first()
        if not tenant:
            return None
        return tenant.id if any(m.tenant_id == tenant.id for m in memberships) else None

    return memberships[0].tenant_id if memberships else None


@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        # Check if user already exists
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 400

        if User.query.filter_by(email=data['email']).first():
            return jsonify({'error': 'Email already exists'}), 400

        # Create new user
        user = User(
            username=data['username'],
            email=data['email'],
            company_name=data.get('company_name', '')
        )
        user.set_password(data['password'])

        db.session.add(user)
        db.session.flush()

        # Registration creates the user's own tenant, owned by them
        tenant_name = data.get('tenant_name') or data.get('company_name') or data['username']
        tenant = Tenant(name=tenant_name, slug=unique_slug(tenant_name, data['username']))
        db.session.add(tenant)
        db.session.flush()
        db.session.add(TenantMembership(tenant_id=tenant.id, user_id=user.id, role='owner'))

        db.session.commit()

        return jsonify({
            'message': 'User created successfully',
            'access_token': _token_for(user, tenant.id),
            'user': user.to_dict(),
            'tenant': tenant.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get('username') or not data.get('password'):
            return jsonify({'error': 'Username and password are required'}), 400

        # Find user
        user = User.query.filter_by(username=data['username']).first()

        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid credentials'}), 401

        tenant_id = _default_tenant_id(user, data.get('tenant_slug'))
        if tenant_id is None:
            return jsonify({'error': 'User has no accessible tenant'}), 403

        tenant = Tenant.query.get(tenant_id)

        return jsonify({
            'message': 'Login successful',
            'access_token': _token_for(user, tenant_id),
            'user': user.to_dict(),
            'tenant': tenant.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    try:
        user_id = int(get_jwt_identity())
        user = User.query.get(user_id)

        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({'user': user.to_dict()}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/tenants', methods=['GET'])
@jwt_required()
def list_tenants():
    """List the tenants the caller belongs to, with their role in each."""
    try:
        user_id = int(get_jwt_identity())
        memberships = TenantMembership.query.filter_by(user_id=user_id).all()

        return jsonify({'tenants': [m.to_dict() for m in memberships]}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@auth_bp.route('/tenants/switch', methods=['POST'])
@tenant_required
def switch_tenant():
    """Issue a new token scoped to another tenant the caller is a member of."""
    try:
        data = request.get_json() or {}
        tenant_id = data.get('tenant_id')
        tenant_slug = data.get('tenant_slug')

        if not tenant_id and not tenant_slug:
            return jsonify({'error': 'tenant_id or tenant_slug is required'}), 400

        tenant = (Tenant.query.get(tenant_id) if tenant_id
                  else Tenant.query.filter_by(slug=tenant_slug).first())
        if not tenant:
            return jsonify({'error': 'Tenant not found'}), 404

        if not g.user.membership_for(tenant.id):
            return jsonify({'error': 'No access to this tenant'}), 403

        return jsonify({
            'access_token': _token_for(g.user, tenant.id),
            'tenant': tenant.to_dict()
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
