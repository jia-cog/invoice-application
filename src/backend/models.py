from decimal import Decimal

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Numeric

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    company_name = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with invoices
    invoices = db.relationship('Invoice', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'company_name': self.company_name,
            'created_at': self.created_at.isoformat()
        }

class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Customer information
    customer_name = db.Column(db.String(200), nullable=False)
    customer_email = db.Column(db.String(120))
    customer_address = db.Column(db.Text)
    
    # Invoice details
    issue_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date())
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='draft')  # draft, sent, paid, overdue
    
    # Financial information — use Numeric for monetary precision
    subtotal = db.Column(Numeric(12, 2), default=0.0)
    tax_rate = db.Column(Numeric(5, 2), default=0.0)
    tax_amount = db.Column(Numeric(12, 2), default=0.0)
    total_amount = db.Column(Numeric(12, 2), default=0.0)
    
    # Additional fields
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship with invoice items
    items = db.relationship('InvoiceItem', backref='invoice', lazy=True, cascade='all, delete-orphan')
    
    def calculate_totals(self):
        self.subtotal = sum(item.total for item in self.items)
        self.tax_amount = self.subtotal * (self.tax_rate / 100)
        self.total_amount = self.subtotal + self.tax_amount
    
    def to_dict(self):
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'customer_name': self.customer_name,
            'customer_email': self.customer_email,
            'customer_address': self.customer_address,
            'issue_date': self.issue_date.isoformat(),
            'due_date': self.due_date.isoformat(),
            'status': self.status,
            'subtotal': float(self.subtotal) if self.subtotal is not None else 0.0,
            'tax_rate': float(self.tax_rate) if self.tax_rate is not None else 0.0,
            'tax_amount': float(self.tax_amount) if self.tax_amount is not None else 0.0,
            'total_amount': float(self.total_amount) if self.total_amount is not None else 0.0,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'items': [item.to_dict() for item in self.items]
        }

class InvoiceItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoice.id'), nullable=False)
    
    description = db.Column(db.String(500), nullable=False)
    quantity = db.Column(Numeric(10, 2), nullable=False, default=1.0)
    unit_price = db.Column(Numeric(12, 2), nullable=False)
    total = db.Column(Numeric(12, 2), nullable=False)
    
    def calculate_total(self):
        self.total = self.quantity * self.unit_price
    
    def to_dict(self):
        return {
            'id': self.id,
            'description': self.description,
            'quantity': float(self.quantity) if self.quantity is not None else 0.0,
            'unit_price': float(self.unit_price) if self.unit_price is not None else 0.0,
            'total': float(self.total) if self.total is not None else 0.0
        }

class Report(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    report_type = db.Column(db.String(50), nullable=False)  # monthly, quarterly, yearly, custom
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    
    # Report data (native JSON type for PostgreSQL; falls back to Text on SQLite)
    data = db.Column(db.JSON)  # JSON object containing report metrics
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with user
    user = db.relationship('User', backref='reports')
    
    def set_data(self, data_dict):
        self.data = data_dict
    
    def get_data(self):
        return self.data if self.data else {}
    
    def to_dict(self):
        return {
            'id': self.id,
            'report_type': self.report_type,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat(),
            'data': self.get_data(),
            'created_at': self.created_at.isoformat()
        }
