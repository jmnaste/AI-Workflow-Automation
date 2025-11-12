// Auth Routes - Proxy to Auth Service
import express from 'express';
import { setAuthCookie, clearAuthCookie, verifyToken } from '../middleware/jwt.js';

const router = express.Router();

const AUTH_SERVICE_URL = process.env.AUTH_BASE_URL || 'http://auth:8000';

/**
 * POST /bff/auth/request-otp
 * Proxy to Auth Service: Request OTP for email
 */
router.post('/request-otp', async (req, res) => {
  try {
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/request-otp`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(req.body),
    });
    
    const data = await response.json() as any;
    
    if (!response.ok) {
      res.status(response.status).json(data);
      return;
    }
    
    req.log.info({ email: req.body.email, isNewUser: data.isNewUser }, 'OTP requested via Auth Service');
    res.json(data);
    
  } catch (error) {
    req.log.error({ error }, 'Failed to proxy request-otp to Auth Service');
    res.status(500).json({ error: 'Failed to connect to authentication service' });
  }
});

/**
 * POST /bff/auth/verify-otp
 * Proxy to Auth Service: Verify OTP and set JWT cookie
 */
router.post('/verify-otp', async (req, res) => {
  try {
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/verify-otp`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(req.body),
    });
    
    const data = await response.json() as any;
    
    if (!response.ok) {
      res.status(response.status).json(data);
      return;
    }
    
    // Extract JWT token from Auth Service response
    const { token, user } = data;
    
    // Set JWT in httpOnly cookie
    setAuthCookie(res, token);
    
    req.log.info({ email: user.email, userId: user.id }, 'User authenticated via Auth Service');
    
    // Return user profile (without token for security)
    res.json({
      success: true,
      user,
    });
    
  } catch (error) {
    req.log.error({ error }, 'Failed to proxy verify-otp to Auth Service');
    res.status(500).json({ error: 'Failed to connect to authentication service' });
  }
});

/**
 * GET /bff/auth/me
 * Get current user profile from Auth Service
 */
router.get('/me', async (req, res) => {
  try {
    // Extract JWT from cookie
    const token = req.cookies[process.env.JWT_COOKIE_NAME || 'flovify_token'];
    
    if (!token) {
      res.status(401).json({ error: 'Not authenticated' });
      return;
    }
    
    // Verify token locally (optional, for early validation)
    try {
      verifyToken(token);
    } catch (error) {
      clearAuthCookie(res);
      res.status(401).json({ error: 'Invalid or expired token' });
      return;
    }
    
    // Proxy to Auth Service with Bearer token
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/me`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      if (response.status === 401) {
        clearAuthCookie(res);
      }
      res.status(response.status).json(data);
      return;
    }
    
    res.json(data);
    
  } catch (error) {
    req.log.error({ error }, 'Failed to proxy /me to Auth Service');
    res.status(500).json({ error: 'Failed to connect to authentication service' });
  }
});

/**
 * POST /bff/auth/logout
 * Clear JWT cookie
 */
router.post('/logout', (req, res) => {
  clearAuthCookie(res);
  req.log.info('User logged out (cookie cleared)');
  res.json({ success: true, message: 'Logged out successfully' });
});

/**
 * GET /bff/auth/tenants
 * List all connected tenants (admin only)
 */
router.get('/tenants', async (req, res) => {
  try {
    const token = req.cookies[process.env.JWT_COOKIE_NAME || 'flovify_token'];
    
    if (!token) {
      res.status(401).json({ error: 'Not authenticated' });
      return;
    }
    
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/tenants`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      res.status(response.status).json(data);
      return;
    }
    
    res.json(data);
    
  } catch (error) {
    req.log.error({ error }, 'Failed to proxy tenants list to Auth Service');
    res.status(500).json({ error: 'Failed to connect to authentication service' });
  }
});

/**
 * DELETE /bff/auth/tenants/:tenantId
 * Disconnect a tenant (admin only)
 */
router.delete('/tenants/:tenantId', async (req, res) => {
  try {
    const token = req.cookies[process.env.JWT_COOKIE_NAME || 'flovify_token'];
    
    if (!token) {
      res.status(401).json({ error: 'Not authenticated' });
      return;
    }
    
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/tenants/${req.params.tenantId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      res.status(response.status).json(data);
      return;
    }
    
    req.log.info({ tenantId: req.params.tenantId }, 'Tenant disconnected');
    res.json(data);
    
  } catch (error) {
    req.log.error({ error }, 'Failed to proxy tenant deletion to Auth Service');
    res.status(500).json({ error: 'Failed to connect to authentication service' });
  }
});

/**
 * GET /bff/auth/oauth/:provider/authorize
 * Start OAuth flow for connecting external account
 * Redirects to Auth Service which redirects to OAuth provider
 */
router.get('/oauth/:provider/authorize', async (req, res) => {
  try {
    const token = req.cookies[process.env.JWT_COOKIE_NAME || 'flovify_token'];
    
    if (!token) {
      res.status(401).json({ error: 'Not authenticated' });
      return;
    }
    
    const provider = req.params.provider;
    
    // Redirect to Auth Service OAuth endpoint (which will redirect to provider)
    const authUrl = `${AUTH_SERVICE_URL}/auth/oauth/${provider}/authorize`;
    
    // Forward with Authorization header
    const response = await fetch(authUrl, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      redirect: 'manual', // Don't follow redirects
    });
    
    // Get redirect location from Auth Service
    const location = response.headers.get('location');
    
    if (location) {
      req.log.info({ provider }, 'Redirecting to OAuth provider');
      res.redirect(location);
    } else {
      res.status(500).json({ error: 'Failed to initiate OAuth flow' });
    }
    
  } catch (error) {
    req.log.error({ error }, 'Failed to start OAuth flow');
    res.status(500).json({ error: 'Failed to connect to authentication service' });
  }
});

export default router;
