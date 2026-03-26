from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, date, timedelta
from sqlalchemy import and_
from models import db, Invoice
import csv
import io

exports_bp = Blueprint('exports', __name__)


def get_last_month_range():
    """Calculate the 1st and last day of the previous calendar month."""
    today = date.today()
    first_of_current = today.replace(day=1)
    last_of_prev = first_of_current - timedelta(days=1)
    first_of_prev = last_of_prev.replace(day=1)
    return first_of_prev, last_of_prev


@exports_bp.route('/export', methods=['GET'])
@jwt_required()
def export_invoices():
    try:
        user_id = int(get_jwt_identity())

        # Determine date range (default: last month)
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            start_date, end_date = get_last_month_range()

        # Query invoices within date range for the authenticated user
        invoices = Invoice.query.filter(
            and_(
                Invoice.user_id == user_id,
                Invoice.issue_date >= start_date,
                Invoice.issue_date <= end_date
            )
        ).order_by(Invoice.issue_date.asc()).all()

        # Build daily totals
        daily_totals = {}
        for inv in invoices:
            day_key = inv.issue_date.isoformat()
            if day_key not in daily_totals:
                daily_totals[day_key] = {'date': day_key, 'total_amount': 0.0, 'count': 0}
            daily_totals[day_key]['total_amount'] += inv.total_amount
            daily_totals[day_key]['count'] += 1

        # Fill in missing days with zeros
        all_days = []
        current = start_date
        while current <= end_date:
            day_key = current.isoformat()
            if day_key in daily_totals:
                all_days.append(daily_totals[day_key])
            else:
                all_days.append({'date': day_key, 'total_amount': 0.0, 'count': 0})
            current += timedelta(days=1)

        # Status breakdown
        status_breakdown = {'draft': 0, 'sent': 0, 'paid': 0, 'overdue': 0}
        for inv in invoices:
            status = inv.status or 'draft'
            if status in status_breakdown:
                status_breakdown[status] += 1

        # Overall summary
        total_count = len(invoices)
        total_revenue = sum(inv.total_amount for inv in invoices)
        average_amount = round(total_revenue / total_count, 2) if total_count > 0 else 0.0

        return jsonify({
            'date_range': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'summary': {
                'total_count': total_count,
                'total_revenue': round(total_revenue, 2),
                'average_amount': average_amount
            },
            'status_breakdown': status_breakdown,
            'daily_totals': all_days,
            'invoices': [inv.to_dict() for inv in invoices]
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@exports_bp.route('/export/csv', methods=['GET'])
@jwt_required()
def export_invoices_csv():
    try:
        user_id = int(get_jwt_identity())

        # Determine date range (default: last month)
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            start_date, end_date = get_last_month_range()

        # Query invoices
        invoices = Invoice.query.filter(
            and_(
                Invoice.user_id == user_id,
                Invoice.issue_date >= start_date,
                Invoice.issue_date <= end_date
            )
        ).order_by(Invoice.issue_date.asc()).all()

        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow([
            'invoice_number', 'customer_name', 'issue_date', 'due_date',
            'status', 'subtotal', 'tax_rate', 'tax_amount', 'total_amount', 'notes'
        ])

        # Data rows
        for inv in invoices:
            writer.writerow([
                inv.invoice_number,
                inv.customer_name,
                inv.issue_date.isoformat(),
                inv.due_date.isoformat(),
                inv.status,
                round(inv.subtotal, 2),
                round(inv.tax_rate, 2),
                round(inv.tax_amount, 2),
                round(inv.total_amount, 2),
                inv.notes or ''
            ])

        csv_content = output.getvalue()
        output.close()

        # Build filename with year and month of the export range
        filename = f"invoices_export_{start_date.strftime('%Y_%m')}.csv"

        return Response(
            csv_content,
            mimetype='text/csv',
            headers={
                'Content-Type': 'text/csv',
                'Content-Disposition': f'attachment; filename={filename}'
            }
        )

    except Exception as e:
        return jsonify({'error': str(e)}), 500
