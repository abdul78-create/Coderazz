/**
 * CodeRazz Typed API Client
 * Zero-cost, resilient HTTP client wrapper for backend API communication.
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

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
  expires_in_seconds?: number;
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

export type ProblemDifficulty = "EASY" | "MEDIUM" | "HARD";

export interface TestCasePublic {
  id: string;
  order_index: number;
  input_data: string;
  expected_output: string;
  explanation?: string;
}

export interface ProblemListItem {
  id: string;
  slug: string;
  title: string;
  difficulty: ProblemDifficulty;
  category: string;
  order_index: number;
  is_published: boolean;
  sample_cases_count: number;
  total_cases_count: number;
}

export interface ProblemDetail {
  id: string;
  slug: string;
  title: string;
  description: string;
  difficulty: ProblemDifficulty;
  category: string;
  starter_code: string;
  time_limit_ms: number;
  memory_limit_mb: number;
  order_index: number;
  sample_test_cases: TestCasePublic[];
}

export type SubmissionVerdict =
  | "ACCEPTED"
  | "WRONG_ANSWER"
  | "RUNTIME_ERROR"
  | "TIME_LIMIT_EXCEEDED"
  | "MEMORY_LIMIT_EXCEEDED"
  | "OUTPUT_LIMIT_EXCEEDED"
  | "COMPILATION_ERROR"
  | "SANDBOX_ERROR"
  | "PENDING";

export interface TestCaseResult {
  test_case_id?: string;
  order_index: number;
  is_hidden: boolean;
  passed: boolean;
  verdict: SubmissionVerdict;
  runtime_ms: number;
  memory_kb: number;
  input_data?: string;
  expected_output?: string;
  actual_output?: string;
  stderr?: string;
  explanation?: string;
}

export interface DiagnosisResult {
  id?: string;
  misconception_code: string;
  misconception_name?: string;
  misconception_category?: string;
  confidence_score: number;
  detector_type: string;
  is_primary?: boolean;
  evidence_lines?: number[];
  explanation?: string;
  pedagogical_remedy?: string;
  secondary_candidates?: Array<{
    code: string;
    confidence: number;
    detector?: string;
    explanation?: string;
  }>;
}

export interface CodeRunResult {
  verdict: SubmissionVerdict;
  stdout: string;
  stderr: string;
  runtime_ms: number;
  memory_kb: number;
  test_cases_passed: number;
  total_test_cases: number;
  error_message?: string;
  test_cases: TestCaseResult[];
  diagnosis?: DiagnosisResult;
}

export interface SubmissionRecord {
  id: string;
  problem_id: string;
  user_id: string;
  code: string;
  language: string;
  status: string;
  verdict: SubmissionVerdict;
  runtime_ms?: number;
  memory_kb?: number;
  test_cases_passed: number;
  total_test_cases: number;
  stdout?: string;
  stderr?: string;
  error_message?: string;
  created_at: string;
  problem_title?: string;
  problem_slug?: string;
  diagnosis?: DiagnosisResult;
  diagnoses?: DiagnosisResult[];
}

export interface SubmissionListItem {
  id: string;
  problem_id: string;
  problem_title: string;
  problem_slug: string;
  verdict: SubmissionVerdict;
  status: string;
  runtime_ms?: number;
  test_cases_passed: number;
  total_test_cases: number;
  created_at: string;
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
      ...((options?.headers as Record<string, string>) || {}),
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
  async logout(
    refreshToken?: string | null,
    accessToken?: string | null
  ): Promise<MessageResponse> {
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

  /**
   * Retrieve list of programming problems.
   */
  async getProblems(params?: {
    difficulty?: string;
    category?: string;
  }): Promise<ProblemListItem[]> {
    let query = "";
    if (params) {
      const q = new URLSearchParams();
      if (params.difficulty) q.append("difficulty", params.difficulty);
      if (params.category) q.append("category", params.category);
      if (q.toString()) query = `?${q.toString()}`;
    }
    return fetchFromApi<ProblemListItem[]>(`/api/v1/problems${query}`);
  },

  /**
   * Retrieve details and visible sample test cases for a problem.
   */
  async getProblem(idOrSlug: string): Promise<ProblemDetail> {
    return fetchFromApi<ProblemDetail>(`/api/v1/problems/${idOrSlug}`);
  },

  /**
   * Run code interactively against sample test cases in the sandbox.
   */
  async runCode(
    payload: { code: string; problem_id?: string; custom_input?: string },
    token: string
  ): Promise<CodeRunResult> {
    return fetchFromApi<CodeRunResult>(
      "/api/v1/submissions/run",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
      token
    );
  },

  /**
   * Submit code for final grading against all hidden test cases.
   */
  async submitCode(
    payload: { problem_id: string; code: string; language?: string },
    token: string
  ): Promise<SubmissionRecord> {
    return fetchFromApi<SubmissionRecord>(
      "/api/v1/submissions",
      {
        method: "POST",
        body: JSON.stringify(payload),
      },
      token
    );
  },

  /**
   * Retrieve submission history for the authenticated user.
   */
  async getSubmissions(
    token: string,
    problemId?: string
  ): Promise<SubmissionListItem[]> {
    const q = problemId ? `?problem_id=${problemId}` : "";
    return fetchFromApi<SubmissionListItem[]>(
      `/api/v1/submissions${q}`,
      {},
      token
    );
  },

  /**
   * Retrieve details for a single submission.
   */
  async getSubmission(
    submissionId: string,
    token: string
  ): Promise<SubmissionRecord> {
    return fetchFromApi<SubmissionRecord>(
      `/api/v1/submissions/${submissionId}`,
      {},
      token
    );
  },
};
