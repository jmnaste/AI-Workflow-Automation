// Admin Routes - Proxy to Auth Service with role verification
import express from 'express';
import { requireAuth } from '../middleware/jwt.js';

const router = express.Router();

const AUTH_SERVICE_URL = process.env.AUTH_BASE_URL || 'http://auth:8000';

/**
 * Middleware to verify admin role.
 * 
 * User Role Definitions:
 * - user: Standard user with basic access
 * - super: Elevated user with additional business workflow privileges (NOT admin console)
 * - admin: Full administrative access including admin console and user management
 * 
 * Only 'admin' role can access admin console routes.
 */
function requireAdmin(req: express.Request, res: express.Response, next: express.NextFunction): void {
  if (!req.user) {
    res.status(401).json({ error: 'Authentication required' });
    return;
  }
  
  const role = (req.user as any).role;
  // Only 'admin' role can access admin console
  if (role !== 'admin') {
    res.status(403).json({ error: 'Admin access required' });
    return;
  }
  
  next();
}

// Apply authentication and admin role check to all admin routes
router.use(requireAuth);
router.use(requireAdmin);

/**
 * GET /bff/admin/users
 * List all users (admin only)
 */
router.get('/users', async (req, res) => {
  try {
    const token = req.cookies[process.env.JWT_COOKIE_NAME || 'flovify_token'];
    
    // Build query params for pagination
    const queryParams = new URLSearchParams();
    if (req.query.page) queryParams.append('page', req.query.page as string);
    if (req.query.limit) queryParams.append('limit', req.query.limit as string);
    if (req.query.search) queryParams.append('search', req.query.search as string);
    
    const url = `${AUTH_SERVICE_URL}/auth/admin/users${queryParams.toString() ? '?' + queryParams.toString() : ''}`;
    
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    const data = await response.json() as any;
    
    if (!response.ok) {
      res.status(response.status).json(data);
      return;
    }
    
    req.log.info({ admin: req.user?.email, userCount: data.users?.length }, 'Admin listed users');
    res.json(data);
    
  } catch (error) {
    req.log.error({ error }, 'Failed to proxy admin/users to Auth Service');
    res.status(500).json({ error: 'Failed to connect to authentication service' });
  }
});

/**
 * POST /bff/admin/users
 * Create a new user (admin only)
 */
router.post('/users', async (req, res) => {
  try {
    const token = req.cookies[process.env.JWT_COOKIE_NAME || 'flovify_token'];
    
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/admin/users`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(req.body),
    });
    
    const data = await response.json() as any;
    
    if (!response.ok) {
      res.status(response.status).json(data);
      return;
    }
    
    req.log.info({ admin: req.user?.email, email: req.body.email }, 'Admin created user');
    res.json(data);
    
  } catch (error) {
    req.log.error({ error }, 'Failed to proxy admin/users POST to Auth Service');
    res.status(500).json({ error: 'Failed to connect to authentication service' });
  }
});

/**
 * PATCH /bff/admin/users/:id
 * Update user role or status (admin only)
 */
router.patch('/users/:id', async (req, res) => {
  try {
    const token = req.cookies[process.env.JWT_COOKIE_NAME || 'flovify_token'];
    const userId = req.params.id;
    
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/admin/users/${userId}`, {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(req.body),
    });
    
    const data = await response.json() as any;
    
    if (!response.ok) {
      res.status(response.status).json(data);
      return;
    }
    
    req.log.info({ admin: req.user?.email, userId, updates: req.body }, 'Admin updated user');
    res.json(data);
    
  } catch (error) {
    req.log.error({ error }, 'Failed to proxy admin/users/:id to Auth Service');
    res.status(500).json({ error: 'Failed to connect to authentication service' });
  }
});

/**
 * DELETE /bff/admin/users/:id
 * Delete user (admin only)
 */
router.delete('/users/:id', async (req, res) => {
  try {
    const token = req.cookies[process.env.JWT_COOKIE_NAME || 'flovify_token'];
    const userId = req.params.id;
    
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/admin/users/${userId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    const data = await response.json() as any;
    
    if (!response.ok) {
      res.status(response.status).json(data);
      return;
    }
    
    req.log.info({ admin: req.user?.email, userId }, 'Admin deleted user');
    res.json(data);
    
  } catch (error) {
    req.log.error({ error }, 'Failed to proxy admin/users/:id DELETE to Auth Service');
    res.status(500).json({ error: 'Failed to connect to authentication service' });
  }
});

/**
 * GET /bff/admin/settings
 * Get system settings (admin only)
 */
router.get('/settings', async (req, res) => {
  try {
    const token = req.cookies[process.env.JWT_COOKIE_NAME || 'flovify_token'];
    
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/admin/settings`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    const data = await response.json() as any;
    
    if (!response.ok) {
      res.status(response.status).json(data);
      return;
    }
    
    req.log.info({ admin: req.user?.email }, 'Admin retrieved settings');
    res.json(data);
    
  } catch (error) {
    req.log.error({ error }, 'Failed to proxy admin/settings to Auth Service');
    res.status(500).json({ error: 'Failed to connect to authentication service' });
  }
});

/**
 * POST /bff/admin/settings
 * Update system settings (admin only)
 */
router.post('/settings', async (req, res) => {
  try {
    const token = req.cookies[process.env.JWT_COOKIE_NAME || 'flovify_token'];
    
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/admin/settings`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(req.body),
    });
    
    const data = await response.json() as any;
    
    if (!response.ok) {
      res.status(response.status).json(data);
      return;
    }
    
    req.log.info({ admin: req.user?.email, settings: req.body }, 'Admin updated settings');
    res.json(data);
    
  } catch (error) {
    req.log.error({ error }, 'Failed to proxy admin/settings to Auth Service');
    res.status(500).json({ error: 'Failed to connect to authentication service' });
  }
});

export default router;
