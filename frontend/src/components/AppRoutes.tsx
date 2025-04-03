import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import Layout from './Layout';
import Login from '../pages/Login';
import Dashboard from '../pages/Dashboard';

// Protected route component
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { isAuthenticated } = useAuth();
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  
  return <Layout>{children}</Layout>;
};

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      
      <Route path="/" element={
        <ProtectedRoute>
          <Dashboard />
        </ProtectedRoute>
      } />
      
      {/* Add placeholder routes for future implementation */}
      <Route path="/tags" element={
        <ProtectedRoute>
          <div className="p-6">
            <h1 className="text-3xl font-bold">Tags Management</h1>
            <p className="mt-4">This page is under construction.</p>
          </div>
        </ProtectedRoute>
      } />
      
      <Route path="/media" element={
        <ProtectedRoute>
          <div className="p-6">
            <h1 className="text-3xl font-bold">Media Library</h1>
            <p className="mt-4">This page is under construction.</p>
          </div>
        </ProtectedRoute>
      } />
      
      <Route path="/system" element={
        <ProtectedRoute>
          <div className="p-6">
            <h1 className="text-3xl font-bold">System Settings</h1>
            <p className="mt-4">This page is under construction.</p>
          </div>
        </ProtectedRoute>
      } />
      
      {/* Catch all route - redirect to dashboard */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}