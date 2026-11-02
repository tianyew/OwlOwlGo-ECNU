// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { createApp, nextTick, type App } from 'vue';
import LearningJourney from '../src/features/assessment/LearningJourney.vue';
import { questions } from '../src/features/phonetics/questions';
import { submitAnswers, getPlan, getTopics } from '../src/shared/api/demo';
let app: App;
let host: HTMLDivElement;
async function settle() { for (let i = 0; i < 6; i++) await nextTick(); }
async function click(text: string) {
  const button = [...host.querySelectorAll('button')].find(b => b.textContent?.includes(text));
  expect(button).toBeDefined(); button!.click(); await settle();
}
async function completeQuiz() {
  await click('开始测评');
  for (let i = 0; i < questions.length; i++) {
    (host.querySelectorAll('input')[questions[i].answer] as HTMLInputElement).click();
    await settle(); await click('提交答案');
    await click(i === questions.length - 1 ? '查看测评结果' : '下一题');
  }
  await click('选择学习方向');
}
beforeEach(() => { host = document.createElement('div'); document.body.appendChild(host); app = createApp(LearningJourney); app.mount(host); });
afterEach(() => { app.unmount(); host.remove(); });
describe('demo journey', () => {
  it('carries diagnosis through topic changes and clears the journey on restart', async () => {
    await completeQuiz();
    expect(host.textContent).toContain('100 / 100');
    expect((host.querySelector('.question-actions .primary') as HTMLButtonElement).disabled).toBe(true);
    for (const topic of await getTopics()) {
      (host.querySelector(`input[value="${topic.id}"]`) as HTMLInputElement).click(); await settle();
      await click('确认方向');
      expect(host.querySelector('h1')?.textContent).toContain(topic.title);
      expect(host.querySelectorAll('.unit-list details')).toHaveLength(3);
      (host.querySelector('.unit-list summary') as HTMLElement).click(); await settle();
      expect(host.querySelector('.unit-list details')?.hasAttribute('open')).toBe(true);
      expect(host.textContent).toContain(topic.units[0].example);
      expect(host.textContent).toContain('100 / 100');
      await click('修改学习方向');
      expect((host.querySelector(`input[value="${topic.id}"]`) as HTMLInputElement).checked).toBe(true);
    }
    await click('重新前测');
    expect(host.textContent).toContain('开始测评');
    expect(host.querySelector('.diagnosis-summary')).toBeNull();
    await completeQuiz();
    expect(host.querySelector('input:checked')).toBeNull();
  });
  it('validates submissions and returns appropriate low, middle and high score advice', async () => {
    const wrong = questions.map(q => (q.answer + 1) % q.options.length);
    expect((await submitAnswers(wrong)).score).toBe(0);
    expect((await submitAnswers(wrong)).advice).toContain('拼音结构');
    const half = questions.map((q, i) => i < 4 ? q.answer : wrong[i]);
    expect((await submitAnswers(half)).score).toBe(50);
    expect((await submitAnswers(half)).advice).toContain('未掌握');
    expect((await submitAnswers(questions.map(q => q.answer))).advice).toContain('较好');
    await expect(submitAnswers([])).rejects.toThrow();
    await expect(submitAnswers(questions.map(() => -1))).rejects.toThrow();
    await expect(getPlan('missing')).rejects.toThrow();
  });
});
