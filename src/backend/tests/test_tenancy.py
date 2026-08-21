#!/usr/bin/env python3
"""
Multi-tenancy Tests

Verifies that data is scoped to the tenant carried in the access token and that a
member of one tenant cannot read or mutate another tenant's records.
"""

import os
import sys
import unittest
from datetime import date

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from config import Config
from models import Invoice, TenantMembership, db


class TestConfig(Config):
    SQLALCHEMY_DATABASE_URI = 'sqlite://'
    TESTING = True


class TenancyTestCase(unittest.TestCase):
    """Base fixture with two registered users, each owning their own tenant."""

    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def register(self, username, company_name):
        response = self.client.post('/api/auth/register', json={
            'username': username,
            'email': f'{username}@example.com',
            'password': 'topsecretpassword',
            'company_name': company_name
        })
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()

    @staticmethod
    def auth(token):
        return {'Authorization': f'Bearer {token}'}

    def create_invoice(self, token, customer_name='Customer'):
        response = self.client.post('/api/invoices/', headers=self.auth(token), json={
            'customer_name': customer_name,
            'due_date': '2030-01-31',
            'items': [{'description': 'Work', 'quantity': 2, 'unit_price': 50}]
        })
        self.assertEqual(response.status_code, 201, response.get_json())
        return response.get_json()['invoice']


class TestTenantProvisioning(TenancyTestCase):
    """Registration and login issue tokens scoped to a tenant."""

    def test_register_creates_owned_tenant(self):
        body = self.register('alice', 'Acme Inc')

        self.assertEqual(body['tenant']['name'], 'Acme Inc')
        self.assertEqual(body['tenant']['slug'], 'acme-inc')

        membership = TenantMembership.query.filter_by(
            tenant_id=body['tenant']['id'], user_id=body['user']['id']
        ).first()
        self.assertIsNotNone(membership)
        self.assertEqual(membership.role, 'owner')

    def test_tenant_slugs_are_unique(self):
        first = self.register('alice', 'Acme Inc')
        second = self.register('bob', 'Acme Inc')

        self.assertEqual(first['tenant']['slug'], 'acme-inc')
        self.assertEqual(second['tenant']['slug'], 'acme-inc-2')

    def test_login_returns_tenant_scoped_token(self):
        self.register('alice', 'Acme Inc')

        response = self.client.post('/api/auth/login', json={
            'username': 'alice', 'password': 'topsecretpassword'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('tenant', response.get_json())

    def test_request_without_tenant_claim_is_rejected(self):
        from flask_jwt_extended import create_access_token

        alice = self.register('alice', 'Acme Inc')
        legacy_token = create_access_token(identity=str(alice['user']['id']))

        response = self.client.get('/api/invoices/', headers=self.auth(legacy_token))

        self.assertEqual(response.status_code, 401)

    def test_membership_revoked_after_token_issued(self):
        alice = self.register('alice', 'Acme Inc')
        TenantMembership.query.filter_by(user_id=alice['user']['id']).delete()
        db.session.commit()

        response = self.client.get('/api/invoices/', headers=self.auth(alice['access_token']))

        self.assertEqual(response.status_code, 403)


class TestTenantIsolation(TenancyTestCase):
    """One tenant's records are invisible and immutable to another tenant."""

    def setUp(self):
        super().setUp()
        self.alice = self.register('alice', 'Acme Inc')
        self.bob = self.register('bob', 'Globex')
        self.alice_invoice = self.create_invoice(self.alice['access_token'], 'Acme Customer')

    def test_list_invoices_only_returns_own_tenant(self):
        response = self.client.get('/api/invoices/', headers=self.auth(self.bob['access_token']))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['invoices'], [])

    def test_get_other_tenants_invoice_is_not_found(self):
        response = self.client.get(f"/api/invoices/{self.alice_invoice['id']}",
                                   headers=self.auth(self.bob['access_token']))

        self.assertEqual(response.status_code, 404)

    def test_update_other_tenants_invoice_is_not_found(self):
        response = self.client.put(f"/api/invoices/{self.alice_invoice['id']}",
                                   headers=self.auth(self.bob['access_token']),
                                   json={'customer_name': 'Hijacked'})

        self.assertEqual(response.status_code, 404)

    def test_delete_other_tenants_invoice_is_not_found(self):
        response = self.client.delete(f"/api/invoices/{self.alice_invoice['id']}",
                                      headers=self.auth(self.bob['access_token']))

        self.assertEqual(response.status_code, 404)

    def test_invoice_numbers_may_repeat_across_tenants(self):
        duplicate = Invoice(
            invoice_number=self.alice_invoice['invoice_number'],
            tenant_id=self.bob['tenant']['id'],
            user_id=self.bob['user']['id'],
            customer_name='Globex Customer',
            issue_date=date(2030, 1, 1),
            due_date=date(2030, 1, 31)
        )
        db.session.add(duplicate)
        db.session.commit()

        self.assertNotEqual(duplicate.tenant_id, self.alice_invoice['tenant_id'])

    def test_dashboard_and_reports_are_tenant_scoped(self):
        dashboard = self.client.get('/api/reports/dashboard',
                                    headers=self.auth(self.bob['access_token']))
        self.assertEqual(dashboard.status_code, 200)
        self.assertEqual(dashboard.get_json()['overview']['total_invoices'], 0)

        generated = self.client.post('/api/reports/generate',
                                     headers=self.auth(self.bob['access_token']),
                                     json={'report_type': 'custom',
                                           'start_date': '2000-01-01',
                                           'end_date': '2100-01-01'})
        self.assertEqual(generated.status_code, 201)
        self.assertEqual(generated.get_json()['report']['data']['summary']['total_invoices'], 0)

        alice_dashboard = self.client.get('/api/reports/dashboard',
                                          headers=self.auth(self.alice['access_token']))
        self.assertEqual(alice_dashboard.get_json()['overview']['total_invoices'], 1)

    def test_reports_list_excludes_other_tenants(self):
        self.client.post('/api/reports/generate', headers=self.auth(self.alice['access_token']),
                         json={'report_type': 'custom', 'start_date': '2000-01-01',
                               'end_date': '2100-01-01'})

        response = self.client.get('/api/reports/', headers=self.auth(self.bob['access_token']))

        self.assertEqual(response.get_json()['reports'], [])


class TestTenantSwitching(TenancyTestCase):
    """Users belonging to several tenants can move between them."""

    def setUp(self):
        super().setUp()
        self.alice = self.register('alice', 'Acme Inc')
        self.bob = self.register('bob', 'Globex')

    def test_switch_to_tenant_with_membership(self):
        globex_id = self.bob['tenant']['id']
        db.session.add(TenantMembership(tenant_id=globex_id,
                                        user_id=self.alice['user']['id'],
                                        role='member'))
        db.session.commit()

        response = self.client.post('/api/auth/tenants/switch',
                                    headers=self.auth(self.alice['access_token']),
                                    json={'tenant_id': globex_id})

        self.assertEqual(response.status_code, 200)
        new_token = response.get_json()['access_token']
        self.assertEqual(
            self.client.get('/api/invoices/', headers=self.auth(new_token)).status_code, 200)

    def test_switch_without_membership_is_forbidden(self):
        response = self.client.post('/api/auth/tenants/switch',
                                    headers=self.auth(self.alice['access_token']),
                                    json={'tenant_id': self.bob['tenant']['id']})

        self.assertEqual(response.status_code, 403)

    def test_list_tenants_returns_memberships(self):
        response = self.client.get('/api/auth/tenants',
                                   headers=self.auth(self.alice['access_token']))

        self.assertEqual(response.status_code, 200)
        tenants = response.get_json()['tenants']
        self.assertEqual(len(tenants), 1)
        self.assertEqual(tenants[0]['tenant']['slug'], 'acme-inc')

    def test_login_can_select_tenant_by_slug(self):
        db.session.add(TenantMembership(tenant_id=self.bob['tenant']['id'],
                                        user_id=self.alice['user']['id'],
                                        role='member'))
        db.session.commit()

        response = self.client.post('/api/auth/login', json={
            'username': 'alice', 'password': 'topsecretpassword', 'tenant_slug': 'globex'
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['tenant']['slug'], 'globex')

    def test_login_with_unauthorized_tenant_slug_is_forbidden(self):
        response = self.client.post('/api/auth/login', json={
            'username': 'alice', 'password': 'topsecretpassword', 'tenant_slug': 'globex'
        })

        self.assertEqual(response.status_code, 403)

    def test_users_without_membership_cannot_log_in(self):
        TenantMembership.query.filter_by(user_id=self.alice['user']['id']).delete()
        db.session.commit()

        response = self.client.post('/api/auth/login', json={
            'username': 'alice', 'password': 'topsecretpassword'
        })

        self.assertEqual(response.status_code, 403)


def run_tenancy_tests():
    """Run all tenancy tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite([
        loader.loadTestsFromTestCase(TestTenantProvisioning),
        loader.loadTestsFromTestCase(TestTenantIsolation),
        loader.loadTestsFromTestCase(TestTenantSwitching),
    ])
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite).wasSuccessful()


if __name__ == "__main__":
    sys.exit(0 if run_tenancy_tests() else 1)
