import React, { useState, useEffect } from 'react';
import { reportsAPI } from '../../utils/api';
import { toast } from 'react-toastify';
import { 
  BarChart3, 
  Calendar, 
  Download, 
  Plus,
  TrendingUp,
  DollarSign,
  FileText,
  Users,
  AlertTriangle
} from 'lucide-react';
import { format } from 'date-fns';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, LineChart, Line } from 'recharts';

const Reports = () => {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [selectedReport, setSelectedReport] = useState(null);
  const [qualityMetrics, setQualityMetrics] = useState(null);
  const [reportForm, setReportForm] = useState({
    report_type: 'monthly',
    start_date: '',
    end_date: ''
  });

  useEffect(() => {
    fetchReports();
    fetchQualityMetrics();
    setDefaultDates();
  }, []);

  const setDefaultDates = () => {
    const today = new Date();
    const firstDayOfMonth = new Date(today.getFullYear(), today.getMonth(), 1);
    const lastDayOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0);

    setReportForm(prev => ({
      ...prev,
      start_date: format(firstDayOfMonth, 'yyyy-MM-dd'),
      end_date: format(lastDayOfMonth, 'yyyy-MM-dd')
    }));
  };

  const fetchReports = async () => {
    try {
      const response = await reportsAPI.getAll();
      setReports(response.data.reports);
    } catch (error) {
      toast.error('Failed to load reports');
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateReport = async (e) => {
    e.preventDefault();
    setGenerating(true);

    try {
      const response = await reportsAPI.generate(reportForm);
      toast.success('Report generated successfully');
      setSelectedReport(response.data.report);
      fetchReports();
    } catch (error) {
      toast.error('Failed to generate report');
    } finally {
      setGenerating(false);
    }
  };

  const fetchQualityMetrics = async () => {
    try {
      const response = await reportsAPI.getQualityMetrics(60);
      setQualityMetrics(response.data);
    } catch (error) {
      // Quality metrics are supplementary
    }
  };

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setReportForm(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444'];
  const QUALITY_COLORS = ['#ef4444', '#f59e0b', '#3b82f6', '#10b981'];

  if (loading) {
    return (
      <div className="loading">
        <div className="spinner"></div>
      </div>
    );
  }

  return (
    <div className="container" style={{ paddingTop: '2rem', paddingBottom: '2rem' }}>
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '2rem'
      }}>
        <h1 style={{ fontSize: '2rem', fontWeight: 'bold', color: '#1e293b' }}>
          Reports & Analytics
        </h1>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
        gap: '2rem',
        marginBottom: '2rem'
      }}>
        {/* Generate Report Form */}
        <div className="card">
          <h3 style={{
            fontSize: '1.25rem',
            fontWeight: '600',
            color: '#1e293b',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <Plus size={20} />
            Generate New Report
          </h3>

          <form onSubmit={handleGenerateReport}>
            <div className="form-group">
              <label className="form-label">Report Type</label>
              <select
                name="report_type"
                value={reportForm.report_type}
                onChange={handleFormChange}
                className="form-input"
                required
              >
                <option value="monthly">Monthly</option>
                <option value="quarterly">Quarterly</option>
                <option value="yearly">Yearly</option>
                <option value="custom">Custom Range</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">
                <Calendar size={16} style={{ display: 'inline', marginRight: '0.5rem' }} />
                Start Date
              </label>
              <input
                type="date"
                name="start_date"
                value={reportForm.start_date}
                onChange={handleFormChange}
                className="form-input"
                required
              />
            </div>

            <div className="form-group">
              <label className="form-label">
                <Calendar size={16} style={{ display: 'inline', marginRight: '0.5rem' }} />
                End Date
              </label>
              <input
                type="date"
                name="end_date"
                value={reportForm.end_date}
                onChange={handleFormChange}
                className="form-input"
                required
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={generating}
              style={{ width: '100%' }}
            >
              {generating ? (
                <div className="spinner" style={{ width: '1rem', height: '1rem' }} />
              ) : (
                <>
                  <BarChart3 size={16} />
                  Generate Report
                </>
              )}
            </button>
          </form>
        </div>

        {/* Recent Reports */}
        <div className="card">
          <h3 style={{
            fontSize: '1.25rem',
            fontWeight: '600',
            color: '#1e293b',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <FileText size={20} />
            Recent Reports
          </h3>

          {reports.length > 0 ? (
            <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
              {reports.slice(0, 5).map((report) => (
                <div
                  key={report.id}
                  style={{
                    padding: '1rem',
                    border: '1px solid #e5e7eb',
                    borderRadius: '0.375rem',
                    marginBottom: '0.5rem',
                    cursor: 'pointer',
                    transition: 'all 0.2s'
                  }}
                  onClick={() => setSelectedReport(report)}
                  onMouseEnter={(e) => {
                    e.target.style.backgroundColor = '#f9fafb';
                  }}
                  onMouseLeave={(e) => {
                    e.target.style.backgroundColor = 'transparent';
                  }}
                >
                  <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '0.5rem'
                  }}>
                    <span style={{ fontWeight: '500', textTransform: 'capitalize' }}>
                      {report.report_type} Report
                    </span>
                    <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                      {format(new Date(report.created_at), 'MMM dd, yyyy')}
                    </span>
                  </div>
                  <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                    {format(new Date(report.start_date), 'MMM dd')} - {format(new Date(report.end_date), 'MMM dd, yyyy')}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={{
              textAlign: 'center',
              padding: '2rem',
              color: '#6b7280'
            }}>
              <BarChart3 size={48} color="#d1d5db" style={{ margin: '0 auto 1rem' }} />
              <p>No reports generated yet</p>
            </div>
          )}
        </div>
      </div>

      {/* Quality Metrics Section */}
      {qualityMetrics && qualityMetrics.total_invoices > 0 && (
        <div className="card" style={{ marginBottom: '2rem' }}>
          <h3 style={{
            fontSize: '1.5rem',
            fontWeight: '600',
            color: '#1e293b',
            marginBottom: '1.5rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem'
          }}>
            <AlertTriangle size={24} />
            Invoice Quality Metrics (Last {qualityMetrics.days} Days)
          </h3>

          {/* Quality Rate Cards */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
            gap: '1rem',
            marginBottom: '2rem'
          }}>
            <div style={{
              padding: '1.25rem',
              borderRadius: '0.5rem',
              border: '1px solid #fecaca',
              backgroundColor: '#fef2f2'
            }}>
              <p style={{ color: '#991b1b', fontSize: '0.8125rem', marginBottom: '0.25rem' }}>Overdue Rate</p>
              <p style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#dc2626' }}>
                {qualityMetrics.overdue_rate}%
              </p>
            </div>

            <div style={{
              padding: '1.25rem',
              borderRadius: '0.5rem',
              border: '1px solid #fed7aa',
              backgroundColor: '#fff7ed'
            }}>
              <p style={{ color: '#9a3412', fontSize: '0.8125rem', marginBottom: '0.25rem' }}>Draft-Stuck Rate</p>
              <p style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#ea580c' }}>
                {qualityMetrics.draft_stuck_rate}%
              </p>
            </div>

            <div style={{
              padding: '1.25rem',
              borderRadius: '0.5rem',
              border: '1px solid #bbf7d0',
              backgroundColor: '#f0fdf4'
            }}>
              <p style={{ color: '#166534', fontSize: '0.8125rem', marginBottom: '0.25rem' }}>Conversion Rate</p>
              <p style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#16a34a' }}>
                {qualityMetrics.draft_to_paid_rate}%
              </p>
            </div>

            <div style={{
              padding: '1.25rem',
              borderRadius: '0.5rem',
              border: '1px solid #e5e7eb',
              backgroundColor: '#f9fafb'
            }}>
              <p style={{ color: '#374151', fontSize: '0.8125rem', marginBottom: '0.25rem' }}>Total Invoices</p>
              <p style={{ fontSize: '1.75rem', fontWeight: 'bold', color: '#1e293b' }}>
                {qualityMetrics.total_invoices}
              </p>
            </div>
          </div>

          {/* Charts Row */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))',
            gap: '2rem',
            marginBottom: '2rem'
          }}>
            {/* Missing Fields Chart */}
            <div>
              <h4 style={{
                fontSize: '1.125rem',
                fontWeight: '600',
                color: '#1e293b',
                marginBottom: '1rem'
              }}>
                Missing Field Rates
              </h4>
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={[
                  { name: 'Email', rate: qualityMetrics.missing_email_rate },
                  { name: 'Address', rate: qualityMetrics.missing_address_rate },
                  { name: 'Notes', rate: qualityMetrics.missing_notes_rate }
                ]}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" />
                  <YAxis unit="%" />
                  <Tooltip formatter={(value) => [`${value}%`, 'Missing Rate']} />
                  <Bar dataKey="rate" fill="#f59e0b" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Status Breakdown Pie */}
            <div>
              <h4 style={{
                fontSize: '1.125rem',
                fontWeight: '600',
                color: '#1e293b',
                marginBottom: '1rem'
              }}>
                Status Breakdown
              </h4>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={Object.entries(qualityMetrics.status_breakdown).map(([key, value]) => ({
                      name: key.charAt(0).toUpperCase() + key.slice(1),
                      value
                    }))}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => percent > 0 ? `${name} ${(percent * 100).toFixed(0)}%` : ''}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {Object.entries(qualityMetrics.status_breakdown).map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={QUALITY_COLORS[index % QUALITY_COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Invoice Generation Trends */}
          {qualityMetrics.daily_trends && qualityMetrics.daily_trends.length > 0 && (
            <div>
              <h4 style={{
                fontSize: '1.125rem',
                fontWeight: '600',
                color: '#1e293b',
                marginBottom: '1rem'
              }}>
                Invoice Generation Trends
              </h4>
              <ResponsiveContainer width="100%" height={250}>
                <LineChart data={qualityMetrics.daily_trends}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 12 }}
                    tickFormatter={(val) => {
                      const d = new Date(val + 'T00:00:00');
                      return format(d, 'MM/dd');
                    }}
                  />
                  <YAxis yAxisId="left" />
                  <YAxis yAxisId="right" orientation="right" />
                  <Tooltip
                    labelFormatter={(val) => {
                      const d = new Date(val + 'T00:00:00');
                      return format(d, 'MMM dd, yyyy');
                    }}
                  />
                  <Line yAxisId="left" type="monotone" dataKey="count" stroke="#3b82f6" name="Invoices Created" strokeWidth={2} />
                  <Line yAxisId="right" type="monotone" dataKey="total_amount" stroke="#10b981" name="Total Amount ($)" strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* Report Details */}
      {selectedReport && (
        <div className="card">
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '2rem'
          }}>
            <h3 style={{
              fontSize: '1.5rem',
              fontWeight: '600',
              color: '#1e293b',
              textTransform: 'capitalize'
            }}>
              {selectedReport.report_type} Report
            </h3>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <span style={{ color: '#6b7280' }}>
                {format(new Date(selectedReport.start_date), 'MMM dd')} - {format(new Date(selectedReport.end_date), 'MMM dd, yyyy')}
              </span>
              <button className="btn btn-outline">
                <Download size={16} />
                Export
              </button>
            </div>
          </div>

          {selectedReport.data && (
            <>
              {/* Summary Cards */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                gap: '1rem',
                marginBottom: '2rem'
              }}>
                <div style={{
                  background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)',
                  color: 'white',
                  padding: '1.5rem',
                  borderRadius: '0.5rem'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <FileText size={20} />
                    <span style={{ fontSize: '0.875rem', opacity: 0.9 }}>Total Invoices</span>
                  </div>
                  <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>
                    {selectedReport.data.summary?.total_invoices || 0}
                  </div>
                </div>

                <div style={{
                  background: 'linear-gradient(135deg, #10b981, #059669)',
                  color: 'white',
                  padding: '1.5rem',
                  borderRadius: '0.5rem'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <DollarSign size={20} />
                    <span style={{ fontSize: '0.875rem', opacity: 0.9 }}>Total Revenue</span>
                  </div>
                  <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>
                    ${selectedReport.data.summary?.total_revenue?.toFixed(2) || '0.00'}
                  </div>
                </div>

                <div style={{
                  background: 'linear-gradient(135deg, #f59e0b, #d97706)',
                  color: 'white',
                  padding: '1.5rem',
                  borderRadius: '0.5rem'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <TrendingUp size={20} />
                    <span style={{ fontSize: '0.875rem', opacity: 0.9 }}>Avg Invoice</span>
                  </div>
                  <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>
                    ${selectedReport.data.summary?.average_invoice_value?.toFixed(2) || '0.00'}
                  </div>
                </div>

                <div style={{
                  background: 'linear-gradient(135deg, #8b5cf6, #7c3aed)',
                  color: 'white',
                  padding: '1.5rem',
                  borderRadius: '0.5rem'
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <Users size={20} />
                    <span style={{ fontSize: '0.875rem', opacity: 0.9 }}>Customers</span>
                  </div>
                  <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>
                    {selectedReport.data.top_customers?.length || 0}
                  </div>
                </div>
              </div>

              {/* Charts */}
              <div style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
                gap: '2rem',
                marginBottom: '2rem'
              }}>
                {/* Monthly Revenue Chart */}
                {selectedReport.data.monthly_data && selectedReport.data.monthly_data.length > 0 && (
                  <div>
                    <h4 style={{
                      fontSize: '1.125rem',
                      fontWeight: '600',
                      color: '#1e293b',
                      marginBottom: '1rem'
                    }}>
                      Monthly Revenue
                    </h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <BarChart data={selectedReport.data.monthly_data}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="month" />
                        <YAxis />
                        <Tooltip formatter={(value) => [`$${value.toFixed(2)}`, 'Revenue']} />
                        <Bar dataKey="revenue" fill="#3b82f6" />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                )}

                {/* Status Distribution Chart */}
                {selectedReport.data.status_breakdown && (
                  <div>
                    <h4 style={{
                      fontSize: '1.125rem',
                      fontWeight: '600',
                      color: '#1e293b',
                      marginBottom: '1rem'
                    }}>
                      Invoice Status Distribution
                    </h4>
                    <ResponsiveContainer width="100%" height={300}>
                      <PieChart>
                        <Pie
                          data={Object.entries(selectedReport.data.status_breakdown).map(([key, value]) => ({
                            name: key.charAt(0).toUpperCase() + key.slice(1),
                            value
                          }))}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                          outerRadius={80}
                          fill="#8884d8"
                          dataKey="value"
                        >
                          {Object.entries(selectedReport.data.status_breakdown).map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                )}
              </div>

              {/* Top Customers */}
              {selectedReport.data.top_customers && selectedReport.data.top_customers.length > 0 && (
                <div>
                  <h4 style={{
                    fontSize: '1.125rem',
                    fontWeight: '600',
                    color: '#1e293b',
                    marginBottom: '1rem'
                  }}>
                    Top Customers
                  </h4>
                  <div style={{ overflowX: 'auto' }}>
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Customer</th>
                          <th>Invoices</th>
                          <th>Revenue</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedReport.data.top_customers.map((customer, index) => (
                          <tr key={index}>
                            <td style={{ fontWeight: '500' }}>{customer.name}</td>
                            <td>{customer.count}</td>
                            <td style={{ fontWeight: '500' }}>${customer.revenue.toFixed(2)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
};

export default Reports;
