export interface Question {
  id: string;
  number: number;
  type: "complement_simplu" | "complement_grupat";
  text: string;
  choices: Record<string, string>;
  correct_answer?: string;
  correct_statements?: number[] | null;
  page_ref?: string;
  source_file?: string;
}

export interface QuizSession {
  id: number;
  started_at: string;
  completed_at?: string;
  filters: unknown;
  session_type: string;
}

export interface SessionQuestion {
  session_question_id: number;
  question_id: string;
  position: number;
  type: string;
  text: string;
  choices: Record<string, string>;
  topic?: string;
  year?: number;
  source_file?: string;
  page_ref?: string;
  answered: boolean;
  user_answer?: string;
}

export interface QuizDetail {
  session_id: number;
  session_type: string;
  started_at: string;
  completed_at?: string;
  question_count: number;
  questions: SessionQuestion[];
}

export interface AnswerResult {
  is_correct: boolean;
  correct_answer: string;
  correct_statements?: number[];
}

export interface Source {
  file: string;
  year: number;
  cs_count: number;
  cg_count: number;
  total: number;
}

export interface Topic {
  topic: string;
  cs_count: number;
  cg_count: number;
  total: number;
}

export interface Stats {
  total_answered: number;
  total_correct: number;
  accuracy: number;
  by_topic: Record<
    string,
    { total: number; correct: number; accuracy: number }
  >;
  by_year: Record<
    string,
    { total: number; correct: number; accuracy: number }
  >;
}

export interface HistorySession {
  session_id: number;
  started_at: string;
  completed_at?: string;
  session_type: string;
  total_questions: number;
  answered: number;
  correct: number;
  accuracy: number;
}

export interface User {
  id: number;
  username: string;
}

export interface AvailableCounts {
  cs_available: number;
  cg_available: number;
  total_available: number;
}

export interface WeakQuestion {
  question_id: string;
  text: string;
  topic?: string;
  year?: number;
  type?: string;
  total_attempts: number;
  wrong_count: number;
  error_rate: number;
}
