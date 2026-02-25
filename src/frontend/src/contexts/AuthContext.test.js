import React from 'react';
import { render, screen, act, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import { AuthProvider, useAuth } from './AuthContext';
import { authAPI } from '../utils/api';

// Mock the API module
jest.mock('../utils/api', () => ({
  authAPI: {
    login: jest.fn(),
    register: jest.fn(),
    getProfile: jest.fn(),
  },
}));

// Helper component to test useAuth hook
const TestComponent = ({ onAuth }) => {
  const auth = useAuth();
  React.useEffect(() => {
    if (onAuth) onAuth(auth);
  });
  return (
    <div>
      <span data-testid="loading">{String(auth.loading)}</span>
      <span data-testid="authenticated">{String(auth.isAuthenticated)}</span>
      <span data-testid="user">{auth.user ? auth.user.username : 'null'}</span>
      <button data-testid="logout-btn" onClick={auth.logout}>Logout</button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
  });

  describe('useAuth', () => {
    test('throws error when used outside AuthProvider', () => {
      // Suppress console.error for this test
      const consoleSpy = jest.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        render(<TestComponent />);
      }).toThrow('useAuth must be used within an AuthProvider');

      consoleSpy.mockRestore();
    });
  });

  describe('AuthProvider', () => {
    test('initializes from localStorage on mount', async () => {
      localStorage.setItem('token', 'saved-token');
      localStorage.setItem('user', JSON.stringify({ username: 'saveduser' }));

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('false');
      });

      expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
      expect(screen.getByTestId('user')).toHaveTextContent('saveduser');
    });

    test('starts with loading=true and no user when localStorage is empty', async () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      // After init, loading should be false
      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('false');
      });

      expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
      expect(screen.getByTestId('user')).toHaveTextContent('null');
    });

    test('login() calls authAPI.login, stores token/user, returns success', async () => {
      authAPI.login.mockResolvedValue({
        data: {
          access_token: 'new-token',
          user: { username: 'testuser', email: 'test@test.com' },
        },
      });

      let authRef;
      render(
        <AuthProvider>
          <TestComponent onAuth={(auth) => { authRef = auth; }} />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('false');
      });

      let result;
      await act(async () => {
        result = await authRef.login({ username: 'testuser', password: 'pass123' });
      });

      expect(result).toEqual({ success: true });
      expect(authAPI.login).toHaveBeenCalledWith({ username: 'testuser', password: 'pass123' });
      expect(localStorage.getItem('token')).toBe('new-token');
      expect(JSON.parse(localStorage.getItem('user'))).toEqual({ username: 'testuser', email: 'test@test.com' });
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
      expect(screen.getByTestId('user')).toHaveTextContent('testuser');
    });

    test('login() returns error on failure', async () => {
      authAPI.login.mockRejectedValue({
        response: { data: { error: 'Invalid credentials' } },
      });

      let authRef;
      render(
        <AuthProvider>
          <TestComponent onAuth={(auth) => { authRef = auth; }} />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('false');
      });

      let result;
      await act(async () => {
        result = await authRef.login({ username: 'bad', password: 'bad' });
      });

      expect(result).toEqual({ success: false, error: 'Invalid credentials' });
      expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
    });

    test('login() returns default error message when no error in response', async () => {
      authAPI.login.mockRejectedValue(new Error('Network error'));

      let authRef;
      render(
        <AuthProvider>
          <TestComponent onAuth={(auth) => { authRef = auth; }} />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('false');
      });

      let result;
      await act(async () => {
        result = await authRef.login({ username: 'test', password: 'test' });
      });

      expect(result).toEqual({ success: false, error: 'Login failed' });
    });

    test('register() calls authAPI.register, stores token/user, returns success', async () => {
      authAPI.register.mockResolvedValue({
        data: {
          access_token: 'reg-token',
          user: { username: 'newuser', email: 'new@test.com' },
        },
      });

      let authRef;
      render(
        <AuthProvider>
          <TestComponent onAuth={(auth) => { authRef = auth; }} />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('false');
      });

      const userData = { username: 'newuser', email: 'new@test.com', password: 'pass123' };
      let result;
      await act(async () => {
        result = await authRef.register(userData);
      });

      expect(result).toEqual({ success: true });
      expect(authAPI.register).toHaveBeenCalledWith(userData);
      expect(localStorage.getItem('token')).toBe('reg-token');
      expect(screen.getByTestId('authenticated')).toHaveTextContent('true');
      expect(screen.getByTestId('user')).toHaveTextContent('newuser');
    });

    test('register() returns error on failure', async () => {
      authAPI.register.mockRejectedValue({
        response: { data: { error: 'Username already taken' } },
      });

      let authRef;
      render(
        <AuthProvider>
          <TestComponent onAuth={(auth) => { authRef = auth; }} />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('false');
      });

      let result;
      await act(async () => {
        result = await authRef.register({ username: 'taken' });
      });

      expect(result).toEqual({ success: false, error: 'Username already taken' });
    });

    test('register() returns default error message when no error in response', async () => {
      authAPI.register.mockRejectedValue(new Error('Network error'));

      let authRef;
      render(
        <AuthProvider>
          <TestComponent onAuth={(auth) => { authRef = auth; }} />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('false');
      });

      let result;
      await act(async () => {
        result = await authRef.register({ username: 'test' });
      });

      expect(result).toEqual({ success: false, error: 'Registration failed' });
    });

    test('logout() clears localStorage and resets state', async () => {
      localStorage.setItem('token', 'some-token');
      localStorage.setItem('user', JSON.stringify({ username: 'testuser' }));

      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('false');
      });

      expect(screen.getByTestId('authenticated')).toHaveTextContent('true');

      act(() => {
        screen.getByTestId('logout-btn').click();
      });

      expect(localStorage.getItem('token')).toBeNull();
      expect(localStorage.getItem('user')).toBeNull();
      expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
      expect(screen.getByTestId('user')).toHaveTextContent('null');
    });

    test('isAuthenticated reflects token presence', async () => {
      render(
        <AuthProvider>
          <TestComponent />
        </AuthProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('loading')).toHaveTextContent('false');
      });

      // No token = not authenticated
      expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
    });
  });
});
