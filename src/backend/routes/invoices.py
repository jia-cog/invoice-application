from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date
from models import db, Invoice, InvoiceItem, User
import uuid
import csv
import io

invoices_bp = Blueprint('invoices', __name__)

@invoices_bp.route('/', methods=['GET'])
@jwt_required()
def get_invoices():
    try:
        user_id = int(get_jwt_identity())
        invoices = Invoice.query.filter_by(user_id=user_id).order_by(Invoice.created_at.desc()).all()
        
        return jsonify({
            'invoices': [invoice.to_dict() for invoice in invoices]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@invoices_bp.route('/download', methods=['GET'])
@jwt_required()
def download_invoices():
    try:
        user_id = int(get_jwt_identity())
        invoices = Invoice.query.filter_by(user_id=user_id).order_by(Invoice.created_at.desc()).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow([
            'Invoice Number',
            'Customer Name',
            'Customer Email',
            'Customer Address',
            'Issue Date',
            'Due Date',
            'Status',
            'Subtotal',
            'Tax Rate (%)',
            'Tax Amount',
            'Total Amount',
            'Notes',
            'Created At',
            'Updated At'
        ])
        
        for invoice in invoices:
            writer.writerow([
                invoice.invoice_number,
                invoice.customer_name,
                invoice.customer_email or '',
                invoice.customer_address or '',
                invoice.issue_date.isoformat(),
                invoice.due_date.isoformat(),
                invoice.status,
                invoice.subtotal,
                invoice.tax_rate,
                invoice.tax_amount,
                invoice.total_amount,
                invoice.notes or '',
                invoice.created_at.isoformat(),
                invoice.updated_at.isoformat()
            ])
        
        output.seek(0)
        
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment; filename=invoices.csv',
                'Content-Type': 'text/csv'
            }
        )
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@invoices_bp.route('/<int:invoice_id>', methods=['GET'])
@jwt_required()
def get_invoice(invoice_id):
    try:
        user_id = int(get_jwt_identity())
        invoice = Invoice.query.filter_by(id=invoice_id, user_id=user_id).first()
        
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404
        
        return jsonify({'invoice': invoice.to_dict()}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@invoices_bp.route('/', methods=['POST'])
@jwt_required()
def create_invoice():
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['customer_name', 'due_date', 'items']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Generate unique invoice number
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Create invoice
        invoice = Invoice(
            invoice_number=invoice_number,
            user_id=user_id,
            customer_name=data['customer_name'],
            customer_email=data.get('customer_email', ''),
            customer_address=data.get('customer_address', ''),
            due_date=datetime.strptime(data['due_date'], '%Y-%m-%d').date(),
            tax_rate=data.get('tax_rate', 0.0),
            notes=data.get('notes', ''),
            status=data.get('status', 'draft')
        )
        
        db.session.add(invoice)
        db.session.flush()  # Get the invoice ID
        
        # Add invoice items
        for item_data in data['items']:
            if not item_data.get('description') or not item_data.get('quantity') or not item_data.get('unit_price'):
                return jsonify({'error': 'Each item must have description, quantity, and unit_price'}), 400
            
            item = InvoiceItem(
                invoice_id=invoice.id,
                description=item_data['description'],
                quantity=float(item_data['quantity']),
                unit_price=float(item_data['unit_price'])
            )
            item.calculate_total()
            db.session.add(item)
        
        # Calculate invoice totals
        invoice.calculate_totals()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Invoice created successfully',
            'invoice': invoice.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@invoices_bp.route('/<int:invoice_id>', methods=['PUT'])
@jwt_required()
def update_invoice(invoice_id):
    try:
        user_id = int(get_jwt_identity())
        invoice = Invoice.query.filter_by(id=invoice_id, user_id=user_id).first()
        
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404
        
        data = request.get_json()
        
        # Update invoice fields
        if 'customer_name' in data:
            invoice.customer_name = data['customer_name']
        if 'customer_email' in data:
            invoice.customer_email = data['customer_email']
        if 'customer_address' in data:
            invoice.customer_address = data['customer_address']
        if 'due_date' in data:
            invoice.due_date = datetime.strptime(data['due_date'], '%Y-%m-%d').date()
        if 'tax_rate' in data:
            invoice.tax_rate = data['tax_rate']
        if 'notes' in data:
            invoice.notes = data['notes']
        if 'status' in data:
            invoice.status = data['status']
        
        # Update items if provided
        if 'items' in data:
            # Remove existing items
            InvoiceItem.query.filter_by(invoice_id=invoice.id).delete()
            
            # Add new items
            for item_data in data['items']:
                item = InvoiceItem(
                    invoice_id=invoice.id,
                    description=item_data['description'],
                    quantity=float(item_data['quantity']),
                    unit_price=float(item_data['unit_price'])
                )
                item.calculate_total()
                db.session.add(item)
        
        # Recalculate totals
        invoice.calculate_totals()
        invoice.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'message': 'Invoice updated successfully',
            'invoice': invoice.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@invoices_bp.route('/<int:invoice_id>', methods=['DELETE'])
@jwt_required()
def delete_invoice(invoice_id):
    try:
        user_id = int(get_jwt_identity())
        invoice = Invoice.query.filter_by(id=invoice_id, user_id=user_id).first()
        
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404
        
        db.session.delete(invoice)
        db.session.commit()
        
        return jsonify({'message': 'Invoice deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
