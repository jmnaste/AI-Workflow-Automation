// Minimal OIDC auth stub; will be expanded later
export interface AuthSession {
  accessToken?: string
  expiresAt?: number
}

let current: AuthSession = {}

export function getSession(): AuthSession {
  return current
}

export function setSession(s: AuthSession) {
  current = s
}

export function isAuthenticated() {
  return !!current.accessToken && (current.expiresAt ?? 0) > Date.now() + 30_000
}
