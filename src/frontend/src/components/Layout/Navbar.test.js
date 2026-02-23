import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import Navbar from './Navbar';

// Mock modules
const mockNavigate = jest.fn();
const mockLogout = jest.fn();
const mockLocation = { pathname: '/dashboard' };

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  useLocation: () => mockLocation,
  Link: ({ to, children, className, style }) => (
    <a href={to} className={className} style={style}>{children}</a>
  ),
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    user: { username: 'testuser' },
    logout: mockLogout,
  }),
}));

// Mock lucide-react icons
jest.mock('lucide-react', () => ({
  LogOut: () => <span>LogOut</span>,
  FileText: () => <span>FileText</span>,
  BarChart3: () => <span>BarChart3</span>,
  Home: () => <span>Home</span>,
}));

describe('Navbar Component', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('renders navigation links (Dashboard, Invoices, Reports)', () => {
    render(<Navbar />);

    expect(screen.getByText('Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Invoices')).toBeInTheDocument();
    expect(screen.getByText('Reports')).toBeInTheDocument();
  });

  test('renders Invoice App brand link', () => {
    render(<Navbar />);

    expect(screen.getByText('Invoice App')).toBeInTheDocument();
  });

  test('shows welcome message with username', () => {
    render(<Navbar />);

    expect(screen.getByText('Welcome, testuser')).toBeInTheDocument();
  });

  test('logout button calls logout and navigates to /login', () => {
    render(<Navbar />);

    const logoutButton = screen.getByText('Logout').closest('button');
    fireEvent.click(logoutButton);

    expect(mockLogout).toHaveBeenCalled();
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });

  test('navigation links have correct hrefs', () => {
    render(<Navbar />);

    const dashboardLink = screen.getByText('Dashboard').closest('a');
    const invoicesLink = screen.getByText('Invoices').closest('a');
    const reportsLink = screen.getByText('Reports').closest('a');

    expect(dashboardLink).toHaveAttribute('href', '/dashboard');
    expect(invoicesLink).toHaveAttribute('href', '/invoices');
    expect(reportsLink).toHaveAttribute('href', '/reports');
  });
});
