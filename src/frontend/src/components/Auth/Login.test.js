import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import '@testing-library/jest-dom';
import Login from './Login';

// Mock modules
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  Link: ({ to, children, ...props }) => <a href={to} {...props}>{children}</a>,
}));

const mockLogin = jest.fn();
jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    login: mockLogin,
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
  LogIn: () => <span>LogIn</span>,
  User: () => <span>User</span>,
  Lock: () => <span>Lock</span>,
}));

describe('Login Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders login form with username and password fields', () => {
    render(<Login />);

    expect(screen.getByPlaceholderText('Enter your username')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Enter your password')).toBeInTheDocument();
  });

  test('renders Welcome Back heading', () => {
    render(<Login />);

    expect(screen.getByText('Welcome Back')).toBeInTheDocument();
    expect(screen.getByText('Sign in to Invoice Application')).toBeInTheDocument();
  });

  test('submit button is present', () => {
    render(<Login />);

    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  test('calls login with form data on submit', async () => {
    mockLogin.mockResolvedValue({ success: true });

    render(<Login />);

    fireEvent.change(screen.getByPlaceholderText('Enter your username'), {
      target: { name: 'username', value: 'testuser' },
    });
    fireEvent.change(screen.getByPlaceholderText('Enter your password'), {
      target: { name: 'password', value: 'password123' },
    });

    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        username: 'testuser',
        password: 'password123',
      });
    });
  });

  test('shows success toast and navigates on successful login', async () => {
    mockLogin.mockResolvedValue({ success: true });

    render(<Login />);

    fireEvent.change(screen.getByPlaceholderText('Enter your username'), {
      target: { name: 'username', value: 'testuser' },
    });
    fireEvent.change(screen.getByPlaceholderText('Enter your password'), {
      target: { name: 'password', value: 'password123' },
    });

    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('Login successful!');
      expect(mockNavigate).toHaveBeenCalledWith('/dashboard');
    });
  });

  test('shows error toast on failed login', async () => {
    mockLogin.mockResolvedValue({ success: false, error: 'Invalid credentials' });

    render(<Login />);

    fireEvent.change(screen.getByPlaceholderText('Enter your username'), {
      target: { name: 'username', value: 'bad' },
    });
    fireEvent.change(screen.getByPlaceholderText('Enter your password'), {
      target: { name: 'password', value: 'bad' },
    });

    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('Invalid credentials');
    });
  });

  test('shows error toast when login throws an exception', async () => {
    mockLogin.mockRejectedValue(new Error('Network error'));

    render(<Login />);

    fireEvent.change(screen.getByPlaceholderText('Enter your username'), {
      target: { name: 'username', value: 'test' },
    });
    fireEvent.change(screen.getByPlaceholderText('Enter your password'), {
      target: { name: 'password', value: 'test' },
    });

    fireEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('An error occurred during login');
    });
  });

  test('has link to register page', () => {
    render(<Login />);

    const registerLink = screen.getByText('Create one here');
    expect(registerLink).toBeInTheDocument();
    expect(registerLink.closest('a')).toHaveAttribute('href', '/register');
  });
});
