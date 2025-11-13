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
 * GET /bff/auth/credentials
 * List all credentials (admin only)
 */
router.get('/credentials', async (req, res) => {
  try {
    const token = req.cookies[process.env.JWT_COOKIE_NAME || 'flovify_token'];
    
    if (!token) {
      res.status(401).json({ error: 'Not authenticated' });
      return;
    }
    
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/credentials/`, {
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
    req.log.error({ error }, 'Failed to proxy credentials list to Auth Service');
    res.status(500).json({ error: 'Failed to connect to authentication service' });
  }
});

/**
 * POST /bff/auth/credentials
 * Create a new credential (admin only)
 */
router.post('/credentials', async (req, res) => {
  try {
    const token = req.cookies[process.env.JWT_COOKIE_NAME || 'flovify_token'];
    
    if (!token) {
      res.status(401).json({ error: 'Not authenticated' });
      return;
    }
    
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/credentials/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(req.body),
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      res.status(response.status).json(data);
      return;
    }
    
    req.log.info({ credentialName: req.body.name }, 'Credential created');
    res.status(201).json(data);
    
  } catch (error) {
    req.log.error({ error }, 'Failed to proxy credential creation to Auth Service');
    res.status(500).json({ error: 'Failed to connect to authentication service' });
  }
});

/**
 * GET /bff/auth/credentials/:credentialId
 * Get a specific credential (admin only)
 */
router.get('/credentials/:credentialId', async (req, res) => {
  try {
    const token = req.cookies[process.env.JWT_COOKIE_NAME || 'flovify_token'];
    
    if (!token) {
      res.status(401).json({ error: 'Not authenticated' });
      return;
    }
    
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/credentials/${req.params.credentialId}`, {
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
    req.log.error({ error }, 'Failed to proxy credential get to Auth Service');
    res.status(500).json({ error: 'Failed to connect to authentication service' });
  }
});

/**
 * DELETE /bff/auth/credentials/:credentialId
 * Delete a credential (admin only)
 */
router.delete('/credentials/:credentialId', async (req, res) => {
  try {
    const token = req.cookies[process.env.JWT_COOKIE_NAME || 'flovify_token'];
    
    if (!token) {
      res.status(401).json({ error: 'Not authenticated' });
      return;
    }
    
    const response = await fetch(`${AUTH_SERVICE_URL}/auth/credentials/${req.params.credentialId}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (response.status === 204) {
      req.log.info({ credentialId: req.params.credentialId }, 'Credential deleted');
      res.status(204).send();
      return;
    }
    
    const data = await response.json();
    
    if (!response.ok) {
      res.status(response.status).json(data);
      return;
    }
    
    res.json(data);
    
  } catch (error) {
    req.log.error({ error }, 'Failed to proxy credential deletion to Auth Service');
    res.status(500).json({ error: 'Failed to connect to authentication service' });
  }
});

/**
 * GET /bff/auth/oauth/authorize?credential_id=xxx
 * Get OAuth authorization URL for a specific credential
 * Returns JSON for frontend to handle redirect
 */
router.get('/oauth/authorize', async (req, res) => {
  try {
    const credentialId = req.query.credential_id;
    
    if (!credentialId || typeof credentialId !== 'string') {
      res.status(400).json({ error: 'credential_id query parameter required' });
      return;
    }
    
    // Proxy to Auth Service to get OAuth authorization URL
    const authUrl = `${AUTH_SERVICE_URL}/auth/oauth/authorize?credential_id=${credentialId}`;
    
    req.log.info({ credentialId }, 'Getting OAuth authorization URL for credential');
    
    const response = await fetch(authUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      }
    });
    
    if (!response.ok) {
      const error = await response.text();
      req.log.error({ status: response.status, error }, 'Failed to get authorization URL from Auth service');
      res.status(response.status).json({ error: 'Failed to get authorization URL' });
      return;
    }
    
    const data = await response.json();
    
    // Return the authorization URL to frontend
    res.json(data);
    
  } catch (error) {
    req.log.error({ error }, 'Failed to get OAuth authorization URL');
    res.status(500).json({ error: 'Failed to connect to authentication service' });
  }
});

/**
 * GET /bff/auth/oauth/callback
 * OAuth callback handler - receives code and state from provider
 * Forwards to Auth Service for token exchange
 */
router.get('/oauth/callback', async (req, res) => {
  try {
    const error = req.query.error;
    
    // Forward all query params to Auth Service
    const queryParams = new URLSearchParams(req.query as Record<string, string>).toString();
    const authUrl = `${AUTH_SERVICE_URL}/auth/oauth/callback?${queryParams}`;
    
    // Proxy the request
    const response = await fetch(authUrl, {
      method: 'GET',
      redirect: 'manual', // Don't follow redirects
    });
    
    // Get redirect location from Auth Service (should redirect to UI)
    const location = response.headers.get('location');
    
    if (location) {
      req.log.info({ hasError: !!error }, 'OAuth callback processed, redirecting to UI');
      res.redirect(location);
    } else {
      res.status(500).send('OAuth callback processing failed');
    }
    
  } catch (error) {
    req.log.error({ error }, 'Failed to process OAuth callback');
    res.status(500).send('Failed to process OAuth callback');
  }
});

export default router;
