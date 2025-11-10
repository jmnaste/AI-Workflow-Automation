import { useState } from 'react';
import {
  Box,
  AppBar,
  Toolbar,
  Typography,
  IconButton,
  Drawer,
  useMediaQuery,
  useTheme,
  Avatar,
  Menu,
  MenuItem,
  ListItemIcon,
  Divider,
  Tooltip,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import AccountCircleIcon from '@mui/icons-material/AccountCircle';
import SettingsIcon from '@mui/icons-material/Settings';
import LogoutIcon from '@mui/icons-material/Logout';
import LoginIcon from '@mui/icons-material/Login';
import ChevronLeftIcon from '@mui/icons-material/ChevronLeft';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import { Outlet, useNavigate } from 'react-router-dom';
import Navigation from './Navigation';
import { useAuth } from '../contexts/AuthContext';
import { signOut as apiSignOut } from '../lib/api/auth.js';

const DRAWER_WIDTH_EXPANDED = 240;
const DRAWER_WIDTH_COLLAPSED = 64;

export default function AppLayout() {
  const theme = useTheme();
  const navigate = useNavigate();
  const { user, isAuthenticated, signOut } = useAuth();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileOpen, setMobileOpen] = useState(false);
  const [drawerExpanded, setDrawerExpanded] = useState(true);
  const [userMenuAnchor, setUserMenuAnchor] = useState<null | HTMLElement>(null);

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen);
  };

  const handleDrawerExpandToggle = () => {
    setDrawerExpanded(!drawerExpanded);
  };

  const handleUserMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setUserMenuAnchor(event.currentTarget);
  };

  const handleUserMenuClose = () => {
    setUserMenuAnchor(null);
  };

  const handleSignOut = async () => {
    handleUserMenuClose();
    try {
      await apiSignOut(); // Call API to clear cookie
    } catch (err) {
      console.error('Sign out API error:', err);
    }
    signOut(); // Clear local auth state
    navigate('/sign-in'); // Redirect to sign-in
  };

  const drawerWidth = drawerExpanded ? DRAWER_WIDTH_EXPANDED : DRAWER_WIDTH_COLLAPSED;

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* App Bar */}
      <AppBar
        position="fixed"
        sx={{
          zIndex: theme.zIndex.drawer + 1,
          backgroundColor: 'background.paper',
          color: 'text.primary',
        }}
      >
        <Toolbar sx={{ justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            {isMobile && (
              <IconButton
                color="inherit"
                edge="start"
                onClick={handleDrawerToggle}
              >
                <MenuIcon />
              </IconButton>
            )}
            <Typography variant="h6" noWrap sx={{ fontWeight: 700, color: 'primary.main' }}>
              Flovify
            </Typography>
          </Box>

          {/* User Menu */}
          <Box>
            {isAuthenticated ? (
              <>
                <Tooltip title="Account">
                  <IconButton onClick={handleUserMenuOpen} size="small">
                    <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main' }}>
                      {user?.email.charAt(0).toUpperCase()}
                    </Avatar>
                  </IconButton>
                </Tooltip>
                <Menu
                  anchorEl={userMenuAnchor}
                  open={Boolean(userMenuAnchor)}
                  onClose={handleUserMenuClose}
                  transformOrigin={{ horizontal: 'right', vertical: 'top' }}
                  anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
                  slotProps={{
                    paper: {
                      sx: { mt: 1, minWidth: 200 },
                    },
                  }}
                >
                  <Box sx={{ px: 2, py: 1.5 }}>
                    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                      {user?.email.split('@')[0]}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {user?.email}
                    </Typography>
                  </Box>
                  <Divider />
                  <MenuItem onClick={handleUserMenuClose}>
                    <ListItemIcon>
                      <AccountCircleIcon fontSize="small" />
                    </ListItemIcon>
                    My Account
                  </MenuItem>
                  <MenuItem onClick={handleUserMenuClose}>
                    <ListItemIcon>
                      <SettingsIcon fontSize="small" />
                    </ListItemIcon>
                    Settings
                  </MenuItem>
                  <Divider />
                  <MenuItem onClick={handleSignOut}>
                    <ListItemIcon>
                      <LogoutIcon fontSize="small" />
                    </ListItemIcon>
                    Sign Out
                  </MenuItem>
                </Menu>
              </>
            ) : (
              <Tooltip title="Sign in">
                <IconButton size="small" onClick={() => navigate('/sign-in')}>
                  <LoginIcon />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </Toolbar>
      </AppBar>

      {/* Sidebar Drawer */}
      <Box
        component="nav"
        sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}
      >
        {isMobile ? (
          <Drawer
            variant="temporary"
            open={mobileOpen}
            onClose={handleDrawerToggle}
            ModalProps={{ keepMounted: true }}
            sx={{
              '& .MuiDrawer-paper': {
                boxSizing: 'border-box',
                width: DRAWER_WIDTH_EXPANDED,
              },
            }}
          >
            <Navigation expanded={true} />
          </Drawer>
        ) : (
          <Drawer
            variant="permanent"
            sx={{
              '& .MuiDrawer-paper': {
                boxSizing: 'border-box',
                width: drawerWidth,
                transition: theme.transitions.create('width', {
                  easing: theme.transitions.easing.sharp,
                  duration: theme.transitions.duration.enteringScreen,
                }),
              },
            }}
            open
          >
            <Navigation expanded={drawerExpanded} />
            {!isMobile && (
              <Box
                sx={{
                  position: 'absolute',
                  bottom: 16,
                  left: 0,
                  right: 0,
                  display: 'flex',
                  justifyContent: 'center',
                }}
              >
                <IconButton
                  onClick={handleDrawerExpandToggle}
                  size="small"
                  sx={{
                    bgcolor: 'background.paper',
                    border: '1px solid',
                    borderColor: 'divider',
                    '&:hover': { bgcolor: 'background.paper' },
                  }}
                >
                  {drawerExpanded ? <ChevronLeftIcon /> : <ChevronRightIcon />}
                </IconButton>
              </Box>
            )}
          </Drawer>
        )}
      </Box>

      {/* Main Content */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          width: { md: `calc(100% - ${drawerWidth}px)` },
          mt: 8,
          backgroundColor: 'background.default',
          minHeight: '100vh',
          transition: theme.transitions.create('width', {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.enteringScreen,
          }),
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
}
