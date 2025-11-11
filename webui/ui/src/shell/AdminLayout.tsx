import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

/**
 * AdminLayout - Protects admin routes
 * Only allows access to users with role 'admin' or 'super'
 */
export default function AdminLayout() {
  const { user } = useAuth();

  // Check if user has admin or super role
  const isAdmin = user?.role === 'admin' || user?.role === 'super';

  if (!isAdmin) {
    return <Navigate to="/dashboard" replace />;
  }

  return <Outlet />;
}
