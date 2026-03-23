import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { LogOut, FileText, BarChart3, Home } from 'lucide-react';

const Navbar = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path) => location.pathname === path;

  return (
    <nav style={{
      background: 'white',
      borderBottom: '1px solid #e5e7eb',
      padding: '0 1rem',
      position: 'sticky',
      top: 0,
      zIndex: 1000,
      boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)'
    }}>
      <div className="container" style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: '4rem'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
          <Link 
            to="/dashboard" 
            style={{
              fontSize: '1.5rem',
              fontWeight: 'bold',
              color: '#3b82f6',
              textDecoration: 'none'
            }}
          >
            Invoice App
          </Link>
          
          <div style={{ display: 'flex', gap: '1rem' }}>
            <Link
              to="/dashboard"
              className={`btn ${isActive('/dashboard') ? 'btn-primary' : 'btn-outline'}`}
              style={{ textDecoration: 'none' }}
            >
              <Home size={16} />
              Dashboard
            </Link>
            <Link
              to="/invoices"
              className={`btn ${isActive('/invoices') ? 'btn-primary' : 'btn-outline'}`}
              style={{ textDecoration: 'none' }}
            >
              <FileText size={16} />
              Invoices
            </Link>
            <Link
              to="/reports"
              className={`btn ${isActive('/reports') ? 'btn-primary' : 'btn-outline'}`}
              style={{ textDecoration: 'none' }}
            >
              <BarChart3 size={16} />
              Reports
            </Link>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <span style={{ color: '#6b7280', fontSize: '0.875rem' }}>
            Welcome, {user?.username}
          </span>
          {user?.is_admin && (
            <span style={{
              background: '#3b82f6',
              color: 'white',
              padding: '0.125rem 0.5rem',
              borderRadius: '9999px',
              fontSize: '0.75rem',
              fontWeight: '600'
            }}>
              Admin
            </span>
          )}
          <button
            onClick={handleLogout}
            className="btn btn-outline"
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
          >
            <LogOut size={16} />
            Logout
          </button>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
