import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Dashboard from './Dashboard';
import { reportsAPI } from '../../utils/api';

// Mock modules
jest.mock('../../utils/api', () => ({
  reportsAPI: {
    getDashboard: jest.fn(),
  },
}));

jest.mock('react-toastify', () => ({
  toast: {
    error: jest.fn(),
  },
}));

const { toast } = require('react-toastify');

jest.mock('react-router-dom', () => ({
  Link: ({ to, children, className, style }) => (
    <a href={to} className={className} style={style}>{children}</a>
  ),
}));

jest.mock('lucide-react', () => ({
  FileText: () => <span>FileText</span>,
  DollarSign: () => <span>DollarSign</span>,
  TrendingUp: () => <span>TrendingUp</span>,
  Clock: () => <span>Clock</span>,
  Plus: () => <span>Plus</span>,
  Eye: () => <span>Eye</span>,
  Calendar: () => <span>Calendar</span>,
}));

jest.mock('date-fns', () => ({
  format: (date, fmt) => '2025-01-15',
}));

const mockDashboardData = {
  overview: {
    total_invoices: 25,
    total_revenue: 15000.50,
    monthly_revenue: 3200.75,
    pending_count: 5,
  },
  recent_invoices: [
    {
      id: 1,
      invoice_number: 'INV-001',
      customer_name: 'Acme Corp',
      issue_date: '2025-01-15',
      total_amount: 1500.00,
      status: 'paid',
    },
    {
      id: 2,
      invoice_number: 'INV-002',
      customer_name: 'Tech Inc',
      issue_date: '2025-01-20',
      total_amount: 2500.00,
      status: 'sent',
    },
  ],
};

describe('Dashboard Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('shows loading spinner initially', () => {
    reportsAPI.getDashboard.mockReturnValue(new Promise(() => {})); // Never resolves

    render(<Dashboard />);

    expect(document.querySelector('.spinner')).toBeInTheDocument();
  });

  test('fetches and displays dashboard data', async () => {
    reportsAPI.getDashboard.mockResolvedValue({ data: mockDashboardData });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('Dashboard')).toBeInTheDocument();
    });

    expect(reportsAPI.getDashboard).toHaveBeenCalledTimes(1);
  });

  test('shows overview cards with correct values', async () => {
    reportsAPI.getDashboard.mockResolvedValue({ data: mockDashboardData });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('25')).toBeInTheDocument();
    });

    expect(screen.getByText('$15000.50')).toBeInTheDocument();
    expect(screen.getByText('$3200.75')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  test('shows recent invoices table', async () => {
    reportsAPI.getDashboard.mockResolvedValue({ data: mockDashboardData });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('Recent Invoices')).toBeInTheDocument();
    });

    expect(screen.getByText('INV-001')).toBeInTheDocument();
    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('$1500.00')).toBeInTheDocument();
    expect(screen.getByText('INV-002')).toBeInTheDocument();
    expect(screen.getByText('Tech Inc')).toBeInTheDocument();
  });

  test('shows empty state when no invoices', async () => {
    reportsAPI.getDashboard.mockResolvedValue({
      data: {
        overview: {
          total_invoices: 0,
          total_revenue: 0,
          monthly_revenue: 0,
          pending_count: 0,
        },
        recent_invoices: [],
      },
    });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('No invoices yet')).toBeInTheDocument();
    });

    expect(screen.getByText('Create your first invoice to get started')).toBeInTheDocument();
  });

  test('shows error toast on fetch failure', async () => {
    reportsAPI.getDashboard.mockRejectedValue(new Error('Network error'));

    render(<Dashboard />);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to load dashboard data');
    });
  });

  test('shows New Invoice link', async () => {
    reportsAPI.getDashboard.mockResolvedValue({ data: mockDashboardData });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('New Invoice')).toBeInTheDocument();
    });

    const newInvoiceLink = screen.getByText('New Invoice').closest('a');
    expect(newInvoiceLink).toHaveAttribute('href', '/invoices/new');
  });
});
