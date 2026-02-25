import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import Register from './Register';

// Mock modules
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>,
}));

const mockRegister = jest.fn();
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    register: mockRegister,
  }),
}));

jest.mock('react-toastify', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

const { toast } = require('react-toastify');

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  UserPlus: () => <span>UserPlus</span>,
  User: () => <span>User</span>,
  Mail: () => <span>Mail</span>,
  Lock: () => <span>Lock</span>,
  Building: () => <span>Building</span>,
}));

describe('Register Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders all form fields', () => {
    render(<Register />);

    expect(screen.getByPlaceholderText('Choose a username')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter your email')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Your company name')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Create a password')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Confirm your password')).toBeInTheDocument();
  });

  test('renders Create Account heading', () => {
    render(<Register />);

    expect(screen.getByRole('heading', { name: 'Create Account' })).toBeInTheDocument();
  });

  test('shows error toast when passwords do not match', async () => {
    render(<Register />);

    fireEvent.change(screen.getByPlaceholderText('Choose a username'), {
      target: { name: 'username', value: 'testuser' },
    });
    fireEvent.change(screen.getByPlaceholderText('Enter your email'), {
      target: { name: 'email', value: 'test@test.com' },
    });
    fireEvent.change(screen.getByPlaceholderText('Create a password'), {
      target: { name: 'password', value: 'password123' },
    });
    fireEvent.change(screen.getByPlaceholderText('Confirm your password'), {
      target: { name: 'confirmPassword', value: 'different' },
    });

    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Passwords do not match');
    });

    expect(mockRegister).not.toHaveBeenCalled();
  });

  test('shows error toast when password is less than 6 characters', async () => {
    render(<Register />);

    fireEvent.change(screen.getByPlaceholderText('Choose a username'), {
      target: { name: 'username', value: 'testuser' },
    });
    fireEvent.change(screen.getByPlaceholderText('Enter your email'), {
      target: { name: 'email', value: 'test@test.com' },
    });
    fireEvent.change(screen.getByPlaceholderText('Create a password'), {
      target: { name: 'password', value: '12345' },
    });
    fireEvent.change(screen.getByPlaceholderText('Confirm your password'), {
      target: { name: 'confirmPassword', value: '12345' },
    });

    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Password must be at least 6 characters long');
    });

    expect(mockRegister).not.toHaveBeenCalled();
  });

  test('calls register with form data (excluding confirmPassword) on valid submit', async () => {
    mockRegister.mockResolvedValue({ success: true });

    render(<Register />);

    fireEvent.change(screen.getByPlaceholderText('Choose a username'), {
      target: { name: 'username', value: 'newuser' },
    });
    fireEvent.change(screen.getByPlaceholderText('Enter your email'), {
      target: { name: 'email', value: 'new@test.com' },
    });
    fireEvent.change(screen.getByPlaceholderText('Your company name'), {
      target: { name: 'company_name', value: 'Test Corp' },
    });
    fireEvent.change(screen.getByPlaceholderText('Create a password'), {
      target: { name: 'password', value: 'password123' },
    });
    fireEvent.change(screen.getByPlaceholderText('Confirm your password'), {
      target: { name: 'confirmPassword', value: 'password123' },
    });

    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith({
        username: 'newuser',
        email: 'new@test.com',
        password: 'password123',
        company_name: 'Test Corp',
      });
    });
  });

  test('shows success toast and navigates on success', async () => {
    mockRegister.mockResolvedValue({ success: true });

    render(<Register />);

    fireEvent.change(screen.getByPlaceholderText('Choose a username'), {
      target: { name: 'username', value: 'newuser' },
    });
    fireEvent.change(screen.getByPlaceholderText('Enter your email'), {
      target: { name: 'email', value: 'new@test.com' },
    });
    fireEvent.change(screen.getByPlaceholderText('Create a password'), {
      target: { name: 'password', value: 'password123' },
    });
    fireEvent.change(screen.getByPlaceholderText('Confirm your password'), {
      target: { name: 'confirmPassword', value: 'password123' },
    });

    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Account created successfully!');
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });
  });

  test('shows error toast on registration failure', async () => {
    mockRegister.mockResolvedValue({ success: false, error: 'Username already taken' });

    render(<Register />);

    fireEvent.change(screen.getByPlaceholderText('Choose a username'), {
      target: { name: 'username', value: 'taken' },
    });
    fireEvent.change(screen.getByPlaceholderText('Enter your email'), {
      target: { name: 'email', value: 'taken@test.com' },
    });
    fireEvent.change(screen.getByPlaceholderText('Create a password'), {
      target: { name: 'password', value: 'password123' },
    });
    fireEvent.change(screen.getByPlaceholderText('Confirm your password'), {
      target: { name: 'confirmPassword', value: 'password123' },
    });

    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Username already taken');
    });
  });

  test('shows error toast when register throws an exception', async () => {
    mockRegister.mockRejectedValue(new Error('Network error'));

    render(<Register />);

    fireEvent.change(screen.getByPlaceholderText('Choose a username'), {
      target: { name: 'username', value: 'user' },
    });
    fireEvent.change(screen.getByPlaceholderText('Enter your email'), {
      target: { name: 'email', value: 'e@test.com' },
    });
    fireEvent.change(screen.getByPlaceholderText('Create a password'), {
      target: { name: 'password', value: 'password123' },
    });
    fireEvent.change(screen.getByPlaceholderText('Confirm your password'), {
      target: { name: 'confirmPassword', value: 'password123' },
    });

    fireEvent.click(screen.getByRole('button', { name: /create account/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('An error occurred during registration');
    });
  });

  test('has link to login page', () => {
    render(<Register />);

    const loginLink = screen.getByText('Sign in here');
    expect(loginLink).toBeInTheDocument();
    expect(loginLink.closest('a')).toHaveAttribute('href', '/login');
  });
});
