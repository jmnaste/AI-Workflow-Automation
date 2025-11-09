import {
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Divider,
  Tooltip,
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import SettingsIcon from '@mui/icons-material/Settings';
import WorkflowIcon from '@mui/icons-material/AccountTree';
import { useNavigate, useLocation } from 'react-router-dom';

const menuItems = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
  { text: 'Workflows', icon: <WorkflowIcon />, path: '/workflows' },
  { text: 'Settings', icon: <SettingsIcon />, path: '/settings' },
];

interface NavigationProps {
  expanded: boolean;
}

export default function Navigation({ expanded }: NavigationProps) {
  const navigate = useNavigate();
  const location = useLocation();

  return (
    <div>
      <Toolbar />
      <Divider />
      <List sx={{ pt: 1 }}>
        {menuItems.map((item) => {
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
        })}
      </List>
    </div>
  );
}
