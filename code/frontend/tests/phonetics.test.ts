// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { createApp, nextTick, type App } from 'vue';
import PhoneticsDemo from '../src/features/phonetics/PhoneticsDemo.vue';
import { questions } from '../src/features/phonetics/questions';

let app: App;
let host: HTMLDivElement;
async function clickButton(text: string) {
  const button = [...host.querySelectorAll('button')].find(item => item.textContent?.includes(text));
  expect(button).toBeDefined();
  button!.click();
  await nextTick(); await nextTick(); await nextTick();
}
async function choose(index: number) {
  (host.querySelectorAll('input')[index] as HTMLInputElement).click();
  await nextTick(); await nextTick(); await nextTick();
}
beforeEach(() => {
  host = document.createElement('div'); document.body.appendChild(host);
  app = createApp(PhoneticsDemo); app.mount(host);
});
afterEach(() => { app.unmount(); host.remove(); });

describe('fixed pinyin assessment', () => {
  it('requires an answer, locks submitted choices, scores once and resets on restart', async () => {
    await clickButton('开始测评');
    expect((host.querySelector('.primary') as HTMLButtonElement).disabled).toBe(true);
    await choose(1); await clickButton('提交答案');
    expect(host.querySelector('[role="status"]')?.textContent).toContain('这题记下来');
    expect((host.querySelector('fieldset') as HTMLFieldSetElement).disabled).toBe(true);
    expect(host.querySelector('.correct')?.textContent).toContain('m');
    for (let i = 1; i < questions.length; i++) {
      await clickButton('下一题');
      expect(host.querySelector('[role="status"]')).toBeNull();
      await choose(questions[i].answer); await clickButton('提交答案');
    }
    await clickButton('查看测评结果');
    expect(host.querySelector('.score-circle strong')?.textContent).toBe('88');
    expect(host.querySelector('.result-hero')?.textContent).toContain('7 / 8');
    expect(host.querySelectorAll('details')).toHaveLength(8);
    expect(host.querySelectorAll('.review-wrong')).toHaveLength(1);
    await clickButton('重新测评');
    expect(host.querySelector('.quiz-top')?.textContent).toContain('已提交 0 题');
    expect((host.querySelector('.primary') as HTMLButtonElement).disabled).toBe(true);
  });
  it('reports full marks and all three categories for a perfect run', async () => {
    await clickButton('开始测评');
    for (let i = 0; i < questions.length; i++) {
      await choose(questions[i].answer); await clickButton('提交答案');
      await clickButton(i === questions.length - 1 ? '查看测评结果' : '下一题');
    }
    expect(host.querySelector('.score-circle strong')?.textContent).toBe('100');
    expect(host.querySelector('.result-hero')?.textContent).toContain('8 / 8');
    expect(host.querySelectorAll('.breakdown article')).toHaveLength(3);
    expect(host.querySelectorAll('.review-wrong')).toHaveLength(0);
  });
});

// Keep the server evidence identical to the questions actually shown to learners.
it('keeps backend assessment evidence aligned with the displayed question bank', async () => {
  const { questions } = await import('../src/features/phonetics/questions');
  const { default: items } = await import('../../backend/app/domain/learner/assessment_items.json');
  expect(items).toEqual(questions);
});
