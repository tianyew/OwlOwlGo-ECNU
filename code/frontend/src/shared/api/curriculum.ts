import { request } from './learning';
export interface Unit {
  id: string; title: string; goal: string; words: string; example: string; task: string;
  grammar: string; dialogue: string[]; practices: string[]; quiz_id: string;
}
export interface Topic {
  id: string; title: string; english: string; description: string; units: Unit[];
  schedule: string; posttest_id: string;
}
export interface Diagnosis { score: number; correct: number; advice: string }
export const curriculumApi = { load: () => request<{ content_version: number; topics: Topic[] }>('curriculum') };
