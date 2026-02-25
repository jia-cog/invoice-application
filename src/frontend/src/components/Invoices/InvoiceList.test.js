import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import InvoiceList from './InvoiceList';
import { invoicesAPI } from '../../utils/api';

// Mock modules
jest.mock('../../utils/api', () => ({
  invoicesAPI: {
    getAll: jest.fn(),
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

jest.mock('react-router-dom', () => ({
  Link: ({ to, children, className, style }) => (
    <a href={to} className={className} style={style}>{children}</a>
  ),
}));

jest.mock('lucide-react', () => ({
  Plus: () => <span>Plus</span>,
  Eye: () => <span>Eye</span>,
  Edit: () => <span>Edit</span>,
  Trash2: () => <span>Trash2</span>,
  Calendar: () => <span>Calendar</span>,
  Search: () => <span>Search</span>,
  Filter: () => <span>Filter</span>,
}));

jest.mock('date-fns', () => ({
  format: () => 'Jan 15, 2025',
}));

const mockInvoices = [
  {
    id: 1,
    invoice_number: 'INV-001',
    customer_name: 'Acme Corp',
    customer_email: 'acme@example.com',
    issue_date: '2025-01-15',
    due_date: '2025-02-15',
    total_amount: 1500.00,
    status: 'paid',
  },
  {
    id: 2,
    invoice_number: 'INV-002',
    customer_name: 'Tech Inc',
    customer_email: 'tech@example.com',
    issue_date: '2025-01-20',
    due_date: '2025-02-20',
    total_amount: 2500.00,
    status: 'draft',
  },
  {
    id: 3,
    invoice_number: 'INV-003',
    customer_name: 'Beta LLC',
    customer_email: '',
    issue_date: '2025-01-25',
    due_date: '2025-02-25',
    total_amount: 800.00,
    status: 'sent',
  },
];

describe('InvoiceList Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('shows loading spinner initially', () => {
    invoicesAPI.getAll.mockReturnValue(new Promise(() => {})); // Never resolves

    render(<InvoiceList />);

    expect(document.querySelector('.spinner')).toBeInTheDocument();
  });

  test('fetches and displays invoices', async () => {
    invoicesAPI.getAll.mockResolvedValue({ data: { invoices: mockInvoices } });

    render(<InvoiceList />);

    await waitFor(() => {
      expect(screen.getByText('INV-001')).toBeInTheDocument();
    });

    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.getByText('Tech Inc')).toBeInTheDocument();
    expect(screen.getByText('Beta LLC')).toBeInTheDocument();
    expect(screen.getByText('$1500.00')).toBeInTheDocument();
    expect(screen.getByText('$2500.00')).toBeInTheDocument();
  });

  test('search filters by customer name', async () => {
    invoicesAPI.getAll.mockResolvedValue({ data: { invoices: mockInvoices } });

    render(<InvoiceList />);

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search by customer or invoice number...');
    fireEvent.change(searchInput, { target: { value: 'Acme' } });

    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.queryByText('Tech Inc')).not.toBeInTheDocument();
    expect(screen.queryByText('Beta LLC')).not.toBeInTheDocument();
  });

  test('search filters by invoice number', async () => {
    invoicesAPI.getAll.mockResolvedValue({ data: { invoices: mockInvoices } });

    render(<InvoiceList />);

    await waitFor(() => {
      expect(screen.getByText('INV-001')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search by customer or invoice number...');
    fireEvent.change(searchInput, { target: { value: 'INV-002' } });

    expect(screen.queryByText('Acme Corp')).not.toBeInTheDocument();
    expect(screen.getByText('Tech Inc')).toBeInTheDocument();
  });

  test('status filter works', async () => {
    invoicesAPI.getAll.mockResolvedValue({ data: { invoices: mockInvoices } });

    render(<InvoiceList />);

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });

    const statusSelect = screen.getByDisplayValue('All Statuses');
    fireEvent.change(statusSelect, { target: { value: 'paid' } });

    expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    expect(screen.queryByText('Tech Inc')).not.toBeInTheDocument();
    expect(screen.queryByText('Beta LLC')).not.toBeInTheDocument();
  });

  test('delete with confirmation dialog', async () => {
    invoicesAPI.getAll.mockResolvedValue({ data: { invoices: mockInvoices } });
    invoicesAPI.delete.mockResolvedValue({});
    window.confirm = jest.fn().mockReturnValue(true);

    render(<InvoiceList />);

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });

    // Find delete buttons (btn-danger class)
    const deleteButtons = screen.getAllByText('Trash2').map(el => el.closest('button'));
    fireEvent.click(deleteButtons[0]);

    expect(window.confirm).toHaveBeenCalledWith('Are you sure you want to delete this invoice?');
    await waitFor(() => {
      expect(invoicesAPI.delete).toHaveBeenCalledWith(1);
      expect(toast.success).toHaveBeenCalledWith('Invoice deleted successfully');
    });
  });

  test('delete cancelled when user declines confirmation', async () => {
    invoicesAPI.getAll.mockResolvedValue({ data: { invoices: mockInvoices } });
    window.confirm = jest.fn().mockReturnValue(false);

    render(<InvoiceList />);

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });

    const deleteButtons = screen.getAllByText('Trash2').map(el => el.closest('button'));
    fireEvent.click(deleteButtons[0]);

    expect(window.confirm).toHaveBeenCalled();
    expect(invoicesAPI.delete).not.toHaveBeenCalled();
  });

  test('shows empty state when no invoices', async () => {
    invoicesAPI.getAll.mockResolvedValue({ data: { invoices: [] } });

    render(<InvoiceList />);

    await waitFor(() => {
      expect(screen.getByText('No invoices yet')).toBeInTheDocument();
    });

    expect(screen.getByText('Create your first invoice to get started')).toBeInTheDocument();
  });

  test('shows "No invoices found" when search has no results', async () => {
    invoicesAPI.getAll.mockResolvedValue({ data: { invoices: mockInvoices } });

    render(<InvoiceList />);

    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText('Search by customer or invoice number...');
    fireEvent.change(searchInput, { target: { value: 'nonexistent' } });

    expect(screen.getByText('No invoices found')).toBeInTheDocument();
    expect(screen.getByText('Try adjusting your search or filter criteria')).toBeInTheDocument();
  });

  test('shows error toast on fetch failure', async () => {
    invoicesAPI.getAll.mockRejectedValue(new Error('Network error'));

    render(<InvoiceList />);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Failed to load invoices');
    });
  });
});
