import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import CreateJob from './pages/CreateJob';
import JsonReview from './pages/JsonReview';
import ImageQueue from './pages/ImageQueue';
import Login from './pages/Login';
import ErrorLogs from './pages/ErrorLogs';

// Placeholders for other pages
const Placeholder = ({ title }) => (
  <div className="flex h-full items-center justify-center text-slate-400">
    <h2>{title} - Coming Soon</h2>
  </div>
);

function AppRoutes() {
  const { user } = useAuth();
  
  if (!user) {
    return <Login />;
  }

  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="jobs/create" element={<CreateJob />} />
        
        {/* Protected routes based on role can be handled in the component or layout.
            For now, just prevent NORMALUSER from accessing settings/approvals if they guess the URL */}
        {(user.role === 'SUPERADMIN' || user.role === 'ADMIN') && (
          <>
            <Route path="approvals/json" element={<JsonReview />} />
            <Route path="approvals/images" element={<ImageQueue />} />
          </>
        )}
        
        <Route path="bundles" element={<Placeholder title="Bundle Review" />} />
        <Route path="error-logs" element={<ErrorLogs />} />
        
        {user.role === 'SUPERADMIN' && (
          <Route path="settings" element={<Placeholder title="Settings" />} />
        )}

        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  );
}
