import { AuthError, notifyAuthExpired } from './auth';
export interface QuizState {
  stage: 'intro' | 'quiz' | 'result'; current: number; selected: number | null;
  submitted: boolean; answers: number[];
}
export interface QuizAnswer { question_id: string; selected_index: number }
export interface QuizDraft { content_version: 1; current: number; answers: QuizAnswer[] }
export interface LearningState {
  checks: Record<string, { answers: number[]; submitted: boolean }>;
  posttests: Record<string, { answers: number[]; submitted: boolean }>;
  onboarding_complete: boolean; content_version: 1; stage: 'assessment' | 'topics' | 'plan';
  quiz: QuizState; topic: string | null; completed: Record<string, number[]>;
  drafts: Record<string, QuizDraft>;
}
export interface Analysis {
  prompt_version: string;
  question_feedback: { question_id: string; observation: string; suggestion: string }[];
  practice_tasks: { title: string; reason: string; question_ids: string[]; activity: string; success_criterion: string }[];
  provider: string; model: string; created_at: string; summary: string;
  strengths: string[]; focus_areas: string[]; next_steps: string[];
}
export interface EvidenceStats {
  score: number | null; latest_score: number | null; evidence_count: number; correct: number;
  latest_correct: number; attempt_count: number; repeat_count: number; evidence_status: string; confidence: number;
}
export interface LearnerProfile extends EvidenceStats {
  policy_version: string; submission_count: number; scope: string; focus_areas: string[]; next_steps: string[];
  matrix: (EvidenceStats & { dimension: string; name: string; cells: (EvidenceStats & { bloom: string; name: string })[] })[];
  knowledge_points: (EvidenceStats & { name: string })[];
}
export interface QuizResult {
  submission_id: string; content_version: number; created_at: string | null;
  quiz_id: string; kind: 'assessment' | 'unit' | 'posttest'; topic: string | null; unit_index: number | null;
  scoring_version: string; score: number; correct: number; total: number; passed: boolean;
  items: {
    question_id: string; selected_index: number; correct_index: number; is_correct: boolean;
    prompt: string; options: string[]; category: string; explanation: string;
  }[];
}
export interface SavedProgress {
  revision: number; state: LearningState; updated_at: string | null; analysis: Analysis | null;
  results: Record<string, QuizResult>; profile: LearnerProfile; topic_completion: Record<string, boolean>;
}
export interface Quiz {
  id: string; kind: 'assessment' | 'unit' | 'posttest'; content_version: 1; title: string;
  questions: { id: string; prompt: string; options: string[]; category: string; example?: string; subtitle?: string }[];
  result: QuizResult | null; draft: QuizDraft | null; unit_completed: boolean;
}
export interface QuizSubmission { submission_id: string; content_version: number; answers: QuizAnswer[] }
export interface SubmissionResponse { result: QuizResult; progress: SavedProgress }
export function emptyQuiz(): QuizState {
  return { stage: 'intro', current: 0, selected: null, submitted: false, answers: [] };
}
export function emptyState(): LearningState {
  return { content_version: 1, onboarding_complete: false, stage: 'assessment', quiz: emptyQuiz(),
    topic: null, completed: {}, checks: {}, posttests: {}, drafts: {} };
}
export async function request<T>(path: string, method = 'GET', body?: object): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api/v1/learning/${path}`, { method, credentials: 'same-origin',
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined });
  } catch { throw new AuthError('无法连接服务，本次操作尚未确认。请重试。', 0); }
  const result = await response.json().catch(() => null);
  if (response.status === 401) notifyAuthExpired();
  if (!response.ok) throw new AuthError(typeof result?.detail === 'string' ? result.detail : '服务暂不可用，请重试。', response.status);
  return result;
}
export const learningApi = {
  load: () => request<SavedProgress>('progress'),
  save: (state: LearningState, revision: number) => request<SavedProgress>('progress', 'PUT', { state, revision }),
  analyze: () => request<Analysis>('analysis', 'POST'),
  quiz: (id: string) => request<Quiz>(`quizzes/${encodeURIComponent(id)}`),
  submit: (id: string, body: QuizSubmission, revision: number) =>
    request<SubmissionResponse>(`quizzes/${encodeURIComponent(id)}/submissions`, 'POST', { ...body, revision }),
  reset: (revision: number) => request<SavedProgress>('assessment/reset', 'POST', { revision }),
  profile: () => request<LearnerProfile>('profile'),
};
