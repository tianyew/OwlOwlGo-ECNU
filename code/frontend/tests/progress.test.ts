// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createApp, nextTick, type App } from 'vue';
import RootApp from '../src/App.vue';
import { authApi } from '../src/shared/api/auth';
vi.mock('../src/shared/api/auth', async original => {
  const module = await original<typeof import('../src/shared/api/auth')>();
  return { ...module, authApi: { me: vi.fn(), login: vi.fn(), logout: vi.fn(), register: vi.fn() } };
});
import LearningJourney from '../src/features/assessment/LearningJourney.vue';
import { learningApi, emptyQuiz, type SavedProgress, type Analysis } from '../src/shared/api/learning';
import { AuthError } from '../src/shared/api/auth';
vi.mock('../src/shared/api/learning', async original => {
  const module = await original<typeof import('../src/shared/api/learning')>();
  return { ...module, learningApi: { load: vi.fn(), save: vi.fn(), analyze: vi.fn() } };
});
let app: App;
let host: HTMLDivElement;
let saved: SavedProgress;
const feedback: Analysis = { provider: 'deepseek', model: 'demo', prompt_version: 'assessment-v2', created_at: 'today', summary: '逐题分析结果', strengths: [], focus_areas: [], next_steps: [], question_feedback: [], practice_tasks: [] };
function finishState() {
  saved.state.quiz = { stage: 'result', current: 7, selected: 1, submitted: true, answers: [0,2,0,1,3,1,2,1] };
}
async function settle() { for (let i = 0; i < 16; i++) await nextTick(); }
async function mount(open = true) {
  host = document.createElement('div'); document.body.appendChild(host);
  app = createApp(LearningJourney, { userId: 'user-one' }); app.mount(host); await settle();
  if (open) await click((saved.state.onboarding_complete ?? saved.state.stage === 'plan') ? '继续学习' : '学习设置');
}
function unmount() { app.unmount(); host.remove(); }
async function click(text: string) {
  const button = [...host.querySelectorAll('button')].find(b => b.textContent?.includes(text));
  expect(button).toBeDefined(); button!.click(); await settle();
}
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(learningApi.analyze).mockRejectedValue(new Error("学习建议暂不可用，请稍后重试。"));
  saved = { revision: 0, updated_at: null, analysis: null,
    state: { content_version: 1, stage: 'assessment', quiz: emptyQuiz(), topic: null, completed: {} } };
  vi.mocked(learningApi.load).mockImplementation(async () => structuredClone(saved));
  vi.mocked(learningApi.save).mockImplementation(async (state, revision) => {
    saved = { revision: revision + 1, state: structuredClone(state), updated_at: 'today', analysis: null };
    return structuredClone(saved);
  });
});
afterEach(() => { unmount(); });
describe('persistent learning', () => {
  it('automatically analyzes a finished assessment once and shows the result beside diagnosis', async () => {
    finishState(); vi.mocked(learningApi.analyze).mockResolvedValue(feedback);
    await mount();
    expect(learningApi.analyze).toHaveBeenCalledTimes(1);
    expect(host.querySelector('.phonetics-demo .analysis-result')?.textContent).toContain('逐题分析结果');
    await click('返回首页'); await click('继续完成学习设置');
    expect(learningApi.analyze).toHaveBeenCalledTimes(1);
  });
  it('reuses persisted analysis without a model request', async () => {
    finishState(); saved.analysis = feedback; await mount();
    expect(learningApi.analyze).not.toHaveBeenCalled();
    expect(host.textContent).toContain('逐题分析结果');
  });
  it('waits for final progress to save before automatic analysis and supports save retry', async () => {
    saved.state.quiz = { stage: 'quiz', current: 7, selected: 1, submitted: true, answers: [0,2,0,1,3,1,2,1] };
    await mount();
    vi.mocked(learningApi.save).mockRejectedValueOnce(new Error('保存失败'));
    await click('查看测评结果');
    expect(learningApi.analyze).not.toHaveBeenCalled();
    await click('重试保存');
    expect(learningApi.analyze).toHaveBeenCalledTimes(1);
    await settle(); expect(learningApi.analyze).toHaveBeenCalledTimes(1);
  });
  it('ignores an in-flight result after starting a new assessment', async () => {
    finishState(); let resolve!: (value: Analysis) => void;
    vi.mocked(learningApi.analyze).mockImplementation(() => new Promise(done => { resolve = done; }));
    await mount(); await click('重新测评'); resolve(feedback); await settle();
    expect(host.querySelector('.analysis-result')).toBeNull();
    expect(saved.state.quiz.stage).not.toBe('result');
  });
  it('keeps the report out of topic and plan pages and does not reanalyze progress changes', async () => {
    finishState(); saved.analysis = feedback;
    vi.mocked(learningApi.save).mockImplementation(async (state, revision) => {
      saved = { revision: revision + 1, state: structuredClone(state), updated_at: 'today', analysis: feedback };
      return structuredClone(saved);
    });
    await mount(); await click('选择学习方向');
    expect(host.querySelector('#learning-analysis')).toBeNull();
    (host.querySelector('input[value="travel"]') as HTMLInputElement).click(); await settle();
    await click('确认方向');
    expect(host.querySelector('#learning-analysis')).toBeNull();
    await click('标记本单元完成'); await click('完成设置，进入首页');
    expect(host.textContent).not.toContain('逐题分析结果');
    await click('查看前测报告');
    expect(host.textContent).toContain('逐题分析结果');
    expect(saved.state.stage).toBe('plan');
    expect(saved.state.topic).toBe('travel');
    await click('返回首页'); await click('修改方向');
    (host.querySelector('input[value="poetry"]') as HTMLInputElement).click(); await settle();
    await click('确认方向');
    expect(host.querySelector('#learning-analysis')).toBeNull();
    expect(learningApi.analyze).not.toHaveBeenCalled();
  });
  it('shows Home for a new account without automatically entering assessment', async () => {
    await mount(false);
    expect(host.querySelector('[aria-label="学习首页"]')).not.toBeNull();
    expect(host.textContent).toContain('第一步 · 完成学习设置');
    expect(host.querySelector('.phonetics-demo')).toBeNull();
    expect(learningApi.save).not.toHaveBeenCalled();
  });
  it('resumes unfinished setup from Home and can return without losing the quiz', async () => {
    saved.state.quiz = { stage: 'quiz', current: 0, selected: 0, submitted: true, answers: [0] };
    await mount(false);
    expect(host.textContent).toContain('前测已提交 1 / 8 题');
    await click('继续完成学习设置');
    expect(host.textContent).toContain('已提交 1 题');
    await click('返回首页');
    expect(host.textContent).toContain('前测已提交 1 / 8 题');
  });
  it('persists explicit setup completion and does not show onboarding on the next login', async () => {
    saved.state = { content_version: 1, onboarding_complete: false, stage: 'plan', topic: 'travel', completed: {},
      quiz: { stage: 'result', current: 7, selected: 1, submitted: true, answers: [0,2,0,1,3,1,2,1] } };
    await mount();
    await click('完成设置，进入首页');
    expect(saved.state.onboarding_complete).toBe(true);
    expect(host.textContent).toContain('我的学习单元');
    expect(host.textContent).not.toContain('第一步 · 完成学习设置');
    unmount(); await mount(false);
    expect(host.textContent).toContain('继续学习');
    await click('修改方向');
    (host.querySelector('input[value="poetry"]') as HTMLInputElement).click(); await settle();
    await click('返回首页');
    expect(host.textContent).toContain('旅游出行');
    expect(saved.state.topic).toBe('travel');
    expect(saved.state.onboarding_complete).toBe(true);
  });
  it('offers review after all units are complete and supports legacy saved plans', async () => {
    saved.state = { content_version: 1, stage: 'plan', topic: 'travel', completed: {travel:[0,1,2]},
      quiz: { stage: 'result', current: 7, selected: 1, submitted: true, answers: [0,2,0,1,3,1,2,1] } };
    await mount(false);
    expect(host.textContent).toContain('回顾学习内容');
    expect(host.textContent).not.toContain('第一步 · 完成学习设置');
  });
  it('starts and saves the quiz inside the full signed-in app', async () => {
    vi.mocked(authApi.me).mockResolvedValue({ id: 'user-one', username: 'admin', display_name: 'Demo' });
    host = document.createElement('div'); document.body.appendChild(host);
    app = createApp(RootApp); app.mount(host); await settle();
    await click('开始学习设置'); await click('开始测评');
    expect(host.textContent).toContain('第 1 / 8 题');
    expect(saved.state.quiz.stage).toBe('quiz');
  });
  it('restores submitted quiz answers after remount and continues without duplicate scoring', async () => {
    await mount(); await click('开始测评');
    (host.querySelector('input') as HTMLInputElement).click(); await settle(); await click('提交答案');
    expect(saved.state.quiz.answers).toEqual([0]);
    unmount(); await mount();
    expect((host.querySelector('fieldset') as HTMLFieldSetElement).disabled).toBe(true);
    expect(host.textContent).toContain('已提交 1 题');
    await click('下一题');
    expect(saved.state.quiz.current).toBe(1);
    expect(saved.state.quiz.answers).toEqual([0]);
  });
  it('persists unit completion, restores plan and displays analysis failure honestly', async () => {
    saved.state = { content_version: 1, stage: 'plan', topic: 'travel', completed: {},
      quiz: { stage: 'result', current: 7, selected: 1, submitted: true, answers: [0,2,0,1,3,1,2,1] } };
    await mount(); await click('标记本单元完成');
    expect(saved.state.completed.travel).toEqual([0]);
    unmount(); await mount(); expect(host.textContent).toContain('1 / 3');
    vi.mocked(learningApi.analyze).mockRejectedValue(new Error('学习建议暂不可用，请稍后重试。'));
    await click('返回首页'); await click('查看前测报告');
    await click('重试分析'); expect(host.textContent).toContain('学习建议暂不可用');
    expect(host.querySelector('.analysis-result')).toBeNull();
  });
  it('keeps unsaved progress and offers retry without showing saved status', async () => {
    await mount();
    vi.mocked(learningApi.save).mockRejectedValueOnce(new Error('连接失败'));
    await click('开始测评'); expect(host.textContent).toContain('连接失败');
    await click('重试保存'); expect(host.querySelector('.save-status')).toBeNull();
    expect(saved.state.quiz.stage).toBe('quiz');
  });
  it('does not overwrite progress after a load failure or revision conflict', async () => {
    vi.mocked(learningApi.load).mockRejectedValueOnce(new Error('加载失败'));
    await mount(false); expect(host.textContent).toContain('加载失败');
    expect(learningApi.save).not.toHaveBeenCalled();
    await click('重新加载进度'); await click('开始学习设置');
    vi.mocked(learningApi.save).mockRejectedValueOnce(new AuthError('版本冲突', 409));
    await click('开始测评'); expect(host.textContent).toContain('版本冲突');
    await click('重新加载已保存进度'); expect(host.textContent).toContain('开始测评');
    expect(learningApi.save).toHaveBeenCalledTimes(1);
  });
});
