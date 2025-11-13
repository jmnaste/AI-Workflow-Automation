// Credentials API Client

export interface Credential {
  id: string;
  name: string;
  display_name: string;
  provider: string;
  client_id: string;
  redirect_uri: string;
  authorization_url: string;
  token_url: string;
  scopes: string[];
  connected_email?: string;
  external_account_id?: string;
  connected_display_name?: string;
  status: 'pending' | 'connected' | 'error';
  error_message?: string;
  last_connected_at?: string;
  created_at: string;
  created_by?: string;
  updated_at: string;
}

export interface CreateCredentialRequest {
  name: string;
  display_name: string;
  provider: 'ms365' | 'google_workspace';
  client_id: string;
  client_secret: string;
  redirect_uri: string;
  authorization_url?: string;
  token_url?: string;
  scopes?: string[];
}

/**
 * List all credentials (admin only)
 */
export async function listCredentials(): Promise<Credential[]> {
  const response = await fetch('/bff/auth/credentials', {
    method: 'GET',
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to fetch credentials' }));
    throw new Error(error.message || `HTTP ${response.status}`);
  }

  return await response.json();
}

/**
 * Get a specific credential by ID (admin only)
 */
export async function getCredential(credentialId: string): Promise<Credential> {
  const response = await fetch(`/bff/auth/credentials/${credentialId}`, {
    method: 'GET',
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to fetch credential' }));
    throw new Error(error.message || `HTTP ${response.status}`);
  }

  return await response.json();
}

/**
 * Create a new credential (admin only)
 * Returns the created credential in 'pending' status
 */
export async function createCredential(request: CreateCredentialRequest): Promise<Credential> {
  const response = await fetch('/bff/auth/credentials', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to create credential' }));
    throw new Error(error.message || `HTTP ${response.status}`);
  }

  return await response.json();
}

/**
 * Update an existing credential (admin only)
 */
export async function updateCredential(
  credentialId: string,
  request: Partial<CreateCredentialRequest>
): Promise<Credential> {
  const response = await fetch(`/bff/auth/credentials/${credentialId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    credentials: 'include',
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to update credential' }));
    throw new Error(error.message || `HTTP ${response.status}`);
  }

  return await response.json();
}

/**
 * Delete a credential (admin only)
 * Also deletes associated tokens (CASCADE)
 */
export async function deleteCredential(credentialId: string): Promise<void> {
  const response = await fetch(`/bff/auth/credentials/${credentialId}`, {
    method: 'DELETE',
    credentials: 'include',
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ message: 'Failed to delete credential' }));
    throw new Error(error.message || `HTTP ${response.status}`);
  }
}

/**
 * Start OAuth flow for a specific credential
 * Gets authorization URL from backend and redirects to provider's authorization page
 */
export async function startOAuthFlow(credentialId: string): Promise<void> {
  try {
    const response = await fetch(`/bff/auth/oauth/authorize?credential_id=${credentialId}`, {
      method: 'GET',
      credentials: 'include',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`Failed to get authorization URL: ${response.statusText}`);
    }

    const data = await response.json();
    
    // Redirect to OAuth provider (Microsoft/Google)
    window.location.href = data.authorization_url;
  } catch (error) {
    console.error('Failed to start OAuth flow:', error);
    throw error;
  }
}
