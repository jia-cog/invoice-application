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
  Calendar,
  Activity
} from 'lucide-react';
import { format } from 'date-fns';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line } from 'recharts';

const Dashboard = () => {
  const [dashboardData, setDashboardData] = useState(null);
  const [usageData, setUsageData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
    fetchUsageData();
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

  const fetchUsageData = async () => {
    try {
      const response = await reportsAPI.getUsageAnalytics(60);
      setUsageData(response.data);
    } catch (error) {
      // Usage data is supplementary, don't block on failure
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
              backgroundColor: '#dbeafe',
              padding: '0.75rem',
              borderRadius: '0.5rem'
            }}>
              <FileText size={24} color="#3b82f6" />
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

      {/* Endpoint Usage Analytics */}
      {usageData && (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
          gap: '1.5rem',
          marginBottom: '2rem'
        }}>
          {/* Endpoint Hit Frequencies */}
          <div className="card">
            <h2 style={{
              fontSize: '1.25rem',
              fontWeight: '600',
              color: '#1e293b',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <Activity size={20} />
              Top Endpoints
            </h2>
            {usageData.endpoint_stats && usageData.endpoint_stats.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={usageData.endpoint_stats.slice(0, 8)} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis dataKey="endpoint" type="category" width={150} tick={{ fontSize: 12 }} />
                  <Tooltip formatter={(value) => [value, 'Hits']} />
                  <Bar dataKey="hit_count" fill="#3b82f6" />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                <Activity size={36} color="#d1d5db" style={{ margin: '0 auto 0.5rem' }} />
                <p>No endpoint data yet</p>
              </div>
            )}
          </div>

          {/* Daily Request Trends */}
          <div className="card">
            <h2 style={{
              fontSize: '1.25rem',
              fontWeight: '600',
              color: '#1e293b',
              marginBottom: '1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem'
            }}>
              <TrendingUp size={20} />
              Daily Request Trends
            </h2>
            {usageData.daily_trends && usageData.daily_trends.length > 0 ? (
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={usageData.daily_trends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="hit_count" stroke="#10b981" strokeWidth={2} name="Requests" />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                <TrendingUp size={36} color="#d1d5db" style={{ margin: '0 auto 0.5rem' }} />
                <p>No trend data yet</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Usage Summary Bar */}
      {usageData && usageData.summary && usageData.summary.total_requests > 0 && (
        <div className="card" style={{ marginBottom: '2rem' }}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-around',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '1rem'
          }}>
            <div style={{ textAlign: 'center' }}>
              <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>Total Requests</p>
              <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#1e293b' }}>
                {usageData.summary.total_requests}
              </p>
            </div>
            <div style={{ textAlign: 'center' }}>
              <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>Error Requests</p>
              <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#ef4444' }}>
                {usageData.summary.error_requests}
              </p>
            </div>
            <div style={{ textAlign: 'center' }}>
              <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>Error Rate</p>
              <p style={{
                fontSize: '1.5rem',
                fontWeight: 'bold',
                color: usageData.summary.error_rate > 10 ? '#ef4444' : '#10b981'
              }}>
                {usageData.summary.error_rate}%
              </p>
            </div>
            <div style={{ textAlign: 'center' }}>
              <p style={{ color: '#6b7280', fontSize: '0.875rem' }}>Period</p>
              <p style={{ fontSize: '1.5rem', fontWeight: 'bold', color: '#1e293b' }}>
                {usageData.summary.period_days} days
              </p>
            </div>
          </div>
        </div>
      )}

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
