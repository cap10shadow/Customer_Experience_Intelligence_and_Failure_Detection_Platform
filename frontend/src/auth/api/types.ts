/**
 * Mirrors gateway_service's `AuthenticatedUserResponse`
 * (backend/services/gateway_service/app/schemas/auth.py) -- the one
 * shape shared by POST /auth/login's success case and GET /auth/me.
 */
export interface AuthenticatedUser {
  userId: string
  email: string
  roles: string[]
}

export interface LoginRequest {
  email: string
  password: string
}
