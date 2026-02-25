import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from './App';

// Mock all child components to isolate App routing tests
jest.mock('./contexts/AuthContext', () => ({
  AuthProvider: ({ children }) => <div data-testid="auth-provider">{children}</div>,
  useAuth: () => ({
    isAuthenticated: false,
    loading: false,
    user: null,
    token: null,
    login: jest.fn(),
    register: jest.fn(),
    logout: jest.fn(),
  }),
}));

jest.mock('./components/Auth/Login', () => () => <div data-testid="login-page">Login Page</div>);
jest.mock('./components/Auth/Register', () => () => <div data-testid="register-page">Register Page</div>);
jest.mock('./components/Dashboard/Dashboard', () => () => <div data-testid="dashboard-page">Dashboard</div>);
jest.mock('./components/Invoices/InvoiceList', () => () => <div data-testid="invoice-list">Invoice List</div>);
jest.mock('./components/Invoices/InvoiceForm', () => () => <div data-testid="invoice-form">Invoice Form</div>);
jest.mock('./components/Reports/Reports', () => () => <div data-testid="reports-page">Reports</div>);
jest.mock('./components/Layout/Navbar', () => () => <div data-testid="navbar">Navbar</div>);

// Mock ProtectedRoute to either render children or redirect
jest.mock('./components/ProtectedRoute', () => {
  const { useAuth } = require('./contexts/AuthContext');
  return ({ children }) => {
    const { isAuthenticated, loading } = useAuth();
    if (loading) return <div>Loading...</div>;
    if (!isAuthenticated) return <div data-testid="redirect-login">Redirect to Login</div>;
    return children;
  };
});

jest.mock('react-toastify', () => ({
  ToastContainer: () => <div data-testid="toast-container" />,
}));

describe('App Component', () => {
  test('renders without crashing', () => {
    render(<App />);

    expect(screen.getByTestId('auth-provider')).toBeInTheDocument();
  });

  test('renders ToastContainer', () => {
    render(<App />);

    expect(screen.getByTestId('toast-container')).toBeInTheDocument();
  });

  test('protected routes show redirect when not authenticated', () => {
    render(<App />);

    // Default route "/" redirects to /dashboard which is protected
    // Since not authenticated, should show redirect
    expect(screen.getAllByTestId('redirect-login').length).toBeGreaterThan(0);
  });
});

describe('App with authenticated user', () => {
  beforeEach(() => {
    // Override the mock to return authenticated state
    jest.resetModules();
  });

  test('renders login page at /login route', () => {
    // Set the window location to /login
    window.history.pushState({}, '', '/login');

    render(<App />);

    expect(screen.getByTestId('login-page')).toBeInTheDocument();
  });

  test('renders register page at /register route', () => {
    window.history.pushState({}, '', '/register');

    render(<App />);

    expect(screen.getByTestId('register-page')).toBeInTheDocument();
  });
});
