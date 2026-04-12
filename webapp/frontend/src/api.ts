import type {
  AnswerResult,
  AvailableCounts,
  HistorySession,
  QuizDetail,
  Source,
  Stats,
  Topic,
  User,
  WeakQuestion,
} from "./types";

const TOKEN_KEY = "grile_token";

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown
): Promise<T> {
  const headers: Record<string, string> = {};
  const token = getToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const res = await fetch(`/api${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }

  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new Error(data.detail || `Request failed (${res.status})`);
  }

  return res.json() as Promise<T>;
}

const api = {
  get<T>(path: string): Promise<T> {
    return request<T>("GET", path);
  },
  post<T>(path: string, body?: unknown): Promise<T> {
    return request<T>("POST", path, body);
  },
};

// --- Auth ---

export async function login(
  username: string,
  password: string
): Promise<{ token: string; user: User }> {
  return api.post("/auth/login", { username, password });
}

export async function register(
  username: string,
  password: string,
  inviteCode: string
): Promise<{ token: string; user: User }> {
  return api.post("/auth/register", { username, password, invite_code: inviteCode });
}

export async function getMe(): Promise<User> {
  return api.get("/auth/me");
}

// --- Data ---

export async function getSources(): Promise<Source[]> {
  return api.get("/sources");
}

export async function getTopics(): Promise<Topic[]> {
  return api.get("/topics");
}

export async function getAvailableCounts(filters: {
  sources?: string[];
  years?: number[];
  topics?: string[];
}): Promise<AvailableCounts> {
  return api.post("/quiz/available-counts", filters);
}

// --- Quiz ---

export async function generateQuiz(params: {
  sources?: string[];
  years?: number[];
  topics?: string[];
  cs_count: number;
  cg_count: number;
}): Promise<{ session_id: number; question_count: number }> {
  return api.post("/quiz/generate", params);
}

export async function generateReviewQuiz(params: {
  count?: number;
  topics?: string[];
}): Promise<{ session_id: number; question_count: number }> {
  return api.post("/quiz/review", params);
}

export async function getQuiz(sessionId: number): Promise<QuizDetail> {
  return api.get(`/quiz/${sessionId}`);
}

export async function submitAnswer(
  sessionId: number,
  questionId: string,
  answer: string,
  timeMs?: number
): Promise<AnswerResult> {
  return api.post(`/quiz/${sessionId}/answer`, {
    question_id: questionId,
    answer,
    time_spent_ms: timeMs,
  });
}

export async function completeQuiz(sessionId: number): Promise<unknown> {
  return api.post(`/quiz/${sessionId}/complete`);
}

// --- Stats ---

export async function getStats(): Promise<Stats> {
  return api.get("/stats");
}

export async function getHistory(): Promise<HistorySession[]> {
  return api.get("/stats/history");
}

export async function getWeakest(): Promise<WeakQuestion[]> {
  return api.get("/stats/weakest");
}

export default api;
