import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

/**
 * AdminLayout - Protects admin routes
 * Only allows access to users with role 'admin'
 * Note: 'super-user' role has elevated business privileges but NO admin console access
 */
export default function AdminLayout() {
  const { user } = useAuth();

  // Check if user has admin role (super-user role is NOT allowed in admin console)
  const isAdmin = user?.role === 'admin';

  if (!isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
