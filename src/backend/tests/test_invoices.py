#!/usr/bin/env python3
"""
Invoice Endpoints Tests

Comprehensive test coverage for all 5 invoice endpoints:
  GET    /api/invoices/
  GET    /api/invoices/<invoice_id>
  POST   /api/invoices/
  PUT    /api/invoices/<invoice_id>
  DELETE /api/invoices/<invoice_id>
"""

import sys
import os
import unittest
import json

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from models import db, Invoice, InvoiceItem, User


class TestInvoiceEndpoints(unittest.TestCase):
    """Test cases for invoice CRUD endpoints."""

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

        # Register a test user and store the JWT token
        resp = self.client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'testuser@example.com',
            'password': 'password123',
            'company_name': 'Test Co'
        })
        data = json.loads(resp.data)
        self.token = data['access_token']

    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def auth_headers(self, token=None):
        """Return authorization headers with the given or default token."""
        return {
            'Authorization': f'Bearer {token or self.token}',
            'Content-Type': 'application/json'
        }

    def _create_invoice(self, **overrides):
        """POST a valid invoice payload and return the response.

        Any key in *overrides* replaces the corresponding default value.
        """
        payload = {
            'customer_name': 'John Doe',
            'customer_email': 'john@example.com',
            'customer_address': '123 Main St',
            'due_date': '2026-12-31',
            'tax_rate': 10.0,
            'notes': 'Test invoice',
            'status': 'draft',
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
            json=payload,
            headers=self.auth_headers()
        )

    def _register_second_user(self):
        """Register a second user and return the JWT token."""
        resp = self.client.post('/api/auth/register', json={
            'username': 'otheruser',
            'email': 'other@example.com',
            'password': 'password456',
            'company_name': 'Other Co'
        })
        data = json.loads(resp.data)
        return data['access_token']

    # ==================================================================
    # 1. GET /api/invoices/  —  get_invoices()
    # ==================================================================

    def test_get_invoices_empty(self):
        """Returns 200 with empty list when no invoices exist."""
        resp = self.client.get('/api/invoices/', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['invoices'], [])

    def test_get_invoices_with_data(self):
        """Returns invoices ordered by created_at desc when invoices exist."""
        self._create_invoice(customer_name='First Customer')
        self._create_invoice(customer_name='Second Customer')

        resp = self.client.get('/api/invoices/', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data['invoices']), 2)
        # Most recent first
        self.assertEqual(data['invoices'][0]['customer_name'], 'Second Customer')
        self.assertEqual(data['invoices'][1]['customer_name'], 'First Customer')

    def test_get_invoices_unauthorized(self):
        """Request without token returns 401."""
        resp = self.client.get('/api/invoices/')
        self.assertEqual(resp.status_code, 401)

    def test_get_invoices_only_own(self):
        """Each user only sees their own invoices."""
        # User 1 creates an invoice
        self._create_invoice(customer_name='User1 Invoice')

        # User 2 creates an invoice
        token2 = self._register_second_user()
        self.client.post('/api/invoices/', json={
            'customer_name': 'User2 Invoice',
            'due_date': '2026-12-31',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 10}]
        }, headers=self.auth_headers(token2))

        # User 1 should only see their own
        resp = self.client.get('/api/invoices/', headers=self.auth_headers())
        data = json.loads(resp.data)
        self.assertEqual(len(data['invoices']), 1)
        self.assertEqual(data['invoices'][0]['customer_name'], 'User1 Invoice')

        # User 2 should only see their own
        resp = self.client.get('/api/invoices/', headers=self.auth_headers(token2))
        data = json.loads(resp.data)
        self.assertEqual(len(data['invoices']), 1)
        self.assertEqual(data['invoices'][0]['customer_name'], 'User2 Invoice')

    # ==================================================================
    # 2. GET /api/invoices/<invoice_id>  —  get_invoice()
    # ==================================================================

    def test_get_invoice_success(self):
        """Fetch a single invoice by ID and verify all fields."""
        create_resp = self._create_invoice()
        self.assertEqual(create_resp.status_code, 201)
        created = json.loads(create_resp.data)['invoice']

        resp = self.client.get(
            f"/api/invoices/{created['id']}",
            headers=self.auth_headers()
        )
        self.assertEqual(resp.status_code, 200)
        invoice = json.loads(resp.data)['invoice']
        self.assertEqual(invoice['id'], created['id'])
        self.assertEqual(invoice['customer_name'], 'John Doe')
        self.assertEqual(invoice['customer_email'], 'john@example.com')
        self.assertEqual(invoice['customer_address'], '123 Main St')
        self.assertEqual(invoice['due_date'], '2026-12-31')
        self.assertEqual(invoice['status'], 'draft')
        self.assertIsNotNone(invoice['invoice_number'])
        self.assertEqual(len(invoice['items']), 2)

    def test_get_invoice_not_found(self):
        """Non-existent ID returns 404."""
        resp = self.client.get('/api/invoices/99999', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 404)

    def test_get_invoice_unauthorized(self):
        """Request without token returns 401."""
        resp = self.client.get('/api/invoices/1')
        self.assertEqual(resp.status_code, 401)

    def test_get_invoice_belongs_to_other_user(self):
        """User B cannot fetch User A's invoice (gets 404)."""
        create_resp = self._create_invoice()
        invoice_id = json.loads(create_resp.data)['invoice']['id']

        token2 = self._register_second_user()
        resp = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers(token2)
        )
        self.assertEqual(resp.status_code, 404)

    # ==================================================================
    # 3. POST /api/invoices/  —  create_invoice()
    # ==================================================================

    def test_create_invoice_success(self):
        """Full valid payload returns 201 with correct totals."""
        resp = self._create_invoice()
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        invoice = data['invoice']

        # invoice_number generated
        self.assertTrue(invoice['invoice_number'].startswith('INV-'))

        # subtotal = (2*50) + (1*100) = 200
        self.assertAlmostEqual(invoice['subtotal'], 200.0)
        # tax_amount = 200 * 10/100 = 20
        self.assertAlmostEqual(invoice['tax_amount'], 20.0)
        # total_amount = 200 + 20 = 220
        self.assertAlmostEqual(invoice['total_amount'], 220.0)

        self.assertEqual(invoice['customer_name'], 'John Doe')
        self.assertEqual(invoice['notes'], 'Test invoice')
        self.assertEqual(len(invoice['items']), 2)

    def test_create_invoice_missing_customer_name(self):
        """Omitting customer_name returns 400."""
        resp = self._create_invoice(customer_name='')
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_missing_due_date(self):
        """Omitting due_date returns 400."""
        resp = self._create_invoice(due_date='')
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_missing_items(self):
        """Omitting items returns 400."""
        resp = self.client.post('/api/invoices/', json={
            'customer_name': 'John',
            'due_date': '2026-12-31'
        }, headers=self.auth_headers())
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_empty_items(self):
        """Empty items list returns 400."""
        resp = self._create_invoice(items=[])
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_item_missing_description(self):
        """Item without description returns 400."""
        resp = self._create_invoice(items=[
            {'quantity': 1, 'unit_price': 10.0}
        ])
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_item_missing_quantity(self):
        """Item without quantity returns 400."""
        resp = self._create_invoice(items=[
            {'description': 'Widget', 'unit_price': 10.0}
        ])
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_item_missing_unit_price(self):
        """Item without unit_price returns 400."""
        resp = self._create_invoice(items=[
            {'description': 'Widget', 'quantity': 1}
        ])
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_default_status_is_draft(self):
        """When status is not sent, it defaults to 'draft'."""
        payload = {
            'customer_name': 'Jane',
            'due_date': '2026-12-31',
            'items': [{'description': 'X', 'quantity': 1, 'unit_price': 5}]
        }
        resp = self.client.post('/api/invoices/', json=payload,
                                headers=self.auth_headers())
        self.assertEqual(resp.status_code, 201)
        invoice = json.loads(resp.data)['invoice']
        self.assertEqual(invoice['status'], 'draft')

    def test_create_invoice_with_tax_rate(self):
        """Tax amount and total are correctly calculated from tax_rate."""
        resp = self._create_invoice(
            tax_rate=15.0,
            items=[{'description': 'A', 'quantity': 4, 'unit_price': 25.0}]
        )
        self.assertEqual(resp.status_code, 201)
        invoice = json.loads(resp.data)['invoice']
        # subtotal = 4*25 = 100
        self.assertAlmostEqual(invoice['subtotal'], 100.0)
        # tax = 100 * 15/100 = 15
        self.assertAlmostEqual(invoice['tax_amount'], 15.0)
        # total = 100 + 15 = 115
        self.assertAlmostEqual(invoice['total_amount'], 115.0)

    def test_create_invoice_unauthorized(self):
        """Request without token returns 401."""
        resp = self.client.post('/api/invoices/', json={
            'customer_name': 'X',
            'due_date': '2026-12-31',
            'items': [{'description': 'Y', 'quantity': 1, 'unit_price': 1}]
        })
        self.assertEqual(resp.status_code, 401)

    # ==================================================================
    # 4. PUT /api/invoices/<invoice_id>  —  update_invoice()
    # ==================================================================

    def test_update_invoice_success(self):
        """Update customer_name, status, and notes — verify 200 and updates."""
        inv = json.loads(self._create_invoice().data)['invoice']

        resp = self.client.put(
            f"/api/invoices/{inv['id']}",
            json={
                'customer_name': 'Updated Name',
                'status': 'sent',
                'notes': 'Updated notes'
            },
            headers=self.auth_headers()
        )
        self.assertEqual(resp.status_code, 200)
        updated = json.loads(resp.data)['invoice']
        self.assertEqual(updated['customer_name'], 'Updated Name')
        self.assertEqual(updated['status'], 'sent')
        self.assertEqual(updated['notes'], 'Updated notes')

    def test_update_invoice_items(self):
        """Updating items replaces old items and recalculates totals."""
        inv = json.loads(self._create_invoice().data)['invoice']

        new_items = [
            {'description': 'New Item', 'quantity': 3, 'unit_price': 30.0}
        ]
        resp = self.client.put(
            f"/api/invoices/{inv['id']}",
            json={'items': new_items},
            headers=self.auth_headers()
        )
        self.assertEqual(resp.status_code, 200)
        updated = json.loads(resp.data)['invoice']
        self.assertEqual(len(updated['items']), 1)
        self.assertEqual(updated['items'][0]['description'], 'New Item')
        # subtotal = 3*30 = 90, tax_rate still 10 => tax = 9, total = 99
        self.assertAlmostEqual(updated['subtotal'], 90.0)
        self.assertAlmostEqual(updated['tax_amount'], 9.0)
        self.assertAlmostEqual(updated['total_amount'], 99.0)

    def test_update_invoice_not_found(self):
        """Updating non-existent ID returns 404."""
        resp = self.client.put(
            '/api/invoices/99999',
            json={'status': 'paid'},
            headers=self.auth_headers()
        )
        self.assertEqual(resp.status_code, 404)

    def test_update_invoice_unauthorized(self):
        """Request without token returns 401."""
        resp = self.client.put('/api/invoices/1', json={'status': 'paid'})
        self.assertEqual(resp.status_code, 401)

    def test_update_invoice_belongs_to_other_user(self):
        """User B cannot update User A's invoice (gets 404)."""
        inv = json.loads(self._create_invoice().data)['invoice']
        token2 = self._register_second_user()

        resp = self.client.put(
            f"/api/invoices/{inv['id']}",
            json={'status': 'paid'},
            headers=self.auth_headers(token2)
        )
        self.assertEqual(resp.status_code, 404)

    def test_update_invoice_partial_fields(self):
        """Updating only status leaves other fields unchanged."""
        inv = json.loads(self._create_invoice().data)['invoice']

        resp = self.client.put(
            f"/api/invoices/{inv['id']}",
            json={'status': 'paid'},
            headers=self.auth_headers()
        )
        self.assertEqual(resp.status_code, 200)
        updated = json.loads(resp.data)['invoice']
        self.assertEqual(updated['status'], 'paid')
        # Other fields unchanged
        self.assertEqual(updated['customer_name'], inv['customer_name'])
        self.assertEqual(updated['notes'], inv['notes'])
        self.assertAlmostEqual(updated['subtotal'], inv['subtotal'])

    def test_update_invoice_due_date(self):
        """Updating due_date parses correctly."""
        inv = json.loads(self._create_invoice().data)['invoice']

        resp = self.client.put(
            f"/api/invoices/{inv['id']}",
            json={'due_date': '2027-06-15'},
            headers=self.auth_headers()
        )
        self.assertEqual(resp.status_code, 200)
        updated = json.loads(resp.data)['invoice']
        self.assertEqual(updated['due_date'], '2027-06-15')

    # ==================================================================
    # 5. DELETE /api/invoices/<invoice_id>  —  delete_invoice()
    # ==================================================================

    def test_delete_invoice_success(self):
        """Delete an invoice and verify GET returns 404 after deletion."""
        inv = json.loads(self._create_invoice().data)['invoice']

        resp = self.client.delete(
            f"/api/invoices/{inv['id']}",
            headers=self.auth_headers()
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('message', data)

        # Confirm it's gone
        get_resp = self.client.get(
            f"/api/invoices/{inv['id']}",
            headers=self.auth_headers()
        )
        self.assertEqual(get_resp.status_code, 404)

    def test_delete_invoice_not_found(self):
        """Deleting non-existent ID returns 404."""
        resp = self.client.delete(
            '/api/invoices/99999',
            headers=self.auth_headers()
        )
        self.assertEqual(resp.status_code, 404)

    def test_delete_invoice_unauthorized(self):
        """Request without token returns 401."""
        resp = self.client.delete('/api/invoices/1')
        self.assertEqual(resp.status_code, 401)

    def test_delete_invoice_belongs_to_other_user(self):
        """User B cannot delete User A's invoice (gets 404)."""
        inv = json.loads(self._create_invoice().data)['invoice']
        token2 = self._register_second_user()

        resp = self.client.delete(
            f"/api/invoices/{inv['id']}",
            headers=self.auth_headers(token2)
        )
        self.assertEqual(resp.status_code, 404)

    def test_delete_invoice_cascades_items(self):
        """Deleting an invoice also deletes its InvoiceItems (cascade)."""
        inv = json.loads(self._create_invoice().data)['invoice']
        invoice_id = inv['id']

        # Verify items exist before deletion
        items_before = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertGreater(len(items_before), 0)

        self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self.auth_headers()
        )

        # Verify items are gone after deletion
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
