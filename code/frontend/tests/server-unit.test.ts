// @vitest-environment happy-dom
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { createApp, type App } from 'vue';
import ServerUnitQuiz from '../src/features/assessment/ServerUnitQuiz.vue';
import { learningApi } from '../src/shared/api/learning';
import { quizFixture, resultFixture, savedFixture, settle, click } from './learning-fixtures';
let app: App;
let host: HTMLDivElement;
const quizId = 'unit-travel-0';
function response() {
  return { result: resultFixture(quizId, [
    { question_id: 'travel-0-expression', selected_index: 0 },
    { question_id: 'travel-0-position', selected_index: 0 },
  ], 50), progress: savedFixture() };
}
async function mount(submit = vi.fn().mockResolvedValue(response()), disabled = false, signedIn = true) {
  host = document.createElement('div'); document.body.appendChild(host);
  app = createApp(ServerUnitQuiz, { quizId, submit, disabled, signedIn }); app.mount(host); await settle();
  return submit;
}
function chooseBoth() { for (const fieldset of host.querySelectorAll('.practice-question')) (fieldset.querySelector('input') as HTMLInputElement).click(); }
beforeEach(() => { vi.spyOn(learningApi, 'quiz').mockResolvedValue(quizFixture(quizId)); });
afterEach(() => { app?.unmount(); host?.remove(); vi.restoreAllMocks(); });
it('requires all answers and displays the returned score and feedback', async () => {
  const submit = await mount();
  expect((host.querySelector('button.primary') as HTMLButtonElement).disabled).toBe(true);
  expect(host.textContent).not.toContain('“左边”是方位词');
  chooseBoth(); await settle(); await click(host, '提交礼貌问路');
  expect(submit).toHaveBeenCalledOnce();
  expect(submit.mock.calls[0][0]).toBe(quizId);
  expect(host.querySelector('.quiz-result')?.textContent).toContain('50 分');
  expect(host.textContent).toContain('“左边”是方位词');
  expect(host.textContent).toContain('本次尚未通过');
  expect((host.querySelector('.practice-question') as HTMLFieldSetElement).disabled).toBe(true);
});
it('keeps choices and the retry key after a lost response and uses a new key for a new attempt', async () => {
  const submit = vi.fn().mockRejectedValueOnce(new Error('连接失败')).mockResolvedValue(response());
  await mount(submit); chooseBoth(); await settle(); await click(host, '提交礼貌问路');
  expect(host.textContent).toContain('连接失败'); expect(host.querySelectorAll('input:checked')).toHaveLength(2);
  await click(host, '提交礼貌问路');
  const key = submit.mock.calls[0][1].submission_id;
  expect(submit.mock.calls[1][1].submission_id).toBe(key);
  await click(host, '重新练习'); chooseBoth(); await settle(); await click(host, '提交礼貌问路');
  expect(submit.mock.calls[2][1].submission_id).not.toBe(key);
});
it('restores latest feedback and a previously earned completion without submitting', async () => {
  vi.mocked(learningApi.quiz).mockResolvedValue({ ...quizFixture(quizId), result: response().result, unit_completed: true });
  const submit = await mount();
  expect(host.textContent).toContain('50 分'); expect(host.textContent).toContain('本单元已完成');
  expect(host.querySelectorAll('input:checked')).toHaveLength(2); expect(submit).not.toHaveBeenCalled();
});
it('retries question loading and blocks submitting while parent progress is unsaved', async () => {
  vi.mocked(learningApi.quiz).mockRejectedValueOnce(new Error('加载失败'));
  const submit = await mount(vi.fn(), true);
  expect(host.textContent).toContain('加载失败'); await click(host, '重新加载题目'); chooseBoth(); await settle();
  expect((host.querySelector('button.primary') as HTMLButtonElement).disabled).toBe(true); expect(submit).not.toHaveBeenCalled();
});
it('lets guests browse without creating an official submission', async () => {
  const submit = await mount(vi.fn(), false, false);
  expect(host.textContent).toContain('登录后可提交');
  expect((host.querySelector('.practice-question') as HTMLFieldSetElement).disabled).toBe(true);
  expect(submit).not.toHaveBeenCalled();
});
