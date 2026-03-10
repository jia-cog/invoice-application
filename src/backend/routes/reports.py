from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_
from models import db, Invoice, Report, User
import calendar

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/', methods=['GET'])
@jwt_required()
def get_reports():
    try:
        user_id = int(get_jwt_identity())
        reports = Report.query.filter_by(user_id=user_id).order_by(Report.created_at.desc()).all()
        
        return jsonify({
            'reports': [report.to_dict() for report in reports]
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_report():
    try:
        user_id = int(get_jwt_identity())
        data = request.get_json()
        
        # Validate required fields
        if not data.get('report_type') or not data.get('start_date') or not data.get('end_date'):
            return jsonify({'error': 'report_type, start_date, and end_date are required'}), 400
        
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        
        # Get invoices in the date range
        invoices = Invoice.query.filter(
            and_(
                Invoice.user_id == user_id,
                Invoice.issue_date >= start_date,
                Invoice.issue_date <= end_date
            )
        ).all()
        
        # Calculate report metrics
        total_invoices = len(invoices)
        total_revenue = float(sum(float(inv.total_amount or 0) for inv in invoices))
        paid_invoices = [inv for inv in invoices if inv.status == 'paid']
        pending_invoices = [inv for inv in invoices if inv.status in ['draft', 'sent']]
        overdue_invoices = [inv for inv in invoices if inv.status == 'overdue']
        
        paid_revenue = float(sum(float(inv.total_amount or 0) for inv in paid_invoices))
        pending_revenue = float(sum(float(inv.total_amount or 0) for inv in pending_invoices))
        overdue_revenue = float(sum(float(inv.total_amount or 0) for inv in overdue_invoices))
        
        # Monthly breakdown
        monthly_data = {}
        for invoice in invoices:
            month_key = invoice.issue_date.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {
                    'month': invoice.issue_date.strftime('%B %Y'),
                    'count': 0,
                    'revenue': 0
                }
            monthly_data[month_key]['count'] += 1
            monthly_data[month_key]['revenue'] += float(invoice.total_amount or 0)
        
        # Status breakdown
        status_breakdown = {
            'draft': len([inv for inv in invoices if inv.status == 'draft']),
            'sent': len([inv for inv in invoices if inv.status == 'sent']),
            'paid': len([inv for inv in invoices if inv.status == 'paid']),
            'overdue': len([inv for inv in invoices if inv.status == 'overdue'])
        }
        
        # Top customers
        customer_data = {}
        for invoice in invoices:
            if invoice.customer_name not in customer_data:
                customer_data[invoice.customer_name] = {
                    'name': invoice.customer_name,
                    'count': 0,
                    'revenue': 0
                }
            customer_data[invoice.customer_name]['count'] += 1
            customer_data[invoice.customer_name]['revenue'] += float(invoice.total_amount or 0)
        
        top_customers = sorted(customer_data.values(), key=lambda x: x['revenue'], reverse=True)[:5]
        
        # Prepare report data
        report_data = {
            'summary': {
                'total_invoices': total_invoices,
                'total_revenue': round(total_revenue, 2),
                'paid_revenue': round(paid_revenue, 2),
                'pending_revenue': round(pending_revenue, 2),
                'overdue_revenue': round(overdue_revenue, 2),
                'average_invoice_value': round(total_revenue / total_invoices, 2) if total_invoices > 0 else 0
            },
            'status_breakdown': status_breakdown,
            'monthly_data': list(monthly_data.values()),
            'top_customers': top_customers,
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            }
        }
        
        # Save report to database
        report = Report(
            user_id=user_id,
            report_type=data['report_type'],
            start_date=start_date,
            end_date=end_date
        )
        report.set_data(report_data)
        
        db.session.add(report)
        db.session.commit()
        
        return jsonify({
            'message': 'Report generated successfully',
            'report': report.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard_data():
    try:
        user_id = int(get_jwt_identity())
        
        # Get current month data
        today = date.today()
        start_of_month = today.replace(day=1)
        
        # Get all invoices for the user
        all_invoices = Invoice.query.filter_by(user_id=user_id).all()
        current_month_invoices = Invoice.query.filter(
            and_(
                Invoice.user_id == user_id,
                Invoice.issue_date >= start_of_month
            )
        ).all()
        
        # Calculate metrics
        total_invoices = len(all_invoices)
        total_revenue = float(sum(float(inv.total_amount or 0) for inv in all_invoices))
        monthly_revenue = float(sum(float(inv.total_amount or 0) for inv in current_month_invoices))
        
        paid_invoices = [inv for inv in all_invoices if inv.status == 'paid']
        pending_invoices = [inv for inv in all_invoices if inv.status in ['draft', 'sent']]
        overdue_invoices = [inv for inv in all_invoices if inv.status == 'overdue']
        
        # Recent invoices (last 5)
        recent_invoices = Invoice.query.filter_by(user_id=user_id).order_by(
            Invoice.created_at.desc()
        ).limit(5).all()
        
        dashboard_data = {
            'overview': {
                'total_invoices': total_invoices,
                'total_revenue': round(total_revenue, 2),
                'monthly_revenue': round(monthly_revenue, 2),
                'paid_count': len(paid_invoices),
                'pending_count': len(pending_invoices),
                'overdue_count': len(overdue_invoices)
            },
            'recent_invoices': [invoice.to_dict() for invoice in recent_invoices]
        }
        
        return jsonify(dashboard_data), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@reports_bp.route('/<int:report_id>', methods=['DELETE'])
@jwt_required()
def delete_report(report_id):
    try:
        user_id = int(get_jwt_identity())
        report = Report.query.filter_by(id=report_id, user_id=user_id).first()
        
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        db.session.delete(report)
        db.session.commit()
        
        return jsonify({'message': 'Report deleted successfully'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
