// @vitest-environment happy-dom
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { createApp, h, reactive, type App } from 'vue';
import StudyCompanion from '../src/features/companion/StudyCompanion.vue';
import LearningJourney from '../src/features/assessment/LearningJourney.vue';
import type { CompanionContext } from '../src/features/companion/demo';
import { learningApi } from '../src/shared/api/learning';
import { click, installLearning, rawQuestions, settle, topics, withAssessment } from './learning-fixtures';

let app: App;
let host: HTMLDivElement;
let model: { context: CompanionContext };
let fetchMock: ReturnType<typeof vi.fn>;
function companion() { return document.body.querySelector('.study-companion') as HTMLElement; }
function dialog() { return companion().querySelector('[role="dialog"]') as HTMLElement; }
function editor() { return companion().querySelector('textarea') as HTMLTextAreaElement; }
function contextFixture(): CompanionContext {
  const unit = topics[0].units[0];
  return { key: 'lesson-one', scene: 'lesson', label: '旅游出行 · 第 1 单元 · ' + unit.title,
    signedIn: true, lesson: unit, mistakes: [], submitted: false,
    question: { id: 'question-one', prompt: '第一道未提交题目', category: '情境表达' } };
}
async function mount(context = contextFixture()) {
  model = reactive({ context });
  app = createApp({ render: () => h(StudyCompanion, { context: model.context }) });
  app.mount(host); await settle();
}
async function open() { await click(companion(), 'AI 伴学'); }
async function type(text: string) { editor().value = text; editor().dispatchEvent(new Event('input', { bubbles: true })); await settle(); }
beforeEach(() => {
  host = document.createElement('div'); document.body.appendChild(host);
  fetchMock = vi.fn(); vi.stubGlobal('fetch', fetchMock);
});
afterEach(() => { app?.unmount(); host.remove(); vi.restoreAllMocks(); vi.unstubAllGlobals(); });

it('opens only on request, identifies the demo, and restores launcher focus on Escape', async () => {
  await mount();
  expect(dialog()).toBeNull();
  expect(companion().querySelector('button')?.getAttribute('aria-expanded')).toBe('false');
  await open();
  expect(dialog().textContent).toContain('尚未连接真实 AI');
  expect(document.activeElement).toBe(editor());
  editor().dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); await settle();
  expect(dialog()).toBeNull();
  expect(document.activeElement).toBe(companion().querySelector('.companion-launcher'));
  expect(fetchMock).not.toHaveBeenCalled();
});

it('explains the current lesson using existing content and handles unsupported input honestly', async () => {
  await mount(); await open(); await click(dialog(), '讲讲本课句型');
  expect(dialog().querySelector('.companion-message-assistant')?.textContent).toContain(topics[0].units[0].grammar);
  expect(dialog().querySelector('.companion-message-assistant')?.textContent).toContain(topics[0].units[0].example);
  await type('讲讲黑洞是怎么形成的');
  dialog().querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); await settle();
  expect(dialog().textContent).toContain('暂时不能自由回答所有问题');
  expect(fetchMock).not.toHaveBeenCalled();
});

it('offers incremental observation hints and does not reveal old answers before submission', async () => {
  const context = contextFixture();
  context.mistakes = [{ prompt: '旧题目', selected: '旧选择', correct: '不应提前显示的答案', explanation: '不应提前显示的解析' }];
  await mount(context); await open();
  for (const step of ['第一步', '第二步', '第三步']) {
    await click(dialog(), '给我一点提示');
    expect(dialog().querySelector('.companion-message-assistant:last-child')?.textContent).toContain(step);
  }
  await type('帮我复盘这道错题');
  dialog().querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true })); await settle();
  expect(dialog().textContent).toContain('这次练习还没有提交');
  expect(dialog().textContent).not.toContain('不应提前显示的答案');
  expect(dialog().textContent).not.toContain('不应提前显示的解析');
  expect(fetchMock).not.toHaveBeenCalled();
});

it('clears old context and reads actual feedback only after a submitted result', async () => {
  await mount(); await open(); await click(dialog(), '给我一点提示'); await type('尚未发送的旧问题');
  model.context = { ...contextFixture(), key: 'lesson-result', submitted: true,
    mistakes: [{ prompt: '已提交的题目', selected: '实际选择', correct: '正确表达', explanation: '题库提供的真实解析' }] };
  await settle();
  expect(editor().value).toBe('');
  expect(dialog().querySelectorAll('.companion-message')).toHaveLength(0);
  await click(dialog(), '带我复盘错题');
  expect(dialog().textContent).toContain('实际选择');
  expect(dialog().textContent).toContain('题库提供的真实解析');
  expect(dialog().textContent).not.toContain('尚未发送的旧问题');
});

it('explains supplied profile evidence and never invents guest results', async () => {
  await mount({ key: 'profile', scene: 'profile', label: '我的学习画像', signedIn: true,
    mistakes: [], profile: { evidenceCount: 15, repeatCount: 4, focusAreas: ['基础变调'], nextSteps: [] } });
  await open(); await click(dialog(), '解读我的画像');
  expect(dialog().textContent).toContain('15 道不同来源题目');
  expect(dialog().textContent).toContain('4 次重复练习');
  expect(dialog().textContent).toContain('基础变调');
  model.context = { key: 'guest', scene: 'home', label: '游客首页', signedIn: false, mistakes: [] }; await settle();
  await click(dialog(), '读懂我的画像');
  expect(dialog().textContent).toContain('登录并提交测验后');
  expect(dialog().textContent).not.toContain('15 道不同来源题目');
});

it('respects Chinese input composition and Shift+Enter, rejects blank input, and renders text safely', async () => {
  await mount(); await open(); await type('   ');
  expect((dialog().querySelector('.companion-send') as HTMLButtonElement).disabled).toBe(true);
  await type('<img src=x onerror=alert(1)>');
  editor().dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', isComposing: true, bubbles: true, cancelable: true })); await settle();
  editor().dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true, bubbles: true, cancelable: true })); await settle();
  expect(dialog().querySelectorAll('.companion-message')).toHaveLength(0);
  editor().dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter', bubbles: true, cancelable: true })); await settle();
  expect(dialog().querySelectorAll('.companion-message')).toHaveLength(2);
  expect(dialog().querySelector('.companion-message-user')?.textContent).toContain('<img src=x onerror=alert(1)>');
  expect(dialog().querySelector('img')).toBeNull();
  await click(dialog(), '清空对话');
  expect(dialog().querySelectorAll('.companion-message')).toHaveLength(0);
});

it('follows lesson and profile navigation without saving progress or grading on chat actions', async () => {
  const store = installLearning(); withAssessment(store.saved, 'travel'); store.saved.state.onboarding_complete = true;
  app = createApp(LearningJourney, { userId: 'companion-tester' }); app.mount(host); await settle();
  await click(host, '继续学习');
  const before = JSON.stringify(store.saved);
  const saveCount = vi.mocked(learningApi.save).mock.calls.length;
  await open(); await click(dialog(), '讲讲本课句型');
  expect(dialog().querySelector('.companion-context')?.textContent).toContain(topics[0].units[0].title);
  expect(dialog().textContent).toContain(topics[0].units[0].example);
  await click(host, '下一单元');
  expect(dialog().querySelector('.companion-context')?.textContent).toContain(topics[0].units[1].title);
  expect(dialog().querySelectorAll('.companion-message')).toHaveLength(0);
  await click(host.querySelector('.workspace-nav') as HTMLElement, '学习画像');
  await click(dialog(), '解读我的画像');
  expect(dialog().textContent).toContain('8 道不同来源题目');
  expect(JSON.stringify(store.saved)).toBe(before);
  expect(learningApi.save).toHaveBeenCalledTimes(saveCount);
  expect(learningApi.submit).not.toHaveBeenCalled();
  expect(fetchMock).not.toHaveBeenCalled();
});

it('tracks pretest question jumps and starts fresh hints for the new question', async () => {
  installLearning();
  app = createApp(LearningJourney); app.mount(host); await settle();
  await click(host, '开始测评'); await open(); await click(dialog(), '给我一点提示');
  expect(dialog().querySelector('.companion-question')?.textContent).toContain(rawQuestions('assessment')[0].prompt);
  (host.querySelectorAll('.question-map button')[1] as HTMLButtonElement).click(); await settle();
  expect(dialog().querySelector('.companion-question')?.textContent).toContain(rawQuestions('assessment')[1].prompt);
  expect(dialog().querySelectorAll('.companion-message')).toHaveLength(0);
  await click(dialog(), '给我一点提示');
  expect(dialog().textContent).toContain('第一步');
  expect(learningApi.save).not.toHaveBeenCalled();
  expect(learningApi.submit).not.toHaveBeenCalled();
});
