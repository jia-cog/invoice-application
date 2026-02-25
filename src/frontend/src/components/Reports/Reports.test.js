import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Reports from './Reports';
import { reportsAPI } from '../../utils/api';

// Mock modules
jest.mock('../../utils/api', () => ({
  reportsAPI: {
    getAll: jest.fn(),
    generate: jest.fn(),
    delete: jest.fn(),
  },
}));

jest.mock('react-toastify', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

const { toast } = require('react-toastify');

jest.mock('lucide-react', () => ({
  BarChart3: () => <span>BarChart3</span>,
  Calendar: () => <span>Calendar</span>,
  Download: () => <span>Download</span>,
  Plus: () => <span>Plus</span>,
  TrendingUp: () => <span>TrendingUp</span>,
  DollarSign: () => <span>DollarSign</span>,
  FileText: () => <span>FileText</span>,
  Users: () => <span>Users</span>,
}));

jest.mock('date-fns', () => ({
  format: (date, fmt) => {
    if (fmt === 'yyyy-MM-dd') {
      const d = new Date(date);
      return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    }
    return 'Jan 15, 2025';
  },
}));

// Mock recharts components
jest.mock('recharts', () => ({
  BarChart: ({ children }) => <div data-testid="bar-chart">{children}</div>,
  Bar: () => <div>Bar</div>,
  XAxis: () => <div>XAxis</div>,
  YAxis: () => <div>YAxis</div>,
  CartesianGrid: () => <div>CartesianGrid</div>,
  Tooltip: () => <div>Tooltip</div>,
  ResponsiveContainer: ({ children }) => <div data-testid="responsive-container">{children}</div>,
  PieChart: ({ children }) => <div data-testid="pie-chart">{children}</div>,
  Pie: () => <div>Pie</div>,
  Cell: () => <div>Cell</div>,
}));

const mockReports = [
  {
    id: 1,
    report_type: 'monthly',
    start_date: '2025-01-01',
    end_date: '2025-01-31',
    created_at: '2025-01-15T10:00:00Z',
    data: {
      summary: {
        total_invoices: 10,
        total_revenue: 5000.00,
        average_invoice_value: 500.00,
      },
      top_customers: [
        { name: 'Acme Corp', count: 5, revenue: 3000.00 },
        { name: 'Tech Inc', count: 3, revenue: 1500.00 },
      ],
      monthly_data: [
        { month: 'Jan', revenue: 5000 },
      ],
      status_breakdown: {
        paid: 5,
        sent: 3,
        draft: 2,
      },
    },
  },
  {
    id: 2,
    report_type: 'quarterly',
    start_date: '2025-01-01',
    end_date: '2025-03-31',
    created_at: '2025-03-31T10:00:00Z',
    data: null,
  },
];

describe('Reports Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('shows loading spinner initially', () => {
    reportsAPI.getAll.mockReturnValue(new Promise(() => {}));

    render(<Reports />);

    expect(document.querySelector('.spinner')).toBeInTheDocument();
  });

  test('fetches and displays reports list', async () => {
    reportsAPI.getAll.mockResolvedValue({ data: { reports: mockReports } });

    render(<Reports />);

    await waitFor(() => {
      expect(screen.getByText('Reports & Analytics')).toBeInTheDocument();
    });

    expect(screen.getByText('monthly Report')).toBeInTheDocument();
    expect(screen.getByText('quarterly Report')).toBeInTheDocument();
  });

  test('generate report form submits correctly', async () => {
    reportsAPI.getAll.mockResolvedValue({ data: { reports: [] } });
    reportsAPI.generate.mockResolvedValue({
      data: {
        report: mockReports[0],
      },
    });

    render(<Reports />);

    await waitFor(() => {
      expect(screen.getByText('Generate New Report')).toBeInTheDocument();
    });

    // Submit the generate form
    const generateButton = screen.getByText('Generate Report').closest('button');
    fireEvent.click(generateButton);

    await waitFor(() => {
      expect(reportsAPI.generate).toHaveBeenCalled();
      expect(toast.success).toHaveBeenCalledWith('Report generated successfully');
    });
  });

  test('shows empty state when no reports', async () => {
    reportsAPI.getAll.mockResolvedValue({ data: { reports: [] } });

    render(<Reports />);

    await waitFor(() => {
      expect(screen.getByText('No reports generated yet')).toBeInTheDocument();
    });
  });

  test('clicking a report shows its details', async () => {
    reportsAPI.getAll.mockResolvedValue({ data: { reports: mockReports } });

    render(<Reports />);

    await waitFor(() => {
      expect(screen.getByText('monthly Report')).toBeInTheDocument();
    });

    // Click the first report
    fireEvent.click(screen.getByText('monthly Report'));

    await waitFor(() => {
      // Should show report detail section with summary cards
      expect(screen.getByText('Total Invoices')).toBeInTheDocument();
      expect(screen.getByText('Total Revenue')).toBeInTheDocument();
      expect(screen.getByText('10')).toBeInTheDocument();
      expect(screen.getByText('$5000.00')).toBeInTheDocument();
    });
  });

  test('shows top customers table when report has data', async () => {
    reportsAPI.getAll.mockResolvedValue({ data: { reports: mockReports } });

    render(<Reports />);

    await waitFor(() => {
      expect(screen.getByText('monthly Report')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('monthly Report'));

    await waitFor(() => {
      expect(screen.getByText('Top Customers')).toBeInTheDocument();
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
      expect(screen.getByText('Tech Inc')).toBeInTheDocument();
      expect(screen.getByText('$3000.00')).toBeInTheDocument();
    });
  });

  test('shows error toast when generate fails', async () => {
    reportsAPI.getAll.mockResolvedValue({ data: { reports: [] } });
    reportsAPI.generate.mockRejectedValue(new Error('Server error'));

    render(<Reports />);

    await waitFor(() => {
      expect(screen.getByText('Generate New Report')).toBeInTheDocument();
    });

    const generateButton = screen.getByText('Generate Report').closest('button');
    fireEvent.click(generateButton);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to generate report');
    });
  });

  test('shows error toast on fetch failure', async () => {
    reportsAPI.getAll.mockRejectedValue(new Error('Network error'));

    render(<Reports />);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to load reports');
    });
  });

  test('report form has report type dropdown', async () => {
    reportsAPI.getAll.mockResolvedValue({ data: { reports: [] } });

    render(<Reports />);

    await waitFor(() => {
      expect(screen.getByText('Report Type')).toBeInTheDocument();
    });

    const reportTypeSelect = screen.getByDisplayValue('Monthly');
    expect(reportTypeSelect).toBeInTheDocument();

    fireEvent.change(reportTypeSelect, { target: { value: 'quarterly', name: 'report_type' } });
    expect(reportTypeSelect.value).toBe('quarterly');
  });
});
