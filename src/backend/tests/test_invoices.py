#!/usr/bin/env python3
"""
Invoice Endpoints Tests

Comprehensive test coverage for all 5 invoice endpoints:
- GET /api/invoices/
- GET /api/invoices/<invoice_id>
- POST /api/invoices/
- PUT /api/invoices/<invoice_id>
- DELETE /api/invoices/<invoice_id>
"""

import sys
import os
import unittest

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, Invoice, InvoiceItem, User


class TestInvoiceEndpoints(unittest.TestCase):
    """Test cases for all invoice CRUD endpoints."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.app.config['JWT_SECRET_KEY'] = 'test-secret-key'

        self.app_context = self.app.app_context()
        self.app_context.push()

        db.create_all()

        self.client = self.app.test_client()

        # Register a test user and obtain a JWT token
        register_resp = self.client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'testpassword123',
            'company_name': 'Test Co'
        })
        register_data = register_resp.get_json()
        self.token = register_data['access_token']
        self.user_id = register_data['user']['id']

    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def auth_headers(self):
        """Return authorization headers with the test user's JWT token."""
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

    def _create_invoice(self, **overrides):
        """Helper to POST a valid invoice payload. Returns the response."""
        payload = {
            'customer_name': 'Jane Doe',
            'customer_email': 'jane@example.com',
            'customer_address': '123 Main St',
            'due_date': '2026-12-31',
            'tax_rate': 10.0,
            'notes': 'Test invoice',
            'items': [
                {
                    'description': 'Widget A',
                    'quantity': 2,
                    'unit_price': 50.0
                },
                {
                    'description': 'Widget B',
                    'quantity': 1,
                    'unit_price': 100.0
                }
            ]
        }
        payload.update(overrides)
        return self.client.post(
            '/api/invoices/',
            headers=self.auth_headers(),
            json=payload
        )

    def _register_second_user(self):
        """Register a second user and return (token, user_id)."""
        resp = self.client.post('/api/auth/register', json={
            'username': 'otheruser',
            'email': 'other@example.com',
            'password': 'otherpassword123',
            'company_name': 'Other Co'
        })
        data = resp.get_json()
        return data['access_token'], data['user']['id']

    def _auth_headers_for(self, token):
        """Return authorization headers for a given token."""
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

    # ------------------------------------------------------------------
    # 1. GET /api/invoices/ — get_invoices()
    # ------------------------------------------------------------------

    def test_get_invoices_empty(self):
        """Returns 200 with empty list when no invoices exist."""
        resp = self.client.get('/api/invoices/', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data['invoices'], [])

    def test_get_invoices_with_data(self):
        """Create 2+ invoices, verify they are returned ordered by created_at desc."""
        self._create_invoice(customer_name='First Customer')
        self._create_invoice(customer_name='Second Customer')

        resp = self.client.get('/api/invoices/', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        invoices = data['invoices']
        self.assertEqual(len(invoices), 2)
        # Most recently created should come first
        self.assertEqual(invoices[0]['customer_name'], 'Second Customer')
        self.assertEqual(invoices[1]['customer_name'], 'First Customer')

    def test_get_invoices_unauthorized(self):
        """Request without token returns 401."""
        resp = self.client.get('/api/invoices/')
        self.assertEqual(resp.status_code, 401)

    def test_get_invoices_only_own(self):
        """Each user only sees their own invoices."""
        # User A creates an invoice
        self._create_invoice(customer_name='User A Invoice')

        # Register user B and create an invoice
        token_b, _ = self._register_second_user()
        self.client.post('/api/invoices/', headers=self._auth_headers_for(token_b), json={
            'customer_name': 'User B Invoice',
            'due_date': '2026-12-31',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 10.0}]
        })

        # User A should only see their invoice
        resp_a = self.client.get('/api/invoices/', headers=self.auth_headers())
        invoices_a = resp_a.get_json()['invoices']
        self.assertEqual(len(invoices_a), 1)
        self.assertEqual(invoices_a[0]['customer_name'], 'User A Invoice')

        # User B should only see their invoice
        resp_b = self.client.get('/api/invoices/', headers=self._auth_headers_for(token_b))
        invoices_b = resp_b.get_json()['invoices']
        self.assertEqual(len(invoices_b), 1)
        self.assertEqual(invoices_b[0]['customer_name'], 'User B Invoice')

    # ------------------------------------------------------------------
    # 2. GET /api/invoices/<invoice_id> — get_invoice()
    # ------------------------------------------------------------------

    def test_get_invoice_success(self):
        """Create an invoice, fetch by ID, verify all fields match."""
        create_resp = self._create_invoice()
        self.assertEqual(create_resp.status_code, 201)
        created = create_resp.get_json()['invoice']

        resp = self.client.get(
            f"/api/invoices/{created['id']}",
            headers=self.auth_headers()
        )
        self.assertEqual(resp.status_code, 200)
        invoice = resp.get_json()['invoice']
        self.assertEqual(invoice['id'], created['id'])
        self.assertEqual(invoice['customer_name'], 'Jane Doe')
        self.assertEqual(invoice['customer_email'], 'jane@example.com')
        self.assertEqual(invoice['customer_address'], '123 Main St')
        self.assertEqual(invoice['due_date'], '2026-12-31')
        self.assertEqual(invoice['notes'], 'Test invoice')
        self.assertEqual(len(invoice['items']), 2)

    def test_get_invoice_not_found(self):
        """Request non-existent ID returns 404."""
        resp = self.client.get('/api/invoices/99999', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 404)

    def test_get_invoice_unauthorized(self):
        """Request without token returns 401."""
        resp = self.client.get('/api/invoices/1')
        self.assertEqual(resp.status_code, 401)

    def test_get_invoice_belongs_to_other_user(self):
        """User A creates invoice, user B tries to fetch it, gets 404."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        token_b, _ = self._register_second_user()
        resp = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self._auth_headers_for(token_b)
        )
        self.assertEqual(resp.status_code, 404)

    # ------------------------------------------------------------------
    # 3. POST /api/invoices/ — create_invoice()
    # ------------------------------------------------------------------

    def test_create_invoice_success(self):
        """Full valid payload. Verify 201, invoice_number generated, totals correct."""
        resp = self._create_invoice(
            customer_name='Acme Corp',
            customer_email='acme@example.com',
            customer_address='456 Oak Ave',
            due_date='2026-06-30',
            tax_rate=15.0,
            notes='Priority order',
            status='sent',
            items=[
                {'description': 'Service A', 'quantity': 3, 'unit_price': 100.0},
                {'description': 'Service B', 'quantity': 2, 'unit_price': 50.0}
            ]
        )
        self.assertEqual(resp.status_code, 201)
        data = resp.get_json()
        self.assertIn('message', data)
        invoice = data['invoice']

        # invoice_number generated
        self.assertTrue(invoice['invoice_number'].startswith('INV-'))

        # totals: subtotal = 3*100 + 2*50 = 400
        self.assertAlmostEqual(invoice['subtotal'], 400.0)
        # tax_amount = 400 * 15/100 = 60
        self.assertAlmostEqual(invoice['tax_amount'], 60.0)
        # total_amount = 400 + 60 = 460
        self.assertAlmostEqual(invoice['total_amount'], 460.0)

        self.assertEqual(invoice['customer_name'], 'Acme Corp')
        self.assertEqual(invoice['status'], 'sent')

    def test_create_invoice_missing_customer_name(self):
        """Omit customer_name, expect 400."""
        resp = self._create_invoice(customer_name='')
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_missing_due_date(self):
        """Omit due_date, expect 400."""
        resp = self._create_invoice(due_date='')
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_missing_items(self):
        """Omit items, expect 400."""
        resp = self.client.post('/api/invoices/', headers=self.auth_headers(), json={
            'customer_name': 'Test',
            'due_date': '2026-12-31'
        })
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_empty_items(self):
        """Items as empty list, expect 400."""
        resp = self._create_invoice(items=[])
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_item_missing_description(self):
        """Item without description, expect 400."""
        resp = self._create_invoice(items=[
            {'quantity': 1, 'unit_price': 10.0}
        ])
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_item_missing_quantity(self):
        """Item without quantity, expect 400."""
        resp = self._create_invoice(items=[
            {'description': 'Widget', 'unit_price': 10.0}
        ])
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_item_missing_unit_price(self):
        """Item without unit_price, expect 400."""
        resp = self._create_invoice(items=[
            {'description': 'Widget', 'quantity': 1}
        ])
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_default_status_is_draft(self):
        """Don't send status, verify it defaults to 'draft'."""
        resp = self._create_invoice()
        self.assertEqual(resp.status_code, 201)
        invoice = resp.get_json()['invoice']
        self.assertEqual(invoice['status'], 'draft')

    def test_create_invoice_with_tax_rate(self):
        """Send tax_rate, verify tax_amount and total_amount are correct."""
        resp = self._create_invoice(
            tax_rate=20.0,
            items=[
                {'description': 'Item', 'quantity': 5, 'unit_price': 40.0}
            ]
        )
        self.assertEqual(resp.status_code, 201)
        invoice = resp.get_json()['invoice']
        # subtotal = 5 * 40 = 200
        self.assertAlmostEqual(invoice['subtotal'], 200.0)
        # tax_amount = 200 * 20/100 = 40
        self.assertAlmostEqual(invoice['tax_amount'], 40.0)
        # total_amount = 200 + 40 = 240
        self.assertAlmostEqual(invoice['total_amount'], 240.0)

    def test_create_invoice_unauthorized(self):
        """Request without token returns 401."""
        resp = self.client.post('/api/invoices/', json={
            'customer_name': 'Test',
            'due_date': '2026-12-31',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 10.0}]
        })
        self.assertEqual(resp.status_code, 401)

    # ------------------------------------------------------------------
    # 4. PUT /api/invoices/<invoice_id> — update_invoice()
    # ------------------------------------------------------------------

    def test_update_invoice_success(self):
        """Update customer_name, status, notes — verify 200 and fields updated."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        resp = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers(),
            json={
                'customer_name': 'Updated Name',
                'status': 'sent',
                'notes': 'Updated notes'
            }
        )
        self.assertEqual(resp.status_code, 200)
        invoice = resp.get_json()['invoice']
        self.assertEqual(invoice['customer_name'], 'Updated Name')
        self.assertEqual(invoice['status'], 'sent')
        self.assertEqual(invoice['notes'], 'Updated notes')

    def test_update_invoice_items(self):
        """Update items array, verify old items removed, new items added, totals recalculated."""
        create_resp = self._create_invoice(
            tax_rate=10.0,
            items=[
                {'description': 'Old Item', 'quantity': 1, 'unit_price': 100.0}
            ]
        )
        invoice_id = create_resp.get_json()['invoice']['id']

        resp = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers(),
            json={
                'items': [
                    {'description': 'New Item 1', 'quantity': 3, 'unit_price': 20.0},
                    {'description': 'New Item 2', 'quantity': 2, 'unit_price': 30.0}
                ]
            }
        )
        self.assertEqual(resp.status_code, 200)
        invoice = resp.get_json()['invoice']
        self.assertEqual(len(invoice['items']), 2)
        descriptions = {item['description'] for item in invoice['items']}
        self.assertIn('New Item 1', descriptions)
        self.assertIn('New Item 2', descriptions)
        self.assertNotIn('Old Item', descriptions)
        # subtotal = 3*20 + 2*30 = 120, tax = 120*10/100 = 12, total = 132
        self.assertAlmostEqual(invoice['subtotal'], 120.0)
        self.assertAlmostEqual(invoice['tax_amount'], 12.0)
        self.assertAlmostEqual(invoice['total_amount'], 132.0)

    def test_update_invoice_not_found(self):
        """Update non-existent ID returns 404."""
        resp = self.client.put(
            '/api/invoices/99999',
            headers=self.auth_headers(),
            json={'customer_name': 'Ghost'}
        )
        self.assertEqual(resp.status_code, 404)

    def test_update_invoice_unauthorized(self):
        """Request without token returns 401."""
        resp = self.client.put('/api/invoices/1', json={'customer_name': 'Nope'})
        self.assertEqual(resp.status_code, 401)

    def test_update_invoice_belongs_to_other_user(self):
        """User A creates, user B tries to update, gets 404."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        token_b, _ = self._register_second_user()
        resp = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self._auth_headers_for(token_b),
            json={'customer_name': 'Hacked'}
        )
        self.assertEqual(resp.status_code, 404)

    def test_update_invoice_partial_fields(self):
        """Only update status, verify other fields unchanged."""
        create_resp = self._create_invoice(
            customer_name='Original Name',
            notes='Original notes'
        )
        created = create_resp.get_json()['invoice']
        invoice_id = created['id']

        resp = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers(),
            json={'status': 'paid'}
        )
        self.assertEqual(resp.status_code, 200)
        invoice = resp.get_json()['invoice']
        self.assertEqual(invoice['status'], 'paid')
        self.assertEqual(invoice['customer_name'], 'Original Name')
        self.assertEqual(invoice['notes'], 'Original notes')

    def test_update_invoice_due_date(self):
        """Update due_date, verify it parses correctly."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        resp = self.client.put(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers(),
            json={'due_date': '2027-03-15'}
        )
        self.assertEqual(resp.status_code, 200)
        invoice = resp.get_json()['invoice']
        self.assertEqual(invoice['due_date'], '2027-03-15')

    # ------------------------------------------------------------------
    # 5. DELETE /api/invoices/<invoice_id> — delete_invoice()
    # ------------------------------------------------------------------

    def test_delete_invoice_success(self):
        """Create then delete. Verify 200 and message. GET returns 404 after."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        resp = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers()
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn('message', resp.get_json())

        # Verify GET returns 404
        get_resp = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers()
        )
        self.assertEqual(get_resp.status_code, 404)

    def test_delete_invoice_not_found(self):
        """Delete non-existent ID returns 404."""
        resp = self.client.delete('/api/invoices/99999', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 404)

    def test_delete_invoice_unauthorized(self):
        """Request without token returns 401."""
        resp = self.client.delete('/api/invoices/1')
        self.assertEqual(resp.status_code, 401)

    def test_delete_invoice_belongs_to_other_user(self):
        """User A creates, user B tries to delete, gets 404."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        token_b, _ = self._register_second_user()
        resp = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self._auth_headers_for(token_b)
        )
        self.assertEqual(resp.status_code, 404)

    def test_delete_invoice_cascades_items(self):
        """After deleting invoice, verify its InvoiceItems are also deleted."""
        create_resp = self._create_invoice()
        invoice_id = create_resp.get_json()['invoice']['id']

        # Confirm items exist before deletion
        items_before = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertTrue(len(items_before) > 0)

        # Delete the invoice
        self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers()
        )

        # Verify items are gone
        items_after = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertEqual(len(items_after), 0)


def run_invoice_tests():
    """Run all invoice tests and return results."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestInvoiceEndpoints)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_invoice_tests()
    if success:
        print("\nAll invoice tests passed!")
        sys.exit(0)
    else:
        print("\nSome invoice tests failed!")
        sys.exit(1)
