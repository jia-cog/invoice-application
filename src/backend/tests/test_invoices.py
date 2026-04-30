#!/usr/bin/env python3
"""
Invoice endpoint tests.

Tests for POST, GET, PUT, DELETE on /api/invoices/.
"""

import sys
import os
import unittest

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from base import BaseTestCase


class TestInvoiceEndpoints(BaseTestCase):
    """Test cases for invoice CRUD endpoints."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _register_and_get_token(self, username='alice', email='alice@example.com'):
        resp = self.register_user(username, email, 'password123')
        return resp.get_json()['access_token']

    def create_sample_invoice(self, token):
        """POST a valid invoice and return the response."""
        return self.client.post('/api/invoices/', json={
            'customer_name': 'Acme Corp',
            'due_date': '2025-12-31',
            'items': [
                {'description': 'Widget', 'quantity': 2, 'unit_price': 50.0},
            ],
        }, headers=self.get_auth_header(token))

    # ------------------------------------------------------------------
    # POST /api/invoices/
    # ------------------------------------------------------------------

    def test_create_invoice_success(self):
        token = self._register_and_get_token()
        resp = self.create_sample_invoice(token)
        data = resp.get_json()
        self.assertEqual(resp.status_code, 201)
        inv = data['invoice']
        self.assertIn('invoice_number', inv)
        self.assertEqual(inv['customer_name'], 'Acme Corp')
        self.assertTrue(len(inv['items']) >= 1)
        self.assertAlmostEqual(inv['total_amount'], 100.0)

    def test_create_invoice_missing_customer_name(self):
        token = self._register_and_get_token()
        resp = self.client.post('/api/invoices/', json={
            'due_date': '2025-12-31',
            'items': [{'description': 'W', 'quantity': 1, 'unit_price': 10}],
        }, headers=self.get_auth_header(token))
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_missing_due_date(self):
        token = self._register_and_get_token()
        resp = self.client.post('/api/invoices/', json={
            'customer_name': 'Acme',
            'items': [{'description': 'W', 'quantity': 1, 'unit_price': 10}],
        }, headers=self.get_auth_header(token))
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_missing_items(self):
        token = self._register_and_get_token()
        resp = self.client.post('/api/invoices/', json={
            'customer_name': 'Acme',
            'due_date': '2025-12-31',
        }, headers=self.get_auth_header(token))
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_invalid_item(self):
        token = self._register_and_get_token()
        resp = self.client.post('/api/invoices/', json={
            'customer_name': 'Acme',
            'due_date': '2025-12-31',
            'items': [{'quantity': 1, 'unit_price': 10}],  # missing description
        }, headers=self.get_auth_header(token))
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_no_token(self):
        resp = self.client.post('/api/invoices/', json={
            'customer_name': 'Acme',
            'due_date': '2025-12-31',
            'items': [{'description': 'W', 'quantity': 1, 'unit_price': 10}],
        })
        self.assertEqual(resp.status_code, 401)

    def test_create_invoice_with_tax(self):
        token = self._register_and_get_token()
        resp = self.client.post('/api/invoices/', json={
            'customer_name': 'Acme',
            'due_date': '2025-12-31',
            'tax_rate': 10,
            'items': [
                {'description': 'Widget', 'quantity': 2, 'unit_price': 50.0},
            ],
        }, headers=self.get_auth_header(token))
        data = resp.get_json()
        self.assertEqual(resp.status_code, 201)
        inv = data['invoice']
        # subtotal = 100, tax = 10%, tax_amount = 10, total = 110
        self.assertAlmostEqual(inv['tax_amount'], 10.0)
        self.assertAlmostEqual(inv['total_amount'], 110.0)

    # ------------------------------------------------------------------
    # GET /api/invoices/
    # ------------------------------------------------------------------

    def test_get_invoices_empty(self):
        token = self._register_and_get_token()
        resp = self.client.get('/api/invoices/',
                               headers=self.get_auth_header(token))
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['invoices'], [])

    def test_get_invoices_success(self):
        token = self._register_and_get_token()
        self.create_sample_invoice(token)
        self.create_sample_invoice(token)
        resp = self.client.get('/api/invoices/',
                               headers=self.get_auth_header(token))
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(data['invoices']), 2)

    def test_get_invoices_no_token(self):
        resp = self.client.get('/api/invoices/')
        self.assertEqual(resp.status_code, 401)

    def test_get_invoices_isolation(self):
        token_a = self._register_and_get_token('alice', 'alice@example.com')
        token_b = self._register_and_get_token('bob', 'bob@example.com')
        self.create_sample_invoice(token_a)
        self.create_sample_invoice(token_b)

        resp_a = self.client.get('/api/invoices/',
                                 headers=self.get_auth_header(token_a))
        resp_b = self.client.get('/api/invoices/',
                                 headers=self.get_auth_header(token_b))
        self.assertEqual(len(resp_a.get_json()['invoices']), 1)
        self.assertEqual(len(resp_b.get_json()['invoices']), 1)

    # ------------------------------------------------------------------
    # GET /api/invoices/<id>
    # ------------------------------------------------------------------

    def test_get_invoice_by_id_success(self):
        token = self._register_and_get_token()
        inv_id = self.create_sample_invoice(token).get_json()['invoice']['id']
        resp = self.client.get(f'/api/invoices/{inv_id}',
                               headers=self.get_auth_header(token))
        self.assertEqual(resp.status_code, 200)

    def test_get_invoice_not_found(self):
        token = self._register_and_get_token()
        resp = self.client.get('/api/invoices/9999',
                               headers=self.get_auth_header(token))
        self.assertEqual(resp.status_code, 404)

    def test_get_invoice_other_user(self):
        token_a = self._register_and_get_token('alice', 'alice@example.com')
        token_b = self._register_and_get_token('bob', 'bob@example.com')
        inv_id = self.create_sample_invoice(token_a).get_json()['invoice']['id']
        resp = self.client.get(f'/api/invoices/{inv_id}',
                               headers=self.get_auth_header(token_b))
        self.assertEqual(resp.status_code, 404)

    # ------------------------------------------------------------------
    # PUT /api/invoices/<id>
    # ------------------------------------------------------------------

    def test_update_invoice_success(self):
        token = self._register_and_get_token()
        inv_id = self.create_sample_invoice(token).get_json()['invoice']['id']
        resp = self.client.put(f'/api/invoices/{inv_id}', json={
            'customer_name': 'New Corp',
        }, headers=self.get_auth_header(token))
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['invoice']['customer_name'], 'New Corp')

    def test_update_invoice_items(self):
        token = self._register_and_get_token()
        inv_id = self.create_sample_invoice(token).get_json()['invoice']['id']
        resp = self.client.put(f'/api/invoices/{inv_id}', json={
            'items': [
                {'description': 'Gadget', 'quantity': 3, 'unit_price': 20.0},
                {'description': 'Gizmo', 'quantity': 1, 'unit_price': 40.0},
            ],
        }, headers=self.get_auth_header(token))
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        inv = data['invoice']
        self.assertEqual(len(inv['items']), 2)
        # subtotal = 3*20 + 1*40 = 100
        self.assertAlmostEqual(inv['total_amount'], 100.0)

    def test_update_invoice_not_found(self):
        token = self._register_and_get_token()
        resp = self.client.put('/api/invoices/9999', json={
            'customer_name': 'X',
        }, headers=self.get_auth_header(token))
        self.assertEqual(resp.status_code, 404)

    def test_update_invoice_other_user(self):
        token_a = self._register_and_get_token('alice', 'alice@example.com')
        token_b = self._register_and_get_token('bob', 'bob@example.com')
        inv_id = self.create_sample_invoice(token_a).get_json()['invoice']['id']
        resp = self.client.put(f'/api/invoices/{inv_id}', json={
            'customer_name': 'Hacker',
        }, headers=self.get_auth_header(token_b))
        self.assertEqual(resp.status_code, 404)

    def test_update_invoice_status(self):
        token = self._register_and_get_token()
        inv_id = self.create_sample_invoice(token).get_json()['invoice']['id']
        resp = self.client.put(f'/api/invoices/{inv_id}', json={
            'status': 'paid',
        }, headers=self.get_auth_header(token))
        data = resp.get_json()
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['invoice']['status'], 'paid')

    # ------------------------------------------------------------------
    # DELETE /api/invoices/<id>
    # ------------------------------------------------------------------

    def test_delete_invoice_success(self):
        token = self._register_and_get_token()
        inv_id = self.create_sample_invoice(token).get_json()['invoice']['id']
        resp = self.client.delete(f'/api/invoices/{inv_id}',
                                  headers=self.get_auth_header(token))
        self.assertEqual(resp.status_code, 200)
        # Confirm it's gone
        resp2 = self.client.get(f'/api/invoices/{inv_id}',
                                headers=self.get_auth_header(token))
        self.assertEqual(resp2.status_code, 404)

    def test_delete_invoice_not_found(self):
        token = self._register_and_get_token()
        resp = self.client.delete('/api/invoices/9999',
                                  headers=self.get_auth_header(token))
        self.assertEqual(resp.status_code, 404)

    def test_delete_invoice_other_user(self):
        token_a = self._register_and_get_token('alice', 'alice@example.com')
        token_b = self._register_and_get_token('bob', 'bob@example.com')
        inv_id = self.create_sample_invoice(token_a).get_json()['invoice']['id']
        resp = self.client.delete(f'/api/invoices/{inv_id}',
                                  headers=self.get_auth_header(token_b))
        self.assertEqual(resp.status_code, 404)


if __name__ == '__main__':
    unittest.main()
