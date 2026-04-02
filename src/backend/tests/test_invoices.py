#!/usr/bin/env python3
"""
Invoice Endpoint Tests

Comprehensive test suite for all 5 invoice endpoints:
- POST /api/invoices (create)
- GET /api/invoices (list)
- GET /api/invoices/<id> (detail)
- PUT /api/invoices/<id> (update)
- DELETE /api/invoices/<id> (delete)
"""

import sys
import os
import unittest
import json

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set DATABASE_URL before importing app so create_app() uses in-memory SQLite
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from app import create_app
from models import db


class TestInvoiceEndpoints(unittest.TestCase):
    """Test cases for all invoice CRUD endpoints."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        self.app = create_app()
        self.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app.config['TESTING'] = True
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

        # Register a test user and store the access token
        resp = self.client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@test.com',
            'password': 'password123'
        })
        data = json.loads(resp.data)
        self.token = data['access_token']

    def tearDown(self):
        """Clean up after each test method."""
        db.drop_all()
        self.app_context.pop()

    # ------------------------------------------------------------------ helpers

    def auth_headers(self):
        """Return Authorization and Content-Type headers."""
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

    def create_test_invoice(self, overrides=None):
        """POST a valid invoice payload and return the response."""
        payload = {
            'customer_name': 'Test Customer',
            'customer_email': 'customer@test.com',
            'customer_address': '123 Test St',
            'due_date': '2025-12-31',
            'tax_rate': 10.0,
            'notes': 'Test notes',
            'status': 'draft',
            'items': [
                {'description': 'Service A', 'quantity': 2, 'unit_price': 50.00},
                {'description': 'Service B', 'quantity': 1, 'unit_price': 100.00}
            ]
        }
        if overrides:
            payload.update(overrides)
        return self.client.post(
            '/api/invoices/',
            headers=self.auth_headers(),
            json=payload
        )

    def _register_second_user(self):
        """Register a second user and return (client, token)."""
        resp = self.client.post('/api/auth/register', json={
            'username': 'otheruser',
            'email': 'other@test.com',
            'password': 'password456'
        })
        data = json.loads(resp.data)
        return data['access_token']

    # ======================================================================
    # POST /api/invoices  (create_invoice)
    # ======================================================================

    def test_create_invoice_success(self):
        """1. POST valid payload -> 201, correct fields."""
        resp = self.create_test_invoice()
        self.assertEqual(resp.status_code, 201)
        data = json.loads(resp.data)
        self.assertIn('message', data)
        self.assertIn('invoice', data)
        inv = data['invoice']
        self.assertEqual(inv['customer_name'], 'Test Customer')
        self.assertEqual(inv['status'], 'draft')
        self.assertTrue(inv['invoice_number'].startswith('INV-'))
        # 2*50 + 1*100 = 200 subtotal, 10% tax = 20, total = 220
        self.assertAlmostEqual(inv['total_amount'], 220.0)
        self.assertEqual(len(inv['items']), 2)

    def test_create_invoice_missing_customer_name(self):
        """2. Omit customer_name -> 400."""
        resp = self.create_test_invoice(overrides={'customer_name': ''})
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertIn('error', data)

    def test_create_invoice_missing_due_date(self):
        """3. Omit due_date -> 400."""
        resp = self.create_test_invoice(overrides={'due_date': ''})
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_missing_items(self):
        """4. Omit items -> 400."""
        payload = {
            'customer_name': 'Test Customer',
            'due_date': '2025-12-31'
        }
        resp = self.client.post('/api/invoices/', headers=self.auth_headers(), json=payload)
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_empty_items(self):
        """5. Send items: [] -> 400 (items is falsy)."""
        resp = self.create_test_invoice(overrides={'items': []})
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_item_missing_description(self):
        """6. Item without description -> 400."""
        resp = self.create_test_invoice(overrides={
            'items': [{'quantity': 1, 'unit_price': 10.0}]
        })
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.data)
        self.assertIn('Each item must have description, quantity, and unit_price', data['error'])

    def test_create_invoice_item_missing_quantity(self):
        """7. Item without quantity -> 400."""
        resp = self.create_test_invoice(overrides={
            'items': [{'description': 'X', 'unit_price': 10.0}]
        })
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_item_missing_unit_price(self):
        """8. Item without unit_price -> 400."""
        resp = self.create_test_invoice(overrides={
            'items': [{'description': 'X', 'quantity': 1}]
        })
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_without_auth(self):
        """9. POST without Authorization header -> 401."""
        resp = self.client.post('/api/invoices/', json={
            'customer_name': 'Test',
            'due_date': '2025-12-31',
            'items': [{'description': 'A', 'quantity': 1, 'unit_price': 10}]
        })
        self.assertEqual(resp.status_code, 401)

    def test_create_invoice_with_optional_fields(self):
        """10. All optional fields stored correctly."""
        resp = self.create_test_invoice()
        self.assertEqual(resp.status_code, 201)
        inv = json.loads(resp.data)['invoice']
        self.assertEqual(inv['customer_email'], 'customer@test.com')
        self.assertEqual(inv['customer_address'], '123 Test St')
        self.assertAlmostEqual(inv['tax_rate'], 10.0)
        self.assertEqual(inv['notes'], 'Test notes')
        self.assertEqual(inv['status'], 'draft')

    def test_create_invoice_default_status(self):
        """11. POST without status -> defaults to 'draft'."""
        payload = {
            'customer_name': 'No Status',
            'due_date': '2025-12-31',
            'items': [{'description': 'S', 'quantity': 1, 'unit_price': 10}]
        }
        resp = self.client.post('/api/invoices/', headers=self.auth_headers(), json=payload)
        self.assertEqual(resp.status_code, 201)
        inv = json.loads(resp.data)['invoice']
        self.assertEqual(inv['status'], 'draft')

    # ======================================================================
    # GET /api/invoices  (get_invoices)
    # ======================================================================

    def test_get_invoices_empty(self):
        """12. No invoices -> 200, empty list."""
        resp = self.client.get('/api/invoices/', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data['invoices'], [])

    def test_get_invoices_returns_all(self):
        """13. Create 3 invoices -> GET returns 3."""
        for i in range(3):
            self.create_test_invoice(overrides={'customer_name': f'Customer {i}'})
        resp = self.client.get('/api/invoices/', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data['invoices']), 3)

    def test_get_invoices_ordered_by_created_at_desc(self):
        """14. Invoices returned in reverse chronological order."""
        for i in range(3):
            self.create_test_invoice(overrides={'customer_name': f'Customer {i}'})
        resp = self.client.get('/api/invoices/', headers=self.auth_headers())
        invoices = json.loads(resp.data)['invoices']
        created_dates = [inv['created_at'] for inv in invoices]
        self.assertEqual(created_dates, sorted(created_dates, reverse=True))

    def test_get_invoices_without_auth(self):
        """15. GET without token -> 401."""
        resp = self.client.get('/api/invoices/')
        self.assertEqual(resp.status_code, 401)

    def test_get_invoices_user_isolation(self):
        """16. Each user sees only their own invoices."""
        # User 1 creates 2 invoices
        self.create_test_invoice(overrides={'customer_name': 'U1-A'})
        self.create_test_invoice(overrides={'customer_name': 'U1-B'})

        # Register second user
        token2 = self._register_second_user()
        headers2 = {
            'Authorization': f'Bearer {token2}',
            'Content-Type': 'application/json'
        }

        # User 2 creates 1 invoice
        self.client.post('/api/invoices/', headers=headers2, json={
            'customer_name': 'U2-A',
            'due_date': '2025-12-31',
            'items': [{'description': 'X', 'quantity': 1, 'unit_price': 10}]
        })

        # User 1 should see 2
        resp1 = self.client.get('/api/invoices/', headers=self.auth_headers())
        self.assertEqual(len(json.loads(resp1.data)['invoices']), 2)

        # User 2 should see 1
        resp2 = self.client.get('/api/invoices/', headers=headers2)
        self.assertEqual(len(json.loads(resp2.data)['invoices']), 1)

    # ======================================================================
    # GET /api/invoices/<id>  (get_invoice)
    # ======================================================================

    def test_get_invoice_by_id_success(self):
        """17. GET by ID -> 200 with correct data and items."""
        create_resp = self.create_test_invoice()
        inv_id = json.loads(create_resp.data)['invoice']['id']
        resp = self.client.get(f'/api/invoices/{inv_id}', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('invoice', data)
        self.assertEqual(data['invoice']['id'], inv_id)
        self.assertEqual(len(data['invoice']['items']), 2)

    def test_get_invoice_not_found(self):
        """18. GET non-existent ID -> 404."""
        resp = self.client.get('/api/invoices/99999', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 404)

    def test_get_invoice_belongs_to_other_user(self):
        """19. GET another user's invoice -> 404."""
        create_resp = self.create_test_invoice()
        inv_id = json.loads(create_resp.data)['invoice']['id']

        token2 = self._register_second_user()
        headers2 = {
            'Authorization': f'Bearer {token2}',
            'Content-Type': 'application/json'
        }
        resp = self.client.get(f'/api/invoices/{inv_id}', headers=headers2)
        self.assertEqual(resp.status_code, 404)

    def test_get_invoice_without_auth(self):
        """20. GET without auth -> 401."""
        resp = self.client.get('/api/invoices/1')
        self.assertEqual(resp.status_code, 401)

    # ======================================================================
    # PUT /api/invoices/<id>  (update_invoice)
    # ======================================================================

    def test_update_invoice_customer_name(self):
        """21. Update customer_name -> 200, change persisted."""
        create_resp = self.create_test_invoice()
        inv_id = json.loads(create_resp.data)['invoice']['id']
        resp = self.client.put(
            f'/api/invoices/{inv_id}',
            headers=self.auth_headers(),
            json={'customer_name': 'Updated Customer'}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data)['invoice']['customer_name'], 'Updated Customer')

    def test_update_invoice_status(self):
        """22. Update status to 'paid'."""
        create_resp = self.create_test_invoice()
        inv_id = json.loads(create_resp.data)['invoice']['id']
        resp = self.client.put(
            f'/api/invoices/{inv_id}',
            headers=self.auth_headers(),
            json={'status': 'paid'}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(json.loads(resp.data)['invoice']['status'], 'paid')

    def test_update_invoice_multiple_fields(self):
        """23. Update customer_email, notes, due_date simultaneously."""
        create_resp = self.create_test_invoice()
        inv_id = json.loads(create_resp.data)['invoice']['id']
        resp = self.client.put(
            f'/api/invoices/{inv_id}',
            headers=self.auth_headers(),
            json={
                'customer_email': 'new@email.com',
                'notes': 'Updated notes',
                'due_date': '2026-06-15'
            }
        )
        self.assertEqual(resp.status_code, 200)
        inv = json.loads(resp.data)['invoice']
        self.assertEqual(inv['customer_email'], 'new@email.com')
        self.assertEqual(inv['notes'], 'Updated notes')
        self.assertEqual(inv['due_date'], '2026-06-15')

    def test_update_invoice_items(self):
        """24. Update with new items array -> old items replaced, totals recalculated."""
        create_resp = self.create_test_invoice()
        inv_id = json.loads(create_resp.data)['invoice']['id']
        resp = self.client.put(
            f'/api/invoices/{inv_id}',
            headers=self.auth_headers(),
            json={
                'items': [
                    {'description': 'New Service', 'quantity': 3, 'unit_price': 100.00}
                ]
            }
        )
        self.assertEqual(resp.status_code, 200)
        inv = json.loads(resp.data)['invoice']
        self.assertEqual(len(inv['items']), 1)
        # subtotal = 3*100 = 300, tax 10% = 30, total = 330
        self.assertAlmostEqual(inv['total_amount'], 330.0)

    def test_update_invoice_not_found(self):
        """25. PUT to non-existent ID -> 404."""
        resp = self.client.put(
            '/api/invoices/99999',
            headers=self.auth_headers(),
            json={'customer_name': 'X'}
        )
        self.assertEqual(resp.status_code, 404)

    def test_update_invoice_other_user(self):
        """26. Update another user's invoice -> 404."""
        create_resp = self.create_test_invoice()
        inv_id = json.loads(create_resp.data)['invoice']['id']
        token2 = self._register_second_user()
        headers2 = {
            'Authorization': f'Bearer {token2}',
            'Content-Type': 'application/json'
        }
        resp = self.client.put(
            f'/api/invoices/{inv_id}',
            headers=headers2,
            json={'customer_name': 'Hacked'}
        )
        self.assertEqual(resp.status_code, 404)

    def test_update_invoice_without_auth(self):
        """27. PUT without auth -> 401."""
        resp = self.client.put('/api/invoices/1', json={'customer_name': 'X'})
        self.assertEqual(resp.status_code, 401)

    def test_update_invoice_tax_rate_recalculates(self):
        """28. Update tax_rate -> tax_amount and total_amount recalculated."""
        create_resp = self.create_test_invoice()
        inv_id = json.loads(create_resp.data)['invoice']['id']
        # Change tax_rate from 10% to 20%
        resp = self.client.put(
            f'/api/invoices/{inv_id}',
            headers=self.auth_headers(),
            json={'tax_rate': 20.0}
        )
        self.assertEqual(resp.status_code, 200)
        inv = json.loads(resp.data)['invoice']
        # subtotal = 200, tax 20% = 40, total = 240
        self.assertAlmostEqual(inv['tax_amount'], 40.0)
        self.assertAlmostEqual(inv['total_amount'], 240.0)

    # ======================================================================
    # DELETE /api/invoices/<id>  (delete_invoice)
    # ======================================================================

    def test_delete_invoice_success(self):
        """29. DELETE invoice -> 200, then GET -> 404."""
        create_resp = self.create_test_invoice()
        inv_id = json.loads(create_resp.data)['invoice']['id']
        resp = self.client.delete(f'/api/invoices/{inv_id}', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn('message', data)

        # Verify it's gone
        get_resp = self.client.get(f'/api/invoices/{inv_id}', headers=self.auth_headers())
        self.assertEqual(get_resp.status_code, 404)

    def test_delete_invoice_not_found(self):
        """30. DELETE non-existent ID -> 404."""
        resp = self.client.delete('/api/invoices/99999', headers=self.auth_headers())
        self.assertEqual(resp.status_code, 404)

    def test_delete_invoice_other_user(self):
        """31. Delete another user's invoice -> 404."""
        create_resp = self.create_test_invoice()
        inv_id = json.loads(create_resp.data)['invoice']['id']
        token2 = self._register_second_user()
        headers2 = {
            'Authorization': f'Bearer {token2}',
            'Content-Type': 'application/json'
        }
        resp = self.client.delete(f'/api/invoices/{inv_id}', headers=headers2)
        self.assertEqual(resp.status_code, 404)

    def test_delete_invoice_without_auth(self):
        """32. DELETE without auth -> 401."""
        resp = self.client.delete('/api/invoices/1')
        self.assertEqual(resp.status_code, 401)


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
