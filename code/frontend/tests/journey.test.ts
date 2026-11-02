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
      expect(host.querySelectorAll('.unit-page')).toHaveLength(1);
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
  it('scores unit practice and post-test before opening the fixed report', async () => {
    await completeQuiz();
    (host.querySelector('input[value="travel"]') as HTMLInputElement).click(); await settle();
    await click('确认方向');
    const topic = (await getTopics())[0];
    const unitQuiz = host.querySelector('.practice-quiz')!;
    for (const [i, q] of topic.units[0].quiz.entries()) {
      (unitQuiz.querySelectorAll('fieldset')[i].querySelectorAll('input')[q.answer] as HTMLInputElement).click();
      await settle();
    }
    await click('提交礼貌问路');
    expect(host.textContent).toContain('本方向已完成 1 / 5');
    await click('下一单元');
    expect(host.querySelectorAll('.unit-page')).toHaveLength(1);
    expect(host.textContent).toContain(topic.units[1].example);
    expect(host.textContent).not.toContain(topic.units[0].example);
    await click('上一单元');
    expect(host.querySelector('.quiz-result')?.textContent).toContain('100 分');
    await click('开始后测');
    expect(host.querySelector('h1')?.textContent).toContain('后测');
    expect(host.querySelectorAll('.practice-question')).toHaveLength(1);
    expect(host.textContent).toContain('第 1 / 10 题');
    const { postQuestions } = await import('../src/shared/api/curriculum');
    for (const [i, q] of postQuestions(topic).entries()) {
      (host.querySelector('.practice-question')!.querySelectorAll('input')[q.answer] as HTMLInputElement).click(); await settle();
      if (i < 9) await click('下一题');
    }
    await click('上一题');
    expect(host.querySelector('.practice-question input:checked')).not.toBeNull();
    await click('下一题');
    await click('提交方向后测');
    expect(host.querySelector('.quiz-result')?.textContent).toContain('100 分');
    await click('查看诊断报告');
    expect(host.querySelector('.report-score')?.textContent).toContain('100');
    expect(host.textContent).toContain('固定示例');
    await click('重新进行后测');
    expect(host.querySelector('.quiz-result')).toBeNull();
    expect(host.querySelectorAll('.practice-question input:checked')).toHaveLength(0);
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
