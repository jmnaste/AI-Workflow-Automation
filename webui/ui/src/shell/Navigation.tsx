import {
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Divider,
  Tooltip,
  Typography,
  Box,
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import SettingsIcon from '@mui/icons-material/Settings';
import WorkflowIcon from '@mui/icons-material/AccountTree';
import PeopleIcon from '@mui/icons-material/People';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const menuItems = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
  { text: 'Workflows', icon: <WorkflowIcon />, path: '/workflows' },
  { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
];

const adminMenuItems = [
  { text: 'User Management', icon: <PeopleIcon />, path: '/admin/users' },
  { text: 'System Settings', icon: <AdminPanelSettingsIcon />, path: '/admin/settings' },
];

interface NavigationProps {
  expanded: boolean;
}

export default function Navigation({ expanded }: NavigationProps) {
  const navigate = useNavigate();
  const location = useLocation();
  const { user } = useAuth();
  
  const isAdmin = user?.role === 'admin' || user?.role === 'super';

  const renderMenuItem = (item: typeof menuItems[0]) => {
    const isSelected = location.pathname === item.path;
    const button = (
      <ListItemButton
        selected={isSelected}
        onClick={() => navigate(item.path)}
        sx={{
          minHeight: 44,
          justifyContent: expanded ? 'initial' : 'center',
          px: expanded ? 2 : 1.5,
        }}
      >
        <ListItemIcon
          sx={{
            minWidth: 0,
            mr: expanded ? 2 : 'auto',
            justifyContent: 'center',
          }}
        >
          {item.icon}
        </ListItemIcon>
        {expanded && <ListItemText primary={item.text} />}
      </ListItemButton>
    );

    return (
      <ListItem key={item.text} disablePadding sx={{ display: 'block' }}>
        {expanded ? (
          button
        ) : (
          <Tooltip title={item.text} placement="right">
            {button}
          </Tooltip>
        )}
      </ListItem>
    );
  };

  return (
    <div>
      <Toolbar />
      <Divider />
      
      {/* Main Navigation */}
      <List sx={{ pt: 1 }}>
        {menuItems.map(renderMenuItem)}
      </List>
      
      {/* Admin Console Section - Only visible to admin/super */}
      {isAdmin && (
        <>
          <Divider sx={{ my: 1 }} />
          {expanded && (
            <Box sx={{ px: 2, py: 1 }}>
              <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 600 }}>
                ADMIN CONSOLE
              </Typography>
            </Box>
          )}
          <List sx={{ pt: 0 }}>
            {adminMenuItems.map(renderMenuItem)}
          </List>
        </>
      )}
    </div>
  );
}
