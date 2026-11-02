import { AuthError } from './auth';
export interface QuizState {
  stage: 'intro' | 'quiz' | 'result'; current: number; selected: number | null;
  submitted: boolean; answers: number[];
}
export interface LearningState {
  checks?: Record<string, { answers: number[]; submitted: boolean }>;
  posttests?: Record<string, { answers: number[]; submitted: boolean }>;
  onboarding_complete?: boolean;
  content_version: 1; stage: 'assessment' | 'topics' | 'plan'; quiz: QuizState;
  topic: string | null; completed: Record<string, number[]>;
}
export interface Analysis {
  prompt_version: string;
  question_feedback: { question_id: string; observation: string; suggestion: string }[];
  practice_tasks: { title: string; reason: string; question_ids: string[]; activity: string; success_criterion: string }[];
  provider: string; model: string; created_at: string; summary: string;
  strengths: string[]; focus_areas: string[]; next_steps: string[];
}
export interface SavedProgress {
  revision: number; state: LearningState; updated_at: string | null; analysis: Analysis | null;
}
export function emptyQuiz(): QuizState {
  return { stage: 'intro', current: 0, selected: null, submitted: false, answers: [] };
}
async function request<T>(path: string, method = 'GET', body?: object): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/v1/learning/${path}`, { method, credentials: 'same-origin',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined });
  } catch { throw new AuthError('无法连接服务，进度尚未保存。请重试。', 0); }
  const result = await response.json().catch(() => null);
  if (!response.ok) throw new AuthError(typeof result?.detail === 'string' ? result.detail : '服务暂不可用，请重试。', response.status);
  return result;
}
export const learningApi = {
  load: () => request<SavedProgress>('progress'),
  save: (state: LearningState, revision: number) => request<SavedProgress>('progress', 'PUT', { state, revision }),
  analyze: () => request<Analysis>('analysis', 'POST'),
};
