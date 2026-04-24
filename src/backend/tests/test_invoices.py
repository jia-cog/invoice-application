#!/usr/bin/env python3
"""
Invoice Tests

Comprehensive tests for invoice CRUD operations, validation,
error handling, and authentication/authorization.
"""

import sys
import os
import unittest

# Add the parent directory to the path to import backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from flask_jwt_extended import JWTManager, create_access_token
from config import Config
from models import db, User, Invoice, InvoiceItem


def _create_app():
    """Create a Flask app configured for testing with an in-memory database."""
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['TESTING'] = True

    db.init_app(app)
    JWTManager(app)

    from routes.invoices import invoices_bp
    app.register_blueprint(invoices_bp, url_prefix='/api/invoices')

    return app


def _sample_invoice_payload(**overrides):
    """Return a valid invoice creation payload, optionally overridden."""
    payload = {
        'customer_name': 'Acme Corp',
        'customer_email': 'billing@acme.com',
        'customer_address': '123 Main St',
        'due_date': '2026-06-01',
        'tax_rate': 10.0,
        'notes': 'Net 30',
        'status': 'draft',
        'items': [
            {
                'description': 'Consulting',
                'quantity': 5,
                'unit_price': 100.0,
            },
            {
                'description': 'Support',
                'quantity': 2,
                'unit_price': 50.0,
            },
        ],
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Model-level tests
# ---------------------------------------------------------------------------

class TestInvoiceItemModel(unittest.TestCase):
    """Tests for the InvoiceItem model."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = _create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

    def tearDown(self):
        """Clean up after each test."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_calculate_total(self):
        """InvoiceItem.calculate_total sets total = quantity * unit_price."""
        item = InvoiceItem(description='Widget', quantity=3, unit_price=25.0, total=0)
        item.calculate_total()
        self.assertAlmostEqual(item.total, 75.0)

    def test_calculate_total_fractional_quantity(self):
        """Fractional quantities are handled correctly."""
        item = InvoiceItem(description='Hours', quantity=1.5, unit_price=200.0, total=0)
        item.calculate_total()
        self.assertAlmostEqual(item.total, 300.0)

    def test_to_dict(self):
        """to_dict returns the expected keys."""
        item = InvoiceItem(
            id=1, description='Widget', quantity=2, unit_price=10.0, total=20.0
        )
        d = item.to_dict()
        self.assertEqual(d['description'], 'Widget')
        self.assertEqual(d['quantity'], 2)
        self.assertEqual(d['unit_price'], 10.0)
        self.assertEqual(d['total'], 20.0)


class TestInvoiceModel(unittest.TestCase):
    """Tests for the Invoice model."""

    def setUp(self):
        """Set up test fixtures."""
        self.app = _create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        user = User(username='tester', email='tester@test.com')
        user.set_password('password')
        db.session.add(user)
        db.session.commit()
        self.user = user

    def tearDown(self):
        """Clean up after each test."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def test_calculate_totals_no_tax(self):
        """calculate_totals with zero tax rate."""
        invoice = Invoice(
            invoice_number='INV-001',
            user_id=self.user.id,
            customer_name='Test',
            due_date=__import__('datetime').date(2026, 6, 1),
            tax_rate=0.0,
        )
        db.session.add(invoice)
        db.session.flush()

        item = InvoiceItem(
            invoice_id=invoice.id, description='A', quantity=2, unit_price=50.0, total=100.0
        )
        db.session.add(item)
        db.session.flush()

        invoice.calculate_totals()
        self.assertAlmostEqual(invoice.subtotal, 100.0)
        self.assertAlmostEqual(invoice.tax_amount, 0.0)
        self.assertAlmostEqual(invoice.total_amount, 100.0)

    def test_calculate_totals_with_tax(self):
        """calculate_totals applies the tax rate correctly."""
        invoice = Invoice(
            invoice_number='INV-002',
            user_id=self.user.id,
            customer_name='Test',
            due_date=__import__('datetime').date(2026, 6, 1),
            tax_rate=10.0,
        )
        db.session.add(invoice)
        db.session.flush()

        item = InvoiceItem(
            invoice_id=invoice.id, description='B', quantity=1, unit_price=200.0, total=200.0
        )
        db.session.add(item)
        db.session.flush()

        invoice.calculate_totals()
        self.assertAlmostEqual(invoice.subtotal, 200.0)
        self.assertAlmostEqual(invoice.tax_amount, 20.0)
        self.assertAlmostEqual(invoice.total_amount, 220.0)

    def test_calculate_totals_multiple_items(self):
        """calculate_totals sums across multiple items."""
        invoice = Invoice(
            invoice_number='INV-003',
            user_id=self.user.id,
            customer_name='Test',
            due_date=__import__('datetime').date(2026, 6, 1),
            tax_rate=5.0,
        )
        db.session.add(invoice)
        db.session.flush()

        for desc, qty, price in [('X', 2, 10.0), ('Y', 3, 20.0)]:
            item = InvoiceItem(
                invoice_id=invoice.id,
                description=desc,
                quantity=qty,
                unit_price=price,
                total=qty * price,
            )
            db.session.add(item)
        db.session.flush()

        invoice.calculate_totals()
        self.assertAlmostEqual(invoice.subtotal, 80.0)
        self.assertAlmostEqual(invoice.tax_amount, 4.0)
        self.assertAlmostEqual(invoice.total_amount, 84.0)

    def test_to_dict_keys(self):
        """to_dict returns expected top-level keys."""
        invoice = Invoice(
            invoice_number='INV-004',
            user_id=self.user.id,
            customer_name='Test',
            due_date=__import__('datetime').date(2026, 6, 1),
            tax_rate=0.0,
        )
        db.session.add(invoice)
        db.session.commit()

        d = invoice.to_dict()
        expected_keys = {
            'id', 'invoice_number', 'customer_name', 'customer_email',
            'customer_address', 'issue_date', 'due_date', 'status',
            'subtotal', 'tax_rate', 'tax_amount', 'total_amount',
            'notes', 'created_at', 'updated_at', 'items',
        }
        self.assertEqual(set(d.keys()), expected_keys)


# ---------------------------------------------------------------------------
# API / route-level tests
# ---------------------------------------------------------------------------

class TestInvoiceAPI(unittest.TestCase):
    """Tests for invoice API endpoints (CRUD, validation, auth)."""

    def setUp(self):
        """Set up Flask test client, database, and auth token."""
        self.app = _create_app()
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()

        # Create a test user
        user = User(username='testuser', email='test@example.com')
        user.set_password('testpassword')
        db.session.add(user)
        db.session.commit()
        self.user = user

        # Create a second user to test authorization isolation
        user2 = User(username='otheruser', email='other@example.com')
        user2.set_password('otherpassword')
        db.session.add(user2)
        db.session.commit()
        self.user2 = user2

        # Generate JWT tokens
        self.token = create_access_token(identity=str(self.user.id))
        self.token2 = create_access_token(identity=str(self.user2.id))

        self.client = self.app.test_client()

    def tearDown(self):
        """Clean up database and app context."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _auth_header(self, token=None):
        """Return an Authorization header dict."""
        return {'Authorization': f'Bearer {token or self.token}'}

    # ------------------------------------------------------------------
    # Authentication / Authorization
    # ------------------------------------------------------------------

    def test_get_invoices_unauthenticated(self):
        """GET /api/invoices/ without token returns 401."""
        resp = self.client.get('/api/invoices/')
        self.assertEqual(resp.status_code, 401)

    def test_get_invoice_unauthenticated(self):
        """GET /api/invoices/<id> without token returns 401."""
        resp = self.client.get('/api/invoices/1')
        self.assertEqual(resp.status_code, 401)

    def test_create_invoice_unauthenticated(self):
        """POST /api/invoices/ without token returns 401."""
        resp = self.client.post(
            '/api/invoices/',
            json=_sample_invoice_payload(),
        )
        self.assertEqual(resp.status_code, 401)

    def test_update_invoice_unauthenticated(self):
        """PUT /api/invoices/<id> without token returns 401."""
        resp = self.client.put(
            '/api/invoices/1',
            json={'customer_name': 'New Name'},
        )
        self.assertEqual(resp.status_code, 401)

    def test_delete_invoice_unauthenticated(self):
        """DELETE /api/invoices/<id> without token returns 401."""
        resp = self.client.delete('/api/invoices/1')
        self.assertEqual(resp.status_code, 401)

    def test_user_cannot_read_other_users_invoice(self):
        """A user cannot retrieve another user's invoice."""
        # user1 creates an invoice
        resp = self.client.post(
            '/api/invoices/',
            json=_sample_invoice_payload(),
            headers=self._auth_header(self.token),
        )
        self.assertEqual(resp.status_code, 201)
        invoice_id = resp.get_json()['invoice']['id']

        # user2 tries to read it
        resp = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self._auth_header(self.token2),
        )
        self.assertEqual(resp.status_code, 404)

    def test_user_cannot_update_other_users_invoice(self):
        """A user cannot update another user's invoice."""
        resp = self.client.post(
            '/api/invoices/',
            json=_sample_invoice_payload(),
            headers=self._auth_header(self.token),
        )
        invoice_id = resp.get_json()['invoice']['id']

        resp = self.client.put(
            f'/api/invoices/{invoice_id}',
            json={'customer_name': 'Hacked'},
            headers=self._auth_header(self.token2),
        )
        self.assertEqual(resp.status_code, 404)

    def test_user_cannot_delete_other_users_invoice(self):
        """A user cannot delete another user's invoice."""
        resp = self.client.post(
            '/api/invoices/',
            json=_sample_invoice_payload(),
            headers=self._auth_header(self.token),
        )
        invoice_id = resp.get_json()['invoice']['id']

        resp = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self._auth_header(self.token2),
        )
        self.assertEqual(resp.status_code, 404)

    # ------------------------------------------------------------------
    # Create Invoice (POST)
    # ------------------------------------------------------------------

    def test_create_invoice_success(self):
        """POST /api/invoices/ with valid data returns 201."""
        payload = _sample_invoice_payload()
        resp = self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 201)

        data = resp.get_json()
        self.assertIn('invoice', data)
        inv = data['invoice']
        self.assertEqual(inv['customer_name'], 'Acme Corp')
        self.assertEqual(inv['customer_email'], 'billing@acme.com')
        self.assertEqual(inv['due_date'], '2026-06-01')
        self.assertEqual(inv['status'], 'draft')
        self.assertTrue(inv['invoice_number'].startswith('INV-'))
        self.assertEqual(len(inv['items']), 2)

    def test_create_invoice_calculates_totals(self):
        """Totals are correctly calculated on creation."""
        payload = _sample_invoice_payload(tax_rate=10.0)
        resp = self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self._auth_header(),
        )
        inv = resp.get_json()['invoice']
        # subtotal: 5*100 + 2*50 = 600
        self.assertAlmostEqual(inv['subtotal'], 600.0)
        self.assertAlmostEqual(inv['tax_amount'], 60.0)
        self.assertAlmostEqual(inv['total_amount'], 660.0)

    def test_create_invoice_missing_customer_name(self):
        """Missing customer_name returns 400."""
        payload = _sample_invoice_payload()
        del payload['customer_name']
        resp = self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('error', resp.get_json())

    def test_create_invoice_missing_due_date(self):
        """Missing due_date returns 400."""
        payload = _sample_invoice_payload()
        del payload['due_date']
        resp = self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_missing_items(self):
        """Missing items returns 400."""
        payload = _sample_invoice_payload()
        del payload['items']
        resp = self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_empty_items_list(self):
        """Empty items list returns 400."""
        payload = _sample_invoice_payload(items=[])
        resp = self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_item_missing_description(self):
        """Item without description returns 400."""
        payload = _sample_invoice_payload(
            items=[{'quantity': 1, 'unit_price': 10.0}]
        )
        resp = self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_item_missing_quantity(self):
        """Item without quantity returns 400."""
        payload = _sample_invoice_payload(
            items=[{'description': 'Thing', 'unit_price': 10.0}]
        )
        resp = self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_item_missing_unit_price(self):
        """Item without unit_price returns 400."""
        payload = _sample_invoice_payload(
            items=[{'description': 'Thing', 'quantity': 1}]
        )
        resp = self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 400)

    def test_create_invoice_optional_fields_default(self):
        """Optional fields default correctly when omitted."""
        payload = {
            'customer_name': 'Minimal Customer',
            'due_date': '2026-07-01',
            'items': [{'description': 'Item', 'quantity': 1, 'unit_price': 100.0}],
        }
        resp = self.client.post(
            '/api/invoices/',
            json=payload,
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 201)
        inv = resp.get_json()['invoice']
        self.assertEqual(inv['customer_email'], '')
        self.assertEqual(inv['customer_address'], '')
        self.assertEqual(inv['notes'], '')
        self.assertEqual(inv['status'], 'draft')
        self.assertAlmostEqual(inv['tax_rate'], 0.0)

    # ------------------------------------------------------------------
    # Read Invoices (GET list & single)
    # ------------------------------------------------------------------

    def test_get_invoices_empty(self):
        """GET /api/invoices/ with no invoices returns empty list."""
        resp = self.client.get(
            '/api/invoices/',
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['invoices'], [])

    def test_get_invoices_returns_own(self):
        """GET /api/invoices/ returns only the authenticated user's invoices."""
        # user1 creates two invoices
        for _ in range(2):
            self.client.post(
                '/api/invoices/',
                json=_sample_invoice_payload(),
                headers=self._auth_header(self.token),
            )
        # user2 creates one
        self.client.post(
            '/api/invoices/',
            json=_sample_invoice_payload(),
            headers=self._auth_header(self.token2),
        )

        resp = self.client.get(
            '/api/invoices/',
            headers=self._auth_header(self.token),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.get_json()['invoices']), 2)

    def test_get_single_invoice_success(self):
        """GET /api/invoices/<id> returns the correct invoice."""
        create_resp = self.client.post(
            '/api/invoices/',
            json=_sample_invoice_payload(),
            headers=self._auth_header(),
        )
        invoice_id = create_resp.get_json()['invoice']['id']

        resp = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()['invoice']['id'], invoice_id)

    def test_get_single_invoice_not_found(self):
        """GET /api/invoices/<id> for nonexistent invoice returns 404."""
        resp = self.client.get(
            '/api/invoices/99999',
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 404)

    # ------------------------------------------------------------------
    # Update Invoice (PUT)
    # ------------------------------------------------------------------

    def test_update_invoice_fields(self):
        """PUT /api/invoices/<id> updates provided fields."""
        create_resp = self.client.post(
            '/api/invoices/',
            json=_sample_invoice_payload(),
            headers=self._auth_header(),
        )
        invoice_id = create_resp.get_json()['invoice']['id']

        update_payload = {
            'customer_name': 'Updated Corp',
            'customer_email': 'new@acme.com',
            'customer_address': '456 Oak Ave',
            'due_date': '2026-08-15',
            'tax_rate': 15.0,
            'notes': 'Updated notes',
            'status': 'sent',
        }
        resp = self.client.put(
            f'/api/invoices/{invoice_id}',
            json=update_payload,
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 200)
        inv = resp.get_json()['invoice']
        self.assertEqual(inv['customer_name'], 'Updated Corp')
        self.assertEqual(inv['customer_email'], 'new@acme.com')
        self.assertEqual(inv['customer_address'], '456 Oak Ave')
        self.assertEqual(inv['due_date'], '2026-08-15')
        self.assertAlmostEqual(inv['tax_rate'], 15.0)
        self.assertEqual(inv['notes'], 'Updated notes')
        self.assertEqual(inv['status'], 'sent')

    def test_update_invoice_partial(self):
        """PUT /api/invoices/<id> with partial data only updates given fields."""
        create_resp = self.client.post(
            '/api/invoices/',
            json=_sample_invoice_payload(),
            headers=self._auth_header(),
        )
        invoice_id = create_resp.get_json()['invoice']['id']

        resp = self.client.put(
            f'/api/invoices/{invoice_id}',
            json={'status': 'paid'},
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 200)
        inv = resp.get_json()['invoice']
        self.assertEqual(inv['status'], 'paid')
        self.assertEqual(inv['customer_name'], 'Acme Corp')

    def test_update_invoice_replaces_items(self):
        """PUT with new items replaces existing items and recalculates totals."""
        create_resp = self.client.post(
            '/api/invoices/',
            json=_sample_invoice_payload(tax_rate=0.0),
            headers=self._auth_header(),
        )
        invoice_id = create_resp.get_json()['invoice']['id']

        new_items = [{'description': 'New Item', 'quantity': 10, 'unit_price': 30.0}]
        resp = self.client.put(
            f'/api/invoices/{invoice_id}',
            json={'items': new_items},
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 200)
        inv = resp.get_json()['invoice']
        self.assertEqual(len(inv['items']), 1)
        self.assertAlmostEqual(inv['subtotal'], 300.0)
        self.assertAlmostEqual(inv['total_amount'], 300.0)

    def test_update_invoice_not_found(self):
        """PUT /api/invoices/<id> for nonexistent invoice returns 404."""
        resp = self.client.put(
            '/api/invoices/99999',
            json={'status': 'paid'},
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 404)

    # ------------------------------------------------------------------
    # Delete Invoice (DELETE)
    # ------------------------------------------------------------------

    def test_delete_invoice_success(self):
        """DELETE /api/invoices/<id> removes the invoice."""
        create_resp = self.client.post(
            '/api/invoices/',
            json=_sample_invoice_payload(),
            headers=self._auth_header(),
        )
        invoice_id = create_resp.get_json()['invoice']['id']

        resp = self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 200)

        # Verify it is gone
        resp = self.client.get(
            f'/api/invoices/{invoice_id}',
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 404)

    def test_delete_invoice_not_found(self):
        """DELETE /api/invoices/<id> for nonexistent invoice returns 404."""
        resp = self.client.delete(
            '/api/invoices/99999',
            headers=self._auth_header(),
        )
        self.assertEqual(resp.status_code, 404)

    def test_delete_invoice_removes_items(self):
        """Deleting an invoice also removes its line items."""
        create_resp = self.client.post(
            '/api/invoices/',
            json=_sample_invoice_payload(),
            headers=self._auth_header(),
        )
        invoice_id = create_resp.get_json()['invoice']['id']

        self.client.delete(
            f'/api/invoices/{invoice_id}',
            headers=self._auth_header(),
        )

        items = InvoiceItem.query.filter_by(invoice_id=invoice_id).all()
        self.assertEqual(len(items), 0)

    # ------------------------------------------------------------------
    # Invoice number uniqueness
    # ------------------------------------------------------------------

    def test_invoice_numbers_are_unique(self):
        """Each created invoice has a distinct invoice_number."""
        numbers = set()
        for _ in range(5):
            resp = self.client.post(
                '/api/invoices/',
                json=_sample_invoice_payload(),
                headers=self._auth_header(),
            )
            self.assertEqual(resp.status_code, 201)
            numbers.add(resp.get_json()['invoice']['invoice_number'])
        self.assertEqual(len(numbers), 5)


def run_invoice_tests():
    """Run all invoice tests and return results."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestInvoiceItemModel))
    suite.addTests(loader.loadTestsFromTestCase(TestInvoiceModel))
    suite.addTests(loader.loadTestsFromTestCase(TestInvoiceAPI))
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
