import type { ResearchJob, ResearchSummary, TokenResponse, User } from "./types";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

const ACCESS_TOKEN_KEY = "researchai_access_token";
const REFRESH_TOKEN_KEY = "researchai_refresh_token";

export const tokenStorage = {
  getAccessToken: () => localStorage.getItem(ACCESS_TOKEN_KEY),
  getRefreshToken: () => localStorage.getItem(REFRESH_TOKEN_KEY),
  setTokens: (tokens: TokenResponse) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  },
  clear: () => {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
  },
};

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function parseErrorDetail(res: Response): Promise<string> {
  try {
    const body = await res.json();
    if (typeof body.detail === "string") return body.detail;
    if (Array.isArray(body.detail)) {
      // FastAPI/Pydantic validation error shape: [{..., msg: string}, ...]
      const messages = body.detail.map((d: { msg?: string }) => d.msg).filter(Boolean);
      if (messages.length > 0) return messages.join("; ");
    }
    return res.statusText;
  } catch {
    return res.statusText;
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  auth?: boolean;
  /** internal: prevents infinite refresh-retry loops */
  _retried?: boolean;
}

async function tryRefresh(): Promise<boolean> {
  const refreshToken = tokenStorage.getRefreshToken();
  if (!refreshToken) return false;

  try {
    const res = await fetch(`${BASE_URL}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return false;
    tokenStorage.setTokens((await res.json()) as TokenResponse);
    return true;
  } catch {
    return false;
  }
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true, _retried = false } = options;

  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (auth) {
    const token = tokenStorage.getAccessToken();
    if (token) headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  // An expired access token gets one silent refresh-and-retry before
  // giving up — avoids bouncing the user to /login on every 30-minute
  // token expiry while they're mid-session.
  if (res.status === 401 && auth && !_retried) {
    if (await tryRefresh()) {
      return request<T>(path, { ...options, _retried: true });
    }
    tokenStorage.clear();
  }

  if (!res.ok) {
    throw new ApiError(res.status, await parseErrorDetail(res));
  }

  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  register: (email: string, password: string) =>
    request<User>("/auth/register", { method: "POST", body: { email, password }, auth: false }),

  login: async (email: string, password: string): Promise<TokenResponse> => {
    const tokens = await request<TokenResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    });
    tokenStorage.setTokens(tokens);
    return tokens;
  },

  me: () => request<User>("/auth/me"),

  createResearch: (company: string) =>
    request<ResearchJob>("/research", { method: "POST", body: { company } }),

  getResearch: (id: string) => request<ResearchJob>(`/research/${id}`),

  listResearch: () => request<ResearchSummary[]>("/research"),
};
