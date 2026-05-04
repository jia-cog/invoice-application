import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Navbar from './components/Layout/Navbar';

// Auth Components
import Login from './components/Auth/Login';
import Register from './components/Auth/Register';

// Main Components
import Dashboard from './components/Dashboard/Dashboard';
import InvoiceList from './components/Invoices/InvoiceList';
import InvoiceForm from './components/Invoices/InvoiceForm';
import Reports from './components/Reports/Reports';
import AdminUsers from './components/Admin/AdminUsers';

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="App">
          <Routes>
            {/* Public Routes */}
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />
            
            {/* Protected Routes */}
            <Route path="/dashboard" element={
              <ProtectedRoute>
                <Navbar />
                <Dashboard />
              </ProtectedRoute>
            } />
            
            <Route path="/invoices" element={
              <ProtectedRoute>
                <Navbar />
                <InvoiceList />
              </ProtectedRoute>
            } />
            
            <Route path="/invoices/new" element={
              <ProtectedRoute>
                <Navbar />
                <InvoiceForm />
              </ProtectedRoute>
            } />
            
            <Route path="/invoices/:id/edit" element={
              <ProtectedRoute>
                <Navbar />
                <InvoiceForm />
              </ProtectedRoute>
            } />
            
            <Route path="/invoices/:id" element={
              <ProtectedRoute>
                <Navbar />
                <InvoiceForm />
              </ProtectedRoute>
            } />
            
            <Route path="/reports" element={
              <ProtectedRoute>
                <Navbar />
                <Reports />
              </ProtectedRoute>
            } />

            {/* Admin-only routes */}
            <Route path="/admin/users" element={
              <ProtectedRoute adminOnly>
                <Navbar />
                <AdminUsers />
              </ProtectedRoute>
            } />

            {/* Default redirect */}
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
          
          <ToastContainer
            position="top-right"
            autoClose={5000}
            hideProgressBar={false}
            newestOnTop={false}
            closeOnClick
            rtl={false}
            pauseOnFocusLoss
            draggable
            pauseOnHover
            theme="light"
          />
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
