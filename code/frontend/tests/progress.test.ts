// @vitest-environment happy-dom
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { createApp, type App } from 'vue';
import LearningJourney from '../src/features/assessment/LearningJourney.vue';
import RootApp from '../src/App.vue';
import { authApi, AuthError } from '../src/shared/api/auth';
import { learningApi, type Analysis } from '../src/shared/api/learning';
import { installLearning, withAssessment, settle, click, answerQuiz } from './learning-fixtures';
let app: App;
let host: HTMLDivElement;
let store: ReturnType<typeof installLearning>;
const feedback: Analysis = { provider: 'deepseek', model: 'test', prompt_version: 'assessment-v5', created_at: 'today', summary: '逐题分析结果', strengths: [], focus_areas: [], next_steps: [], question_feedback: [], practice_tasks: [] };
async function mount(open = true) {
  host = document.createElement('div'); document.body.appendChild(host);
  app = createApp(LearningJourney, { userId: 'user-one' }); app.mount(host); await settle();
  if (open) await click(host, store.saved.state.onboarding_complete ? '继续学习' : '学习设置');
}
function unmount() { app.unmount(); host.remove(); }
beforeEach(() => { store = installLearning(); });
afterEach(() => { app?.unmount(); host?.remove(); vi.restoreAllMocks(); });

it('opens Home for a new account without starting or submitting an assessment', async () => {
  await mount(false);
  expect(host.querySelector('[aria-label="学习首页"]')).not.toBeNull();
  expect(host.textContent).toContain('第一步 · 完成学习设置');
  expect(learningApi.submit).not.toHaveBeenCalled(); expect(learningApi.quiz).not.toHaveBeenCalled();
});
it('saves assessment answers and page position and restores the draft after remount', async () => {
  await mount(); await click(host, '开始测评');
  (host.querySelector('.practice-question input') as HTMLInputElement).click(); await settle();
  await click(host, '下一题');
  expect(store.saved.state.drafts.assessment.answers).toEqual([{ question_id: 'initial', selected_index: 0 }]);
  expect(store.saved.state.drafts.assessment.current).toBe(1);
  expect(store.saved.results.assessment).toBeUndefined();
  unmount(); await mount();
  expect(host.textContent).toContain('第 2 / 8 题');
  expect(host.textContent).toContain('已作答 1 / 8');
});
it('submits pretest choices to the backend before automatically requesting AI analysis', async () => {
  vi.mocked(learningApi.analyze).mockResolvedValue(feedback);
  await mount(); await click(host, '开始测评');
  expect(learningApi.analyze).not.toHaveBeenCalled();
  await answerQuiz(host, 'assessment');
  expect(learningApi.submit).toHaveBeenCalledOnce();
  expect(vi.mocked(learningApi.submit).mock.calls[0][0]).toBe('assessment');
  expect(host.querySelector('.score-circle strong')?.textContent).toBe('100');
  expect(host.textContent).toContain('逐题分析结果');
  expect(learningApi.analyze).toHaveBeenCalledOnce();
  await click(host, '选择学习方向');
  expect(host.querySelector('.analysis-result')).toBeNull();
  expect(learningApi.analyze).toHaveBeenCalledOnce();
});
it('does not analyze or display a successful pretest when submitting fails and can retry', async () => {
  vi.mocked(learningApi.submit).mockRejectedValueOnce(new Error('提交连接失败'));
  await mount(); await click(host, '开始测评'); await answerQuiz(host, 'assessment');
  expect(host.textContent).toContain('提交连接失败');
  expect(learningApi.analyze).not.toHaveBeenCalled(); expect(store.saved.results.assessment).toBeUndefined();
  const first = vi.mocked(learningApi.submit).mock.calls[0][1];
  await click(host, '提交答案');
  expect(vi.mocked(learningApi.submit).mock.calls[1][1]).toEqual(first);
  expect(host.querySelector('.score-circle strong')?.textContent).toBe('100');
});
it('reuses persisted AI feedback without another model request', async () => {
  withAssessment(store.saved); store.saved.analysis = feedback;
  await mount();
  expect(host.textContent).toContain('逐题分析结果'); expect(learningApi.analyze).not.toHaveBeenCalled();
});
it('ignores an old analysis after resetting the assessment', async () => {
  withAssessment(store.saved);
  let resolve!: (value: Analysis) => void;
  vi.mocked(learningApi.analyze).mockImplementation(() => new Promise(done => { resolve = done; }));
  await mount(); await click(host, '重新测评');
  expect(learningApi.reset).toHaveBeenCalledOnce(); expect(host.textContent).toContain('开始测评');
  resolve(feedback); await settle();
  expect(host.querySelector('.analysis-result')).toBeNull(); expect(store.saved.results.assessment).toBeUndefined();
});
it('retains unsaved answers and offers a save retry', async () => {
  await mount(); await click(host, '开始测评');
  vi.mocked(learningApi.save).mockRejectedValueOnce(new Error('保存连接失败'));
  (host.querySelector('.practice-question input') as HTMLInputElement).click(); await settle();
  expect(host.textContent).toContain('保存连接失败'); expect(host.querySelector('input:checked')).not.toBeNull();
  await click(host, '重试保存');
  expect(store.saved.state.drafts.assessment.answers).toHaveLength(1); expect(host.querySelector('.save-status')).toBeNull();
});
it('never overwrites server progress after a load failure or revision conflict', async () => {
  vi.mocked(learningApi.load).mockRejectedValueOnce(new Error('加载失败'));
  await mount(false); expect(host.textContent).toContain('加载失败'); expect(learningApi.save).not.toHaveBeenCalled();
  await click(host, '重新加载进度'); await click(host, '学习设置'); await click(host, '开始测评');
  vi.mocked(learningApi.save).mockRejectedValueOnce(new AuthError('版本冲突', 409));
  (host.querySelector('.practice-question input') as HTMLInputElement).click(); await settle();
  expect(host.textContent).toContain('版本冲突');
  await click(host, '重新加载已保存进度');
  expect(learningApi.save).toHaveBeenCalledOnce(); expect(store.saved.state.drafts.assessment).toBeUndefined();
});
it('saves explicit setup completion and restores Home with the selected direction', async () => {
  withAssessment(store.saved, 'travel');
  await mount(); await click(host, '完成设置，进入首页');
  expect(store.saved.state.onboarding_complete).toBe(true); expect(host.textContent).toContain('我的学习单元');
  unmount(); await mount(false);
  expect(host.textContent).toContain('继续学习'); expect(host.textContent).toContain('旅游出行');
});
it('displays server unit completion and restores the result after remount', async () => {
  withAssessment(store.saved, 'travel');
  await mount(); await answerQuiz(host, 'unit-travel-0');
  expect(host.textContent).toContain('本方向已完成 1 / 5');
  expect(learningApi.submit).toHaveBeenCalledWith('unit-travel-0', expect.any(Object), expect.any(Number));
  unmount(); await mount();
  expect(host.querySelector('.quiz-result')?.textContent).toContain('100 分');
  expect(host.textContent).toContain('本方向已完成 1 / 5');
});
it('does not award a completion when unit submission fails', async () => {
  withAssessment(store.saved, 'daily');
  vi.mocked(learningApi.submit).mockRejectedValueOnce(new Error('小测提交失败'));
  await mount(); await answerQuiz(host, 'unit-daily-0');
  expect(host.textContent).toContain('小测提交失败'); expect(store.saved.state.completed.daily ?? []).toEqual([]);
  expect(host.textContent).toContain('本方向已完成 0 / 5');
  await click(host, '提交答案');
  expect(host.textContent).toContain('本方向已完成 1 / 5');
});
it('shows profile data returned by the backend including unmeasured cells', async () => {
  withAssessment(store.saved, 'travel'); store.saved.state.onboarding_complete = true;
  await mount(false); await click(host, '查看学习画像');
  expect(host.querySelectorAll('.profile-table tbody tr')).toHaveLength(7);
  expect(host.querySelectorAll('.profile-table td')).toHaveLength(42);
  expect(host.textContent).toContain('尚未测评'); expect(host.textContent).toContain('75%');
  expect(host.textContent).not.toContain('固定示例');
});
it('saves a pretest draft through the complete authenticated app', async () => {
  vi.spyOn(authApi, 'me').mockResolvedValue({ id: 'user-one', username: 'tester', display_name: '测试' });
  host = document.createElement('div'); document.body.appendChild(host);
  app = createApp(RootApp); app.mount(host); await settle();
  await click(host, '学习设置'); await click(host, '开始测评');
  (host.querySelector('.practice-question input') as HTMLInputElement).click(); await settle();
  expect(store.saved.state.drafts.assessment.answers).toHaveLength(1);
});
it('restores an unfinished post-test page and choices without treating a draft as a result', async () => {
  withAssessment(store.saved, 'campus');
  await mount(); await click(host, '开始后测');
  (host.querySelector('.practice-question input') as HTMLInputElement).click(); await settle();
  await click(host, '下一题');
  expect(store.saved.state.drafts['post-campus'].current).toBe(1);
  unmount(); await mount(); await click(host, '开始后测');
  expect(host.textContent).toContain('第 2 / 10 题');
  expect(host.textContent).toContain('已作答 1 / 10');
  expect(host.querySelector('.quiz-result')).toBeNull();
  expect(learningApi.submit).not.toHaveBeenCalled();
});
it('handles a grading revision conflict by requiring the latest saved progress', async () => {
  withAssessment(store.saved, 'poetry');
  vi.mocked(learningApi.submit).mockRejectedValueOnce(new AuthError('测验版本冲突', 409));
  await mount(); await answerQuiz(host, 'unit-poetry-0');
  expect(host.textContent).toContain('测验版本冲突');
  expect(store.saved.state.completed.poetry ?? []).toEqual([]);
  await click(host, '重新加载已保存进度');
  expect(host.querySelector('.save-status')).toBeNull();
  expect(learningApi.submit).toHaveBeenCalledOnce();
});

it('uses workspace navigation without resetting the current course or previous scores', async () => {
  withAssessment(store.saved, 'travel'); store.saved.state.onboarding_complete = true;
  await mount(false);
  const nav = host.querySelector('.workspace-nav') as HTMLElement;
  expect(nav.querySelector('[aria-current="page"]')?.textContent).toContain('学习首页');
  await click(nav, '学习方向');
  expect(host.querySelector('.topic-grid')).not.toBeNull();
  await click(nav, '我的学习');
  expect(host.querySelector('.unit-page-heading')?.textContent).toContain('礼貌问路');
  expect(host.querySelector('.topic-grid')).toBeNull();
  await click(nav, '学习画像');
  expect(host.querySelectorAll('.profile-table td')).toHaveLength(42);
  await click(nav, '学习首页');
  expect(host.querySelector('[aria-label="学习首页"]')).not.toBeNull();
  expect(store.saved.results.assessment.score).toBe(100);
  expect(learningApi.reset).not.toHaveBeenCalled();
  expect(learningApi.submit).not.toHaveBeenCalled();
});

it('jumps to unanswered questions and preserves answers when returning through Home', async () => {
  await mount(); await click(host, '开始测评');
  (host.querySelector('.practice-question input') as HTMLInputElement).click(); await settle();
  const map = host.querySelector('.question-map')!;
  expect(map.querySelectorAll('button.answered')).toHaveLength(1);
  (map.querySelectorAll('button')[7] as HTMLButtonElement).click(); await settle();
  expect(host.textContent).toContain('第 8 / 8 题');
  expect(host.textContent).toContain('还有 7 题待完成');
  expect((host.querySelector('.quiz-submit-area > button.primary') as HTMLButtonElement).disabled).toBe(true);
  expect(store.saved.state.drafts.assessment.current).toBe(7);
  await click(host.querySelector('.workspace-nav') as HTMLElement, '学习首页');
  expect(host.textContent).toContain('前测已作答 1 / 8 题');
  await click(host, '继续完成学习设置');
  expect(host.textContent).toContain('第 8 / 8 题');
  (host.querySelector('.question-map button') as HTMLButtonElement).click(); await settle();
  expect(host.querySelector('input:checked')).not.toBeNull();
  expect(learningApi.submit).not.toHaveBeenCalled();
});

it('announces saving, failure and recovery without claiming unsaved answers are saved', async () => {
  await mount(); await click(host, '开始测评');
  let rejectSave!: (reason: Error) => void;
  vi.mocked(learningApi.save).mockImplementationOnce(() => new Promise((_, reject) => { rejectSave = reject; }));
  (host.querySelector('.practice-question input') as HTMLInputElement).click(); await settle();
  expect(host.querySelector('.sync-indicator')?.textContent).toContain('正在保存进度');
  rejectSave(new Error('网络已断开')); await settle();
  expect(host.querySelector('.sync-indicator')?.textContent).toContain('进度尚未保存');
  expect(host.querySelector('input:checked')).not.toBeNull();
  await click(host, '重试保存');
  expect(host.querySelector('.sync-indicator')?.textContent).toContain('进度已保存');
  expect(store.saved.state.drafts.assessment.answers).toHaveLength(1);
});
