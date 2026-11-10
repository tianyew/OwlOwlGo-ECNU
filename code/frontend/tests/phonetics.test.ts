// @vitest-environment happy-dom
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { createApp, type App } from 'vue';
import PhoneticsDemo from '../src/features/phonetics/PhoneticsDemo.vue';
import { learningApi } from '../src/shared/api/learning';
import { quizFixture, resultFixture, savedFixture, settle, click } from './learning-fixtures';
let app: App;
let host: HTMLDivElement;
beforeEach(() => { host = document.createElement('div'); document.body.appendChild(host); vi.spyOn(learningApi, 'quiz').mockResolvedValue(quizFixture('assessment')); });
afterEach(() => { app?.unmount(); host.remove(); vi.restoreAllMocks(); });
it('shows the introduction and fetches server questions only after starting', async () => {
  app = createApp(PhoneticsDemo, { signedIn: true, disabled: false, submit: vi.fn() }); app.mount(host); await settle();
  expect(host.textContent).toContain('四种声调'); expect(learningApi.quiz).not.toHaveBeenCalled();
  await click(host, '开始测评');
  expect(learningApi.quiz).toHaveBeenCalledWith('assessment');
  expect(host.textContent).toContain('第 1 / 8 题');
  expect(host.textContent).not.toContain('m 是声母');
});
it('restores the authoritative total and category evidence without locally grading', async () => {
  const result = resultFixture('assessment', undefined, 88);
  vi.mocked(learningApi.quiz).mockResolvedValue({ ...quizFixture('assessment'), result });
  const submit = vi.fn().mockResolvedValue({ result, progress: savedFixture() });
  app = createApp(PhoneticsDemo, { signedIn: true, disabled: false, submit, result }); app.mount(host); await settle();
  expect(host.querySelector('.score-circle strong')?.textContent).toBe('88');
  expect(host.querySelectorAll('.breakdown article')).toHaveLength(3); expect(submit).not.toHaveBeenCalled();
});
