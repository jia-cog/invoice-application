import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5001/api';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: (userData) => api.post('/auth/register', userData),
  login: (credentials) => api.post('/auth/login', credentials),
  getProfile: () => api.get('/auth/profile'),
};

// Invoices API
export const invoicesAPI = {
  getAll: () => api.get('/invoices/'),
  getById: (id) => api.get(`/invoices/${id}`),
  create: (invoiceData) => api.post('/invoices/', invoiceData),
  update: (id, invoiceData) => api.put(`/invoices/${id}`, invoiceData),
  delete: (id) => api.delete(`/invoices/${id}`),
};

// Reports API
export const reportsAPI = {
  getAll: () => api.get('/reports/'),
  generate: (reportData) => api.post('/reports/generate', reportData),
  getDashboard: () => api.get('/reports/dashboard'),
  delete: (id) => api.delete(`/reports/${id}`),
  getUsageAnalytics: (days = 60) => api.get(`/reports/usage-analytics?days=${days}`),
  getQualityMetrics: (days = 60) => api.get(`/reports/invoice-quality?days=${days}`),
};

export default api;
