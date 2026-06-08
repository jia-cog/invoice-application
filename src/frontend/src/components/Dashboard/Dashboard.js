import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { reportsAPI } from '../../utils/api';
import { toast } from 'react-toastify';
import { 
  FileText, 
  DollarSign, 
  TrendingUp, 
  Clock, 
  Plus,
  Eye,
  Calendar
} from 'lucide-react';
import { format } from 'date-fns';

const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const response = await reportsAPI.getDashboard();
      setDashboardData(response.data);
    } catch (error) {
      toast.error('Failed to load dashboard data');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadgeClass = (status) => {
    switch (status) {
      case 'paid':
        return 'status-badge status-paid';
      case 'sent':
        return 'status-badge status-sent';
      case 'overdue':
        return 'status-badge status-overdue';
      default:
        return 'status-badge status-draft';
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  const { overview, recent_invoices } = dashboardData || {};

  return (
    <div className="container" style={{ paddingTop: '2rem', paddingBottom: '2rem' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '2rem'
      }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold', color: '#1e293b' }}>
          Dashboard
        </h1>
        <Link to="/invoices/new" className="btn btn-primary">
          <Plus size={16} />
          New Invoice
        </Link>
      </div>

      {/* Overview Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
        gap: '1.5rem',
        marginBottom: '2rem'
      }}>
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                Total Invoices
              </p>
              <p style={{ fontSize: '2rem', fontWeight: 'bold', color: '#1e293b' }}>
                {overview?.total_invoices || 0}
              </p>
            </div>
            <div style={{
              backgroundColor: '#fce4e4',
              padding: '0.75rem',
              borderRadius: '0.5rem'
            }}>
              <FileText size={24} color="#ee0000" />
            </div>
          </div>
        </div>

        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                Total Revenue
              </p>
              <p style={{ fontSize: '2rem', fontWeight: 'bold', color: '#1e293b' }}>
                ${overview?.total_revenue?.toFixed(2) || '0.00'}
              </p>
            </div>
            <div style={{
              backgroundColor: '#d1fae5',
              padding: '0.75rem',
              borderRadius: '0.5rem'
            }}>
              <DollarSign size={24} color="#10b981" />
            </div>
          </div>
        </div>

        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                This Month
              </p>
              <p style={{ fontSize: '2rem', fontWeight: 'bold', color: '#1e293b' }}>
                ${overview?.monthly_revenue?.toFixed(2) || '0.00'}
              </p>
            </div>
            <div style={{
              backgroundColor: '#fef3c7',
              padding: '0.75rem',
              borderRadius: '0.5rem'
            }}>
              <TrendingUp size={24} color="#f59e0b" />
            </div>
          </div>
        </div>

        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                Pending
              </p>
              <p style={{ fontSize: '2rem', fontWeight: 'bold', color: '#1e293b' }}>
                {overview?.pending_count || 0}
              </p>
            </div>
            <div style={{
              backgroundColor: '#fee2e2',
              padding: '0.75rem',
              borderRadius: '0.5rem'
            }}>
              <Clock size={24} color="#ef4444" />
            </div>
          </div>
        </div>
      </div>

      {/* Recent Invoices */}
      <div className="card">
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '1.5rem'
        }}>
          <h2 style={{ fontSize: '1.5rem', fontWeight: '600', color: '#1e293b' }}>
            Recent Invoices
          </h2>
          <Link to="/invoices" className="btn btn-outline">
            View All
          </Link>
        </div>

        {recent_invoices && recent_invoices.length > 0 ? (
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Invoice #</th>
                  <th>Customer</th>
                  <th>Date</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {recent_invoices.map((invoice) => (
                  <tr key={invoice.id}>
                    <td style={{ fontWeight: '500' }}>
                      {invoice.invoice_number}
                    </td>
                    <td>{invoice.customer_name}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <Calendar size={14} color="#6b7280" />
                        {format(new Date(invoice.issue_date), 'MMM dd, yyyy')}
                      </div>
                    </td>
                    <td style={{ fontWeight: '500' }}>
                      ${invoice.total_amount.toFixed(2)}
                    </td>
                    <td>
                      <span className={getStatusBadgeClass(invoice.status)}>
                        {invoice.status}
                      </span>
                    </td>
                    <td>
                      <Link
                        to={`/invoices/${invoice.id}`}
                        className="btn btn-outline"
                        style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }}
                      >
                        <Eye size={12} />
                        View
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{
            textAlign: 'center',
            padding: '3rem',
            color: '#6b7280'
          }}>
            <FileText size={48} color="#d1d5db" style={{ margin: '0 auto 1rem' }} />
            <p style={{ fontSize: '1.125rem', marginBottom: '0.5rem' }}>
              No invoices yet
            </p>
            <p style={{ marginBottom: '1.5rem' }}>
              Create your first invoice to get started
            </p>
            <Link to="/invoices/new" className="btn btn-primary">
              <Plus size={16} />
              Create Invoice
            </Link>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
