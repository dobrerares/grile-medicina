import type {
  AnswerResult,
  AvailableCounts,
  BugReport,
  GrileInfo,
  HistorySession,
  PdfFile,
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

// --- Bug Reports (user) ---

export async function submitReport(data: FormData): Promise<{ status: string; id: number }> {
  const token = getToken();
  const headers: Record<string, string> = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch("/api/reports", {
    method: "POST",
    headers,
    body: data,
  });
  if (res.status === 401) {
    clearToken();
    window.location.href = "/login";
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }
  return res.json();
}

// --- Admin ---

export async function getGrileInfo(): Promise<GrileInfo> {
  return api.get("/admin/grile-info");
}

export async function uploadGrile(file: File): Promise<{ status: string; total_questions: number; source_count: number }> {
  const token = getToken();
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/admin/upload-grile", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed (${res.status})`);
  }
  return res.json();
}

export async function getAdminPdfs(): Promise<PdfFile[]> {
  return api.get("/admin/pdfs");
}

export async function uploadPdf(file: File): Promise<{ status: string; filename: string }> {
  const token = getToken();
  const form = new FormData();
  form.append("file", file);
  const res = await fetch("/api/admin/upload-pdf", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed (${res.status})`);
  }
  return res.json();
}

export async function adminDeletePdf(filename: string): Promise<{ status: string }> {
  const token = getToken();
  const res = await fetch(`/api/admin/pdf/${encodeURIComponent(filename)}`, {
    method: "DELETE",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Delete failed (${res.status})`);
  }
  return res.json();
}

export async function getAdminReports(status?: string): Promise<BugReport[]> {
  const query = status ? `?status=${status}` : "";
  return api.get(`/admin/reports${query}`);
}

export async function resolveReport(id: number): Promise<{ status: string }> {
  const token = getToken();
  const res = await fetch(`/api/admin/reports/${id}`, {
    method: "PATCH",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed (${res.status})`);
  }
  return res.json();
}

export async function deleteReport(id: number): Promise<{ status: string }> {
  const token = getToken();
  const res = await fetch(`/api/admin/reports/${id}`, {
    method: "DELETE",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Failed (${res.status})`);
  }
  return res.json();
}

export default api;
