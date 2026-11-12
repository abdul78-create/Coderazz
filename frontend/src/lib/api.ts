/**
 * CodeRazz Typed API Client
 * Zero-cost, resilient HTTP client wrapper for backend API communication.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type UserRole = "STUDENT" | "TEACHER" | "ANNOTATOR" | "ADMIN";

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: UserProfile;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name: string;
  role?: "STUDENT" | "TEACHER";
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface DatabaseStatus {
  status: "connected" | "unhealthy" | "disconnected";
  mode: "postgresql" | "sqlite";
  dialect: string;
  driver: string;
  version?: string;
  error?: string;
}

export interface HealthResponse {
  status: "healthy" | "degraded" | "down";
  app: string;
  environment: string;
  version: string;
  database: DatabaseStatus;
}

export interface PingResponse {
  message: string;
  app: string;
  version: string;
  timestamp: string;
}

export interface MessageResponse {
  message: string;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public details?: unknown
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/**
 * Perform a typed request to the CodeRazz backend.
 */
async function fetchFromApi<T>(
  endpoint: string,
  options?: RequestInit,
  token?: string | null
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  try {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options?.headers as Record<string, string> || {}),
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const res = await fetch(url, {
      ...options,
      headers,
      cache: "no-store",
    });

    if (!res.ok) {
      const errorBody = await res.json().catch(() => null);
      const detailMsg =
        errorBody && typeof errorBody.detail === "string"
          ? errorBody.detail
          : res.statusText;
      throw new ApiError(detailMsg, res.status, errorBody);
    }

    return (await res.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      `Network error connecting to CodeRazz backend at ${url}: ${(error as Error).message}`
    );
  }
}

export const api = {
  /**
   * Check backend health and database connectivity.
   */
  async getHealth(): Promise<HealthResponse> {
    return fetchFromApi<HealthResponse>("/health");
  },

  /**
   * Diagnostic ping test to /api/v1/ping.
   */
  async ping(): Promise<PingResponse> {
    return fetchFromApi<PingResponse>("/api/v1/ping");
  },

  /**
   * Register a new student or teacher account.
   */
  async register(payload: RegisterPayload): Promise<UserProfile> {
    return fetchFromApi<UserProfile>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  /**
   * Authenticate with email and password to receive JWT and refresh tokens.
   */
  async login(payload: LoginPayload): Promise<TokenResponse> {
    return fetchFromApi<TokenResponse>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  /**
   * Exchange a valid refresh token for a newly rotated token pair.
   */
  async refreshToken(refreshToken: string): Promise<TokenResponse> {
    return fetchFromApi<TokenResponse>("/api/v1/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
  },

  /**
   * Invalidate active session and revoke refresh token.
   */
  async logout(refreshToken?: string | null, accessToken?: string | null): Promise<MessageResponse> {
    return fetchFromApi<MessageResponse>(
      "/api/v1/auth/logout",
      {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken || null }),
      },
      accessToken
    );
  },

  /**
   * Fetch current authenticated user's profile.
   */
  async getMe(accessToken: string): Promise<UserProfile> {
    return fetchFromApi<UserProfile>("/api/v1/auth/me", {}, accessToken);
  },

  /**
   * Probe RBAC protected endpoint for the given role.
   */
  async testRoleProbe(
    role: "student" | "teacher" | "annotator" | "admin",
    accessToken: string
  ): Promise<MessageResponse> {
    return fetchFromApi<MessageResponse>(
      `/api/v1/auth/role-test/${role}`,
      {},
      accessToken
    );
  },
};
