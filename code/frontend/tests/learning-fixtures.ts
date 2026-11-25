import { vi } from 'vitest';
import { nextTick } from 'vue';
import bank from '../../backend/app/domain/content/curriculum.json';
import assessmentItems from '../../backend/app/domain/learner/assessment_items.json';
import { curriculumApi, type Topic } from '../src/shared/api/curriculum';
import { learningApi, emptyState, emptyQuiz, type LearnerProfile, type Quiz, type QuizAnswer, type QuizResult, type SavedProgress } from '../src/shared/api/learning';

export const topics: Topic[] = bank.topics.map(topic => ({
  id: topic.id, title: topic.title, english: topic.english, description: topic.description,
  schedule: '每次学习一个单元。', posttest_id: `post-${topic.id}`,
  units: topic.units.map((unit, index) => ({
    id: unit.id, title: unit.title, goal: unit.goal, words: unit.words, example: unit.example,
    task: unit.task, grammar: unit.grammar, dialogue: unit.dialogue, practices: unit.practices,
    quiz_id: `unit-${topic.id}-${index}`,
  })),
}));
interface RawQuestion { id: string; prompt: string; options: string[]; category: string; answer: number; explanation: string; example?: string; subtitle?: string }
export function rawQuestions(id: string): RawQuestion[] {
  if (id === 'assessment') return assessmentItems;
  const topic = bank.topics.find(t => id.includes(t.id))!;
  return id.startsWith('post-') ? topic.posttest : topic.units[Number(id.split('-').at(-1))].quiz;
}
export function quizFixture(id: string): Quiz {
  const kind = id === 'assessment' ? 'assessment' : id.startsWith('post-') ? 'posttest' : 'unit';
  const topic = topics.find(t => id.includes(t.id));
  const title = kind === 'assessment' ? '拼音与声调前测' : kind === 'posttest' ? `${topic!.title} · 方向后测` : `${topic!.units[Number(id.split('-').at(-1))].title} · 单元小测`;
  return { id, kind, title, content_version: 1, draft: null, result: null, unit_completed: false,
    questions: rawQuestions(id).map(q => ({ id: q.id, prompt: q.prompt, options: q.options, category: q.category, example: q.example, subtitle: q.subtitle })) };
}
export function resultFixture(id: string, answers?: QuizAnswer[], score = 100): QuizResult {
  const quiz = quizFixture(id);
  const topic = topics.find(t => id.includes(t.id));
  return {
    submission_id: `result-${id}`, content_version: 1, created_at: '2026-11-09T00:00:00Z', scoring_version: 'objective-v2',
    quiz_id: id, kind: quiz.kind, topic: topic?.id ?? null, unit_index: quiz.kind === 'unit' ? Number(id.split('-').at(-1)) : null,
    score, correct: Math.round(rawQuestions(id).length * score / 100), total: rawQuestions(id).length, passed: quiz.kind === 'assessment' || score >= (quiz.kind === 'unit' ? 100 : 60),
    items: rawQuestions(id).map(q => {
      const selected = answers?.find(a => a.question_id === q.id)?.selected_index ?? q.answer;
      return { question_id: q.id, selected_index: selected, correct_index: q.answer, is_correct: selected === q.answer, prompt: q.prompt, options: q.options, category: q.category, explanation: q.explanation };
    }),
  };
}
export function profileFixture(count = 0): LearnerProfile {
  const stats = { score: count ? 75 : null, latest_score: count ? 100 : null, evidence_count: count, correct: 0, latest_correct: 0, attempt_count: count, repeat_count: 0, evidence_status: count ? 'emerging' : 'unmeasured', confidence: 0 };
  const blank = { ...stats, score: null, latest_score: null, evidence_count: 0, attempt_count: 0, evidence_status: 'unmeasured' };
  return { ...stats, policy_version: 'first-evidence-v1', submission_count: count ? 1 : 0,
    scope: '首次作答正确率；文字选择题不评定实际听说或汉语等级。', focus_areas: [], next_steps: ['继续学习不同题目。'], knowledge_points: [],
    matrix: ['拼音与声调', '词汇与句式', '功能性阅读', '非连续性文本信息处理', '古诗理解', '文言文理解', '书面表达与修改'].map((name, i) => ({ ...(i === 0 ? stats : blank), dimension: `dimension-${i}`, name,
      cells: ['记忆','理解','应用','分析','评价','创造'].map((cell, j) => ({ ...(i === 0 && j === 0 ? stats : blank), bloom: `bloom-${j}`, name: cell })) })),
  };
}
export function savedFixture(): SavedProgress {
  return { revision: 0, state: emptyState(), updated_at: null, analysis: null, results: {}, profile: profileFixture(), topic_completion: {} };
}
export function withAssessment(saved: SavedProgress, topic?: string) {
  const result = resultFixture('assessment');
  saved.results.assessment = result;
  const answers = result.items.map(item => item.selected_index);
  saved.state.quiz = { stage: 'result', current: 7, selected: answers[7], submitted: true, answers };
  saved.profile = profileFixture(8);
  if (topic) { saved.state.topic = topic; saved.state.stage = 'plan'; }
  return saved;
}
export function installLearning(initial = savedFixture()) {
  const store = { saved: structuredClone(initial) };
  const submissions = new Map(Object.values(initial.results).map(result => [result.submission_id, result]));
  vi.spyOn(learningApi, 'report').mockImplementation(async id => {
    const result = submissions.get(id);
    if (!result || result.kind !== 'posttest') throw new Error('Missing posttest');
    const topic = result.topic ?? '';
    return {
      result: structuredClone(result),
      completed_units: (store.saved.state.completed[topic] ?? []).length,
      topic_completion: store.saved.topic_completion[topic] ?? false,
      profile: structuredClone(store.saved.profile),
    };
  });
  vi.spyOn(curriculumApi, 'load').mockImplementation(async () => ({ content_version: 1, topics: structuredClone(topics) }));
  vi.spyOn(learningApi, 'load').mockImplementation(async () => structuredClone(store.saved));
  vi.spyOn(learningApi, 'save').mockImplementation(async (state, revision) => {
    store.saved = { ...store.saved, state: structuredClone(state), revision: revision + 1, updated_at: 'today' };
    return structuredClone(store.saved);
  });
  vi.spyOn(learningApi, 'analyze').mockRejectedValue(new Error('学习建议暂不可用'));
  vi.spyOn(learningApi, 'quiz').mockImplementation(async id => ({ ...quizFixture(id), result: structuredClone(store.saved.results[id] ?? null), draft: structuredClone(store.saved.state.drafts[id] ?? null), unit_completed: id.startsWith('unit-') && (store.saved.state.completed[id.split('-')[1]] ?? []).includes(Number(id.split('-')[2])) }));
  vi.spyOn(learningApi, 'submit').mockImplementation(async (id, body, revision) => {
    const result = resultFixture(id, body.answers);
    result.submission_id = body.submission_id;
    submissions.set(result.submission_id, result);
    store.saved.results[id] = result; store.saved.revision = revision + 1;
    delete store.saved.state.drafts[id];
    if (id === 'assessment') withAssessment(store.saved);
    if (result.kind === 'unit') store.saved.state.completed[result.topic!] = [...new Set([...(store.saved.state.completed[result.topic!] ?? []), result.unit_index!])];
    store.saved.results[id] = result;
    store.saved.profile = profileFixture(8 + result.total);
    return { result: structuredClone(result), progress: structuredClone(store.saved) };
  });
  vi.spyOn(learningApi, 'reset').mockImplementation(async revision => {
    delete store.saved.results.assessment; delete store.saved.state.drafts.assessment;
    store.saved.state.quiz = emptyQuiz(); store.saved.state.stage = 'assessment';
    store.saved.state.topic = null; store.saved.state.onboarding_complete = false;
    store.saved.analysis = null; store.saved.revision = revision + 1;
    return structuredClone(store.saved);
  });
  return store;
}
export async function settle() { for (let i = 0; i < 40; i++) await nextTick(); }
export async function click(host: HTMLElement, text: string) {
  const button = [...host.querySelectorAll('button')].find(b => b.textContent?.includes(text));
  if (!button) throw new Error(`Missing button: ${text}`);
  button.click(); await settle();
}
export async function answerQuiz(host: HTMLElement, id: string) {
  const questions = rawQuestions(id);
  for (const [index, question] of questions.entries()) {
    const fieldset = id.startsWith('unit-') ? host.querySelectorAll('.practice-question')[index] : host.querySelector('.practice-question');
    (fieldset!.querySelectorAll('input')[question.answer] as HTMLInputElement).click(); await settle();
    if (!id.startsWith('unit-') && index < questions.length - 1) await click(host, '下一题');
  }
  await click(host, '提交答案');
}
