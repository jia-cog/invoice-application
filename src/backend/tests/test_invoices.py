"""
Tests for invoice CRUD routes: GET, POST, PUT, DELETE on /api/invoices.
"""

import unittest
from base import BaseTestCase


class TestCreateInvoice(BaseTestCase):
    """POST /api/invoices/"""

    def test_create_invoice_success(self):
        token = self.get_token()
        resp = self.create_sample_invoice(token)
        data = resp.get_json()

        self.assertEqual(resp.status_code, 201)
        self.assertEqual(data['message'], 'Invoice created successfully')
        inv = data['invoice']
        self.assertTrue(inv['invoice_number'].startswith('INV-'))
        self.assertEqual(inv['customer_name'], 'Acme Corp')
        self.assertEqual(inv['status'], 'draft')
        self.assertEqual(len(inv['items']), 2)

    def test_create_invoice_calculates_totals(self):
        token = self.get_token()
        resp = self.create_sample_invoice(token)
        inv = resp.get_json()['invoice']

        # 2*50 + 1*100 = 200 subtotal, 10% tax = 20, total = 220
        self.assertAlmostEqual(inv['subtotal'], 200.0)
        self.assertAlmostEqual(inv['tax_amount'], 20.0)
        self.assertAlmostEqual(inv['total_amount'], 220.0)

    def test_create_invoice_missing_customer_name(self):
        token = self.get_token()
        resp = self.client.post('/api/invoices/', json={
            'due_date': '2026-12-31',
            'items': [{'description': 'x', 'quantity': 1, 'unit_price': 10}],
        }, headers=self.auth_header(token))

        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_missing_due_date(self):
        token = self.get_token()
        resp = self.client.post('/api/invoices/', json={
            'customer_name': 'Bob',
            'items': [{'description': 'x', 'quantity': 1, 'unit_price': 10}],
        }, headers=self.auth_header(token))

        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_missing_items(self):
        token = self.get_token()
        resp = self.client.post('/api/invoices/', json={
            'customer_name': 'Bob',
            'due_date': '2026-12-31',
        }, headers=self.auth_header(token))

        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_empty_items_list(self):
        token = self.get_token()
        resp = self.client.post('/api/invoices/', json={
            'customer_name': 'Bob',
            'due_date': '2026-12-31',
            'items': [],
        }, headers=self.auth_header(token))

        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_item_missing_description(self):
        token = self.get_token()
        resp = self.client.post('/api/invoices/', json={
            'customer_name': 'Bob',
            'due_date': '2026-12-31',
            'items': [{'quantity': 1, 'unit_price': 10}],
        }, headers=self.auth_header(token))

        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_no_auth(self):
        resp = self.client.post('/api/invoices/', json={
            'customer_name': 'Bob',
            'due_date': '2026-12-31',
            'items': [{'description': 'x', 'quantity': 1, 'unit_price': 10}],
        })
        self.assertEqual(resp.status_code, 401)

    def test_create_invoice_with_zero_tax(self):
        token = self.get_token()
        resp = self.create_sample_invoice(token, tax_rate=0.0)
        inv = resp.get_json()['invoice']

        self.assertAlmostEqual(inv['tax_amount'], 0.0)
        self.assertAlmostEqual(inv['total_amount'], inv['subtotal'])


class TestGetInvoices(BaseTestCase):
    """GET /api/invoices/"""

    def test_get_invoices_empty(self):
        token = self.get_token()
        resp = self.client.get('/api/invoices/',
                               headers=self.auth_header(token))
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(data['invoices']), 0)

    def test_get_invoices_returns_own_only(self):
        token_a = self.get_token(username='alice', email='a@a.com')
        token_b = self.get_token(username='bob', email='b@b.com')

        self.create_sample_invoice(token_a)
        self.create_sample_invoice(token_a)
        self.create_sample_invoice(token_b)

        resp_a = self.client.get('/api/invoices/',
                                 headers=self.auth_header(token_a))
        resp_b = self.client.get('/api/invoices/',
                                 headers=self.auth_header(token_b))

        self.assertEqual(len(resp_a.get_json()['invoices']), 2)
        self.assertEqual(len(resp_b.get_json()['invoices']), 1)

    def test_get_invoices_no_auth(self):
        resp = self.client.get('/api/invoices/')
        self.assertEqual(resp.status_code, 401)


class TestGetSingleInvoice(BaseTestCase):
    """GET /api/invoices/<id>"""

    def test_get_invoice_success(self):
        token = self.get_token()
        create_resp = self.create_sample_invoice(token)
        inv_id = create_resp.get_json()['invoice']['id']

        resp = self.client.get(f'/api/invoices/{inv_id}',
                               headers=self.auth_header(token))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['invoice']['id'], inv_id)

    def test_get_invoice_not_found(self):
        token = self.get_token()
        resp = self.client.get('/api/invoices/9999',
                               headers=self.auth_header(token))
        self.assertEqual(resp.status_code, 404)

    def test_get_invoice_owned_by_another_user(self):
        token_a = self.get_token(username='alice', email='a@a.com')
        token_b = self.get_token(username='bob', email='b@b.com')

        create_resp = self.create_sample_invoice(token_a)
        inv_id = create_resp.get_json()['invoice']['id']

        resp = self.client.get(f'/api/invoices/{inv_id}',
                               headers=self.auth_header(token_b))
        self.assertEqual(resp.status_code, 404)


class TestUpdateInvoice(BaseTestCase):
    """PUT /api/invoices/<id>"""

    def test_update_invoice_fields(self):
        token = self.get_token()
        inv_id = self.create_sample_invoice(token).get_json()['invoice']['id']

        resp = self.client.put(f'/api/invoices/{inv_id}', json={
            'customer_name': 'Updated Name',
            'status': 'sent',
            'notes': 'updated notes',
        }, headers=self.auth_header(token))
        data = resp.get_json()

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(data['invoice']['customer_name'], 'Updated Name')
        self.assertEqual(data['invoice']['status'], 'sent')
        self.assertEqual(data['invoice']['notes'], 'updated notes')

    def test_update_invoice_items(self):
        token = self.get_token()
        inv_id = self.create_sample_invoice(token).get_json()['invoice']['id']

        new_items = [
            {'description': 'New Item', 'quantity': 5, 'unit_price': 20.0},
        ]
        resp = self.client.put(f'/api/invoices/{inv_id}', json={
            'items': new_items,
            'tax_rate': 0,
        }, headers=self.auth_header(token))
        inv = resp.get_json()['invoice']

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(inv['items']), 1)
        self.assertAlmostEqual(inv['subtotal'], 100.0)

    def test_update_invoice_not_found(self):
        token = self.get_token()
        resp = self.client.put('/api/invoices/9999', json={
            'customer_name': 'X',
        }, headers=self.auth_header(token))
        self.assertEqual(resp.status_code, 404)

    def test_update_invoice_owned_by_another_user(self):
        token_a = self.get_token(username='alice', email='a@a.com')
        token_b = self.get_token(username='bob', email='b@b.com')

        inv_id = self.create_sample_invoice(token_a).get_json()['invoice']['id']

        resp = self.client.put(f'/api/invoices/{inv_id}', json={
            'status': 'paid',
        }, headers=self.auth_header(token_b))
        self.assertEqual(resp.status_code, 404)

    def test_update_invoice_due_date(self):
        token = self.get_token()
        inv_id = self.create_sample_invoice(token).get_json()['invoice']['id']

        resp = self.client.put(f'/api/invoices/{inv_id}', json={
            'due_date': '2027-06-15',
        }, headers=self.auth_header(token))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['invoice']['due_date'], '2027-06-15')

    def test_update_invoice_no_auth(self):
        resp = self.client.put('/api/invoices/1', json={'status': 'paid'})
        self.assertEqual(resp.status_code, 401)


class TestDeleteInvoice(BaseTestCase):
    """DELETE /api/invoices/<id>"""

    def test_delete_invoice_success(self):
        token = self.get_token()
        inv_id = self.create_sample_invoice(token).get_json()['invoice']['id']

        resp = self.client.delete(f'/api/invoices/{inv_id}',
                                  headers=self.auth_header(token))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('deleted', resp.get_json()['message'].lower())

        # Verify it's gone
        get_resp = self.client.get(f'/api/invoices/{inv_id}',
                                   headers=self.auth_header(token))
        self.assertEqual(get_resp.status_code, 404)

    def test_delete_invoice_not_found(self):
        token = self.get_token()
        resp = self.client.delete('/api/invoices/9999',
                                  headers=self.auth_header(token))
        self.assertEqual(resp.status_code, 404)

    def test_delete_invoice_owned_by_another_user(self):
        token_a = self.get_token(username='alice', email='a@a.com')
        token_b = self.get_token(username='bob', email='b@b.com')

        inv_id = self.create_sample_invoice(token_a).get_json()['invoice']['id']

        resp = self.client.delete(f'/api/invoices/{inv_id}',
                                  headers=self.auth_header(token_b))
        self.assertEqual(resp.status_code, 404)

        # Verify it still exists for the owner
        get_resp = self.client.get(f'/api/invoices/{inv_id}',
                                   headers=self.auth_header(token_a))
        self.assertEqual(get_resp.status_code, 200)

    def test_delete_invoice_no_auth(self):
        resp = self.client.delete('/api/invoices/1')
        self.assertEqual(resp.status_code, 401)


if __name__ == '__main__':
    unittest.main()
