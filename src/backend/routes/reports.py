from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date, timedelta
from sqlalchemy import func, and_, case
from models import db, Invoice, Report, User, RequestLog
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
        total_revenue = sum(invoice.total_amount for invoice in invoices)
        paid_invoices = [inv for inv in invoices if inv.status == 'paid']
        pending_invoices = [inv for inv in invoices if inv.status in ['draft', 'sent']]
        overdue_invoices = [inv for inv in invoices if inv.status == 'overdue']
        
        paid_revenue = sum(invoice.total_amount for invoice in paid_invoices)
        pending_revenue = sum(invoice.total_amount for invoice in pending_invoices)
        overdue_revenue = sum(invoice.total_amount for invoice in overdue_invoices)
        
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
            monthly_data[month_key]['revenue'] += invoice.total_amount
        
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
            customer_data[invoice.customer_name]['revenue'] += invoice.total_amount
        
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
        total_revenue = sum(invoice.total_amount for invoice in all_invoices)
        monthly_revenue = sum(invoice.total_amount for invoice in current_month_invoices)
        
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


@reports_bp.route('/usage-analytics', methods=['GET'])
@jwt_required()
def get_usage_analytics():
    try:
        days = request.args.get('days', 60, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)

        # Aggregate by endpoint
        endpoint_stats = db.session.query(
            RequestLog.endpoint,
            RequestLog.method,
            func.count(RequestLog.id).label('hit_count')
        ).filter(
            RequestLog.timestamp >= start_date
        ).group_by(
            RequestLog.endpoint, RequestLog.method
        ).order_by(
            func.count(RequestLog.id).desc()
        ).all()

        # Daily trends
        daily_trends = db.session.query(
            func.date(RequestLog.timestamp).label('day'),
            func.count(RequestLog.id).label('hit_count')
        ).filter(
            RequestLog.timestamp >= start_date
        ).group_by(
            func.date(RequestLog.timestamp)
        ).order_by(
            func.date(RequestLog.timestamp)
        ).all()

        # Status code distribution
        status_distribution = db.session.query(
            RequestLog.status_code,
            func.count(RequestLog.id).label('count')
        ).filter(
            RequestLog.timestamp >= start_date
        ).group_by(
            RequestLog.status_code
        ).all()

        # Total requests
        total_requests = db.session.query(
            func.count(RequestLog.id)
        ).filter(
            RequestLog.timestamp >= start_date
        ).scalar() or 0

        return jsonify({
            'total_requests': total_requests,
            'days': days,
            'endpoint_stats': [
                {
                    'endpoint': stat.endpoint,
                    'method': stat.method,
                    'hit_count': stat.hit_count
                } for stat in endpoint_stats
            ],
            'daily_trends': [
                {
                    'date': str(trend.day),
                    'hit_count': trend.hit_count
                } for trend in daily_trends
            ],
            'status_distribution': [
                {
                    'status_code': dist.status_code,
                    'count': dist.count
                } for dist in status_distribution
            ]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@reports_bp.route('/invoice-quality', methods=['GET'])
@jwt_required()
def get_quality_metrics():
    try:
        user_id = int(get_jwt_identity())
        days = request.args.get('days', 60, type=int)
        start_date = datetime.utcnow() - timedelta(days=days)
        today = date.today()

        # Get invoices in the time range for this user
        invoices = Invoice.query.filter(
            and_(
                Invoice.user_id == user_id,
                Invoice.created_at >= start_date
            )
        ).all()

        total_invoices = len(invoices)
        if total_invoices == 0:
            return jsonify({
                'total_invoices': 0,
                'days': days,
                'overdue_rate': 0,
                'draft_stuck_rate': 0,
                'missing_email_rate': 0,
                'missing_address_rate': 0,
                'missing_notes_rate': 0,
                'draft_to_paid_rate': 0,
                'daily_trends': [],
                'status_breakdown': {'draft': 0, 'sent': 0, 'paid': 0, 'overdue': 0}
            }), 200

        # Overdue rate
        overdue_count = len([inv for inv in invoices if inv.status == 'overdue'
                            or (inv.due_date and inv.due_date < today and inv.status not in ('paid',))])
        overdue_rate = round((overdue_count / total_invoices) * 100, 2)

        # Draft-stuck rate: invoices that are still in draft status
        draft_stuck_count = len([inv for inv in invoices if inv.status == 'draft'])
        draft_stuck_rate = round((draft_stuck_count / total_invoices) * 100, 2)

        # Missing fields rates
        missing_email_count = len([inv for inv in invoices
                                   if not inv.customer_email or inv.customer_email.strip() == ''])
        missing_address_count = len([inv for inv in invoices
                                     if not inv.customer_address or inv.customer_address.strip() == ''])
        missing_notes_count = len([inv for inv in invoices
                                   if not inv.notes or inv.notes.strip() == ''])

        missing_email_rate = round((missing_email_count / total_invoices) * 100, 2)
        missing_address_rate = round((missing_address_count / total_invoices) * 100, 2)
        missing_notes_rate = round((missing_notes_count / total_invoices) * 100, 2)

        # Draft-to-paid conversion rate
        paid_count = len([inv for inv in invoices if inv.status == 'paid'])
        draft_to_paid_rate = round((paid_count / total_invoices) * 100, 2)

        # Status breakdown
        status_breakdown = {
            'draft': len([inv for inv in invoices if inv.status == 'draft']),
            'sent': len([inv for inv in invoices if inv.status == 'sent']),
            'paid': len([inv for inv in invoices if inv.status == 'paid']),
            'overdue': len([inv for inv in invoices if inv.status == 'overdue'])
        }

        # Invoice generation trends (daily)
        daily_data = {}
        for inv in invoices:
            day_key = inv.created_at.strftime('%Y-%m-%d')
            if day_key not in daily_data:
                daily_data[day_key] = {'date': day_key, 'count': 0, 'total_amount': 0}
            daily_data[day_key]['count'] += 1
            daily_data[day_key]['total_amount'] += inv.total_amount or 0

        daily_trends = sorted(daily_data.values(), key=lambda x: x['date'])
        for entry in daily_trends:
            entry['total_amount'] = round(entry['total_amount'], 2)

        return jsonify({
            'total_invoices': total_invoices,
            'days': days,
            'overdue_rate': overdue_rate,
            'draft_stuck_rate': draft_stuck_rate,
            'missing_email_rate': missing_email_rate,
            'missing_address_rate': missing_address_rate,
            'missing_notes_rate': missing_notes_rate,
            'draft_to_paid_rate': draft_to_paid_rate,
            'status_breakdown': status_breakdown,
            'daily_trends': daily_trends
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
