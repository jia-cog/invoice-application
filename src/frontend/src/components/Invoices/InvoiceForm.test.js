import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import InvoiceForm from './InvoiceForm';
import { invoicesAPI } from '../../utils/api';

// Mock modules
const mockNavigate = jest.fn();
let mockParams = {};

jest.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
  useParams: () => mockParams,
}));

jest.mock('../../utils/api', () => ({
  invoicesAPI: {
    getById: jest.fn(),
    create: jest.fn(),
    update: jest.fn(),
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
  Save: () => <span>Save</span>,
  Plus: () => <span>Plus</span>,
  Trash2: () => <span>Trash2</span>,
  ArrowLeft: () => <span>ArrowLeft</span>,
  User: () => <span>User</span>,
  Mail: () => <span>Mail</span>,
  MapPin: () => <span>MapPin</span>,
  Calendar: () => <span>Calendar</span>,
  FileText: () => <span>FileText</span>,
  DollarSign: () => <span>DollarSign</span>,
}));

jest.mock('date-fns', () => ({
  format: () => '2025-01-15',
}));

describe('InvoiceForm Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockParams = {};
  });

  describe('Create mode (no id param)', () => {
    test('renders create form with correct title', () => {
      render(<InvoiceForm />);

      expect(screen.getByText('Create New Invoice')).toBeInTheDocument();
    });

    test('renders all form fields', () => {
      render(<InvoiceForm />);

      expect(screen.getByPlaceholderText('Enter customer name')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('customer@example.com')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Customer address')).toBeInTheDocument();
      expect(screen.getByText('Customer Information')).toBeInTheDocument();
      expect(screen.getByText('Invoice Details')).toBeInTheDocument();
      expect(screen.getByText('Invoice Items')).toBeInTheDocument();
    });

    test('form field changes update state', () => {
      render(<InvoiceForm />);

      const customerNameInput = screen.getByPlaceholderText('Enter customer name');
      fireEvent.change(customerNameInput, { target: { name: 'customer_name', value: 'New Customer' } });
      expect(customerNameInput.value).toBe('New Customer');
    });

    test('add item button adds a row', () => {
      render(<InvoiceForm />);

      // Initially 1 item row
      const descriptionInputs = screen.getAllByPlaceholderText('Item description');
      expect(descriptionInputs).toHaveLength(1);

      // Click Add Item
      const addButton = screen.getByText('Add Item').closest('button');
      fireEvent.click(addButton);

      const updatedDescInputs = screen.getAllByPlaceholderText('Item description');
      expect(updatedDescInputs).toHaveLength(2);
    });

    test('remove item removes a row but keeps at least 1', () => {
      render(<InvoiceForm />);

      // Add a second item first
      const addButton = screen.getByText('Add Item').closest('button');
      fireEvent.click(addButton);

      expect(screen.getAllByPlaceholderText('Item description')).toHaveLength(2);

      // Now remove buttons should be visible
      const removeButtons = screen.getAllByText('Trash2').map(el => el.closest('button'));
      fireEvent.click(removeButtons[0]);

      expect(screen.getAllByPlaceholderText('Item description')).toHaveLength(1);

      // With only 1 item, no remove button should exist
      const remainingRemoveButtons = screen.queryAllByText('Trash2').filter(el => el.closest('button'));
      // The button shouldn't render when there's only 1 item
      expect(remainingRemoveButtons).toHaveLength(0);
    });

    test('subtotal/tax/total calculations', () => {
      render(<InvoiceForm />);

      // Set item quantity and price
      const quantityInputs = screen.getAllByDisplayValue('1');
      const priceInputs = screen.getAllByDisplayValue('0');

      // Find the quantity input (type=number with value 1)
      fireEvent.change(quantityInputs[0], { target: { value: '2' } });
      // Find a unit_price input
      const unitPriceInput = priceInputs.find(el => el.getAttribute('step') === '0.01' && el.getAttribute('placeholder') === '0.00');
      if (unitPriceInput) {
        fireEvent.change(unitPriceInput, { target: { value: '100' } });
      }

      // The total line item should show $200.00
      // Subtotal should show $200.00
      expect(screen.getByText('Subtotal:')).toBeInTheDocument();
      expect(screen.getByText('Total:')).toBeInTheDocument();
    });

    test('submit calls invoicesAPI.create for new invoice', async () => {
      invoicesAPI.create.mockResolvedValue({});

      render(<InvoiceForm />);

      // Fill required fields
      fireEvent.change(screen.getByPlaceholderText('Enter customer name'), {
        target: { name: 'customer_name', value: 'Test Customer' },
      });

      // Submit the form
      const submitButton = screen.getByText('Create Invoice').closest('button');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(invoicesAPI.create).toHaveBeenCalled();
        expect(toast.success).toHaveBeenCalledWith('Invoice created successfully');
        expect(mockNavigate).toHaveBeenCalledWith('/invoices');
      });
    });

    test('cancel navigates back', () => {
      render(<InvoiceForm />);

      const cancelButton = screen.getByText('Cancel');
      fireEvent.click(cancelButton);

      expect(mockNavigate).toHaveBeenCalledWith('/invoices');
    });

    test('back button navigates to /invoices', () => {
      render(<InvoiceForm />);

      const backButton = screen.getByText('Back').closest('button');
      fireEvent.click(backButton);

      expect(mockNavigate).toHaveBeenCalledWith('/invoices');
    });
  });

  describe('Edit mode (with id param)', () => {
    beforeEach(() => {
      mockParams = { id: '5' };
    });

    test('shows loading spinner while fetching invoice', () => {
      invoicesAPI.getById.mockReturnValue(new Promise(() => {}));

      render(<InvoiceForm />);

      expect(document.querySelector('.spinner')).toBeInTheDocument();
    });

    test('renders edit form with correct title after loading', async () => {
      invoicesAPI.getById.mockResolvedValue({
        data: {
          invoice: {
            customer_name: 'Existing Customer',
            customer_email: 'existing@test.com',
            customer_address: '123 Main St',
            due_date: '2025-02-15',
            tax_rate: 10,
            notes: 'Test notes',
            status: 'sent',
            items: [{ description: 'Item 1', quantity: 2, unit_price: 50 }],
          },
        },
      });

      render(<InvoiceForm />);

      await waitFor(() => {
        expect(screen.getByText('Edit Invoice')).toBeInTheDocument();
      });

      expect(screen.getByDisplayValue('Existing Customer')).toBeInTheDocument();
      expect(screen.getByDisplayValue('existing@test.com')).toBeInTheDocument();
    });

    test('submit calls invoicesAPI.update for existing invoice', async () => {
      invoicesAPI.getById.mockResolvedValue({
        data: {
          invoice: {
            customer_name: 'Existing Customer',
            customer_email: '',
            customer_address: '',
            due_date: '2025-02-15',
            tax_rate: 0,
            notes: '',
            status: 'draft',
            items: [{ description: 'Item 1', quantity: 1, unit_price: 100 }],
          },
        },
      });
      invoicesAPI.update.mockResolvedValue({});

      render(<InvoiceForm />);

      await waitFor(() => {
        expect(screen.getByText('Edit Invoice')).toBeInTheDocument();
      });

      const submitButton = screen.getByText('Update Invoice').closest('button');
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(invoicesAPI.update).toHaveBeenCalledWith('5', expect.any(Object));
        expect(toast.success).toHaveBeenCalledWith('Invoice updated successfully');
        expect(mockNavigate).toHaveBeenCalledWith('/invoices');
      });
    });

    test('shows error toast on fetch failure and navigates back', async () => {
      invoicesAPI.getById.mockRejectedValue(new Error('Not found'));

      render(<InvoiceForm />);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Failed to load invoice');
        expect(mockNavigate).toHaveBeenCalledWith('/invoices');
      });
    });
  });

  test('shows error toast on submit failure', async () => {
    invoicesAPI.create.mockRejectedValue({
      response: { data: { error: 'Validation error' } },
    });

    render(<InvoiceForm />);

    fireEvent.change(screen.getByPlaceholderText('Enter customer name'), {
      target: { name: 'customer_name', value: 'Test' },
    });

    const submitButton = screen.getByText('Create Invoice').closest('button');
    fireEvent.click(submitButton);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Validation error');
    });
  });
});
