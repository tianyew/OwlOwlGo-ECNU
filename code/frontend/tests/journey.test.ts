// @vitest-environment happy-dom
import { afterEach, beforeEach, expect, it, vi } from 'vitest';
import { createApp, type App } from 'vue';
import LearningJourney from '../src/features/assessment/LearningJourney.vue';
import { learningApi } from '../src/shared/api/learning';
import { installLearning, withAssessment, topics, settle, click, answerQuiz } from './learning-fixtures';
let app: App;
let host: HTMLDivElement;
let store: ReturnType<typeof installLearning>;
beforeEach(() => { store = installLearning(); host = document.createElement('div'); document.body.appendChild(host); });
afterEach(() => { app?.unmount(); host.remove(); vi.restoreAllMocks(); });
it('uses server quizzes for every unit and post-test in all four directions', async () => {
  withAssessment(store.saved, 'travel'); store.saved.state.onboarding_complete = true;
  app = createApp(LearningJourney, { userId: 'tester' }); app.mount(host); await settle();
  await click(host, '继续学习');
  for (const topic of topics) {
    if (topic.id !== 'travel') {
      await click(host, '修改学习方向');
      (host.querySelector(`input[value="${topic.id}"]`) as HTMLInputElement).click(); await settle();
      await click(host, '确认方向');
    }
    for (const [index, unit] of topic.units.entries()) {
      expect(host.textContent).toContain(unit.example);
      await answerQuiz(host, unit.quiz_id);
      expect(host.querySelector('.quiz-result')?.textContent).toContain('100 分');
      if (index < 4) await click(host, '下一单元');
    }
    expect(host.textContent).toContain('本方向已完成 5 / 5');
    await click(host, '开始后测'); await answerQuiz(host, topic.posttest_id);
    await click(host, '查看学习报告');
    expect(host.querySelector('.report-score')?.textContent).toContain('100');
    expect(host.querySelectorAll('.profile-table td')).toHaveLength(42);
    expect(host.textContent).not.toContain('固定示例');
    await click(host, '回到学习规划');
  }
  expect(learningApi.submit).toHaveBeenCalledTimes(24);
});
it('lets a guest preview the server curriculum without producing scores or profile evidence', async () => {
  app = createApp(LearningJourney); app.mount(host); await settle();
  await click(host, '先浏览学习方向');
  (host.querySelector('input[value="poetry"]') as HTMLInputElement).click(); await settle();
  await click(host, '确认方向');
  expect(host.textContent).toContain(topics[3].units[0].example);
  expect(host.textContent).toContain('登录后可提交');
  expect(learningApi.save).not.toHaveBeenCalled(); expect(learningApi.submit).not.toHaveBeenCalled();
});
