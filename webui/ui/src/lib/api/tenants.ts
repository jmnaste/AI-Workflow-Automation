// Tenants API Client

export interface Tenant {
  id: string;
  provider: string;
  externalTenantId: string;
  externalAccountId: string;
  displayName: string;
  metadata?: Record<string, any>;
  createdAt: string;
  updatedAt: string;
  lastRefreshedAt?: string;
}

/**
 * List all connected tenants (admin only)
 */
export async function listTenants(): Promise<Tenant[]> {
  const response = await fetch('/bff/auth/tenants', {
    method: 'GET',
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to fetch tenants' }));
    throw new Error(error.message || `HTTP ${response.status}`);
  }

  const data = await response.json();
  return data.tenants || [];
}

/**
 * Start OAuth flow for connecting a tenant
 * Returns the authorization URL to redirect to
 */
export async function startOAuthFlow(provider: 'ms365' | 'google'): Promise<string> {
  const response = await fetch(`/bff/auth/oauth/${provider}/authorize`, {
    method: 'GET',
    credentials: 'include',
    redirect: 'manual', // Don't follow redirects automatically
  });

  if (response.type === 'opaqueredirect') {
    // Extract redirect URL from response
    return response.url;
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to start OAuth flow' }));
    throw new Error(error.message || `HTTP ${response.status}`);
  }

  const data = await response.json();
  return data.authUrl;
}

/**
 * Disconnect a tenant (delete credentials)
 */
export async function disconnectTenant(tenantId: string): Promise<void> {
  const response = await fetch(`/bff/auth/tenants/${tenantId}`, {
    method: 'DELETE',
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to disconnect tenant' }));
    throw new Error(error.message || `HTTP ${response.status}`);
  }
}

/**
 * Refresh tenant tokens (force refresh)
 */
export async function refreshTenantToken(tenantId: string): Promise<void> {
  const response = await fetch(`/bff/auth/tenants/${tenantId}/refresh`, {
    method: 'POST',
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to refresh token' }));
    throw new Error(error.message || `HTTP ${response.status}`);
  }
}
