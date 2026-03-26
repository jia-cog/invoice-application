import React, { useState, useEffect } from 'react';
import { exportsAPI } from '../../utils/api';
import { toast } from 'react-toastify';
import { format } from 'date-fns';
import { Download, FileText, DollarSign, TrendingUp, BarChart3 } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar, Doughnut } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend
);

const InvoiceExport = () => {
  const [exportData, setExportData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchExportData();
  }, []);

  const fetchExportData = async () => {
    try {
      const response = await exportsAPI.getExportData();
      setExportData(response.data);
    } catch (error) {
      toast.error('Failed to load export data');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadCSV = async () => {
    try {
      const response = await exportsAPI.downloadCSV();
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      const contentDisposition = response.headers['content-disposition'];
      const filename = contentDisposition
        ? contentDisposition.split('filename=')[1]
        : 'invoices_export.csv';
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      toast.success('CSV downloaded successfully');
    } catch (error) {
      toast.error('Failed to download CSV');
    }
  };

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  const { date_range, summary, status_breakdown, daily_totals } = exportData || {};

  const formattedStart = date_range
    ? format(new Date(date_range.start_date + 'T00:00:00'), 'MMMM d, yyyy')
    : '';
  const formattedEnd = date_range
    ? format(new Date(date_range.end_date + 'T00:00:00'), 'MMMM d, yyyy')
    : '';

  // Bar chart data: daily totals
  const barChartData = {
    labels: (daily_totals || []).map((d) =>
      format(new Date(d.date + 'T00:00:00'), 'MMM d')
    ),
    datasets: [
      {
        label: 'Daily Total ($)',
        data: (daily_totals || []).map((d) => d.total_amount),
        backgroundColor: 'rgba(59, 130, 246, 0.7)',
        borderColor: '#3b82f6',
        borderWidth: 1,
        borderRadius: 4,
      },
    ],
  };

  const barChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'top' },
      title: { display: true, text: 'Daily Invoice Totals', font: { size: 16 } },
    },
    scales: {
      y: {
        beginAtZero: true,
        ticks: {
          callback: (value) => '$' + value.toLocaleString(),
        },
      },
    },
  };

  // Doughnut chart data: status breakdown
  const statusLabels = ['Draft', 'Sent', 'Paid', 'Overdue'];
  const statusColors = ['#6b7280', '#3b82f6', '#10b981', '#ef4444'];

  const doughnutData = {
    labels: statusLabels,
    datasets: [
      {
        data: status_breakdown
          ? [status_breakdown.draft, status_breakdown.sent, status_breakdown.paid, status_breakdown.overdue]
          : [0, 0, 0, 0],
        backgroundColor: statusColors,
        borderWidth: 2,
        borderColor: '#ffffff',
      },
    ],
  };

  const doughnutOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'bottom' },
      title: { display: true, text: 'Invoices by Status', font: { size: 16 } },
    },
  };

  return (
    <div className="container" style={{ paddingTop: '2rem', paddingBottom: '2rem' }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '2rem'
      }}>
        <div>
          <h1 style={{ fontSize: '2rem', fontWeight: 'bold', color: '#1e293b', marginBottom: '0.5rem' }}>
            Monthly Export &amp; Reports
          </h1>
          {date_range && (
            <p style={{ color: '#6b7280', fontSize: '1rem' }}>
              Invoices from {formattedStart} &ndash; {formattedEnd}
            </p>
          )}
        </div>
        <button onClick={handleDownloadCSV} className="btn btn-primary">
          <Download size={16} />
          Download CSV
        </button>
      </div>

      {/* Summary Cards */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
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
                {summary?.total_count || 0}
              </p>
            </div>
            <div style={{ backgroundColor: '#dbeafe', padding: '0.75rem', borderRadius: '0.5rem' }}>
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
                ${summary?.total_revenue?.toFixed(2) || '0.00'}
              </p>
            </div>
            <div style={{ backgroundColor: '#d1fae5', padding: '0.75rem', borderRadius: '0.5rem' }}>
              <DollarSign size={24} color="#10b981" />
            </div>
          </div>
        </div>

        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                Average Invoice
              </p>
              <p style={{ fontSize: '2rem', fontWeight: 'bold', color: '#1e293b' }}>
                ${summary?.average_amount?.toFixed(2) || '0.00'}
              </p>
            </div>
            <div style={{ backgroundColor: '#fef3c7', padding: '0.75rem', borderRadius: '0.5rem' }}>
              <TrendingUp size={24} color="#f59e0b" />
            </div>
          </div>
        </div>

        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <p style={{ color: '#6b7280', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
                Status Breakdown
              </p>
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', marginTop: '0.25rem' }}>
                <span className="status-badge status-draft">{status_breakdown?.draft || 0} Draft</span>
                <span className="status-badge status-sent">{status_breakdown?.sent || 0} Sent</span>
                <span className="status-badge status-paid">{status_breakdown?.paid || 0} Paid</span>
                <span className="status-badge status-overdue">{status_breakdown?.overdue || 0} Overdue</span>
              </div>
            </div>
            <div style={{ backgroundColor: '#ede9fe', padding: '0.75rem', borderRadius: '0.5rem' }}>
              <BarChart3 size={24} color="#8b5cf6" />
            </div>
          </div>
        </div>
      </div>

      {/* Charts */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '2fr 1fr',
        gap: '1.5rem',
        marginBottom: '2rem'
      }}>
        {/* Bar Chart */}
        <div className="card">
          <div style={{ height: '400px' }}>
            <Bar data={barChartData} options={barChartOptions} />
          </div>
        </div>

        {/* Doughnut Chart */}
        <div className="card">
          <div style={{ height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Doughnut data={doughnutData} options={doughnutOptions} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default InvoiceExport;
