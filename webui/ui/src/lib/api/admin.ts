// Admin API Client

export interface AdminUser {
  id: string;
  email: string;
  phone?: string;
  role: 'user' | 'admin' | 'super-user';
  isActive: boolean;
  verifiedAt?: string;
  createdAt?: string;
  lastLoginAt?: string;
}

export interface ListUsersResponse {
  users: AdminUser[];
  total: number;
  page: number;
  limit: number;
}

export interface UpdateUserRequest {
  email?: string;
  phone?: string;
  preference?: 'sms' | 'email' | 'none';
  role?: 'user' | 'admin' | 'super-user';
  isActive?: boolean;
}

export interface UpdateUserResponse {
  success: boolean;
  message: string;
  user: AdminUser;
}

export interface SystemSettings {
  otpExpiry: number;
  otpMaxAttempts: number;
  rateLimitWindow: number;
  rateLimitMaxRequests: number;
}

/**
 * List all users (admin only)
 */
export async function listUsers(params?: {
  page?: number;
  limit?: number;
  search?: string;
}): Promise<ListUsersResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.append('page', params.page.toString());
  if (params?.limit) searchParams.append('limit', params.limit.toString());
  if (params?.search) searchParams.append('search', params.search);

  const url = `/bff/admin/users${searchParams.toString() ? '?' + searchParams.toString() : ''}`;
  const response = await fetch(url, {
    credentials: 'include',
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to list users');
  }
  
  return response.json();
}

/**
 * Create a new user (admin only)
 */
export async function createUser(userData: {
  email: string;
  phone?: string;
  preference?: 'sms' | 'email';
  role?: 'user' | 'admin' | 'super-user';
}): Promise<UpdateUserResponse> {
  const response = await fetch('/bff/admin/users', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData),
    credentials: 'include',
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || error.error || 'Failed to create user');
  }
  
  return response.json();
}

/**
 * Update user role or status (admin only)
 */
export async function updateUser(userId: string, updates: UpdateUserRequest): Promise<UpdateUserResponse> {
  const response = await fetch(`/bff/admin/users/${userId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
    credentials: 'include',
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to update user');
  }
  
  return response.json();
}

/**
 * Delete user (admin only)
 */
export async function deleteUser(userId: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`/bff/admin/users/${userId}`, {
    method: 'DELETE',
    credentials: 'include',
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to delete user');
  }
  
  return response.json();
}

/**
 * Get system settings (admin only)
 */
export async function getSystemSettings(): Promise<SystemSettings> {
  const response = await fetch('/bff/admin/settings', {
    credentials: 'include',
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to get system settings');
  }
  
  return response.json();
}

/**
 * Update system settings (admin only)
 */
export async function updateSystemSettings(settings: SystemSettings): Promise<SystemSettings> {
  const response = await fetch('/bff/admin/settings', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(settings),
    credentials: 'include',
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error || 'Failed to update system settings');
  }
  
  return response.json();
}
