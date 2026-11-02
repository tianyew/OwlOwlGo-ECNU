import { questions, summarize } from '../../features/phonetics/questions';

export type Diagnosis = ReturnType<typeof summarize> & { advice: string };
export interface CheckQuestion { prompt: string; options: string[]; answer: number; explanation: string; category: string }
export interface Unit { title: string; goal: string; words: string; example: string; task: string; grammar: string; dialogue: string[]; practices: string[]; quiz: CheckQuestion[] }
export interface Topic { id: string; title: string; english: string; description: string; units: Unit[] }
export { topics } from './curriculum';
import { topics } from './curriculum';

// Promise 接口集中隔离演示数据；后续可在此替换为 HTTP 调用。
export async function getQuestions() { return structuredClone(questions); }
export async function submitAnswers(answers: number[]): Promise<Diagnosis> {
  if (answers.length !== questions.length || answers.some((a, i) => !Number.isInteger(a) || a < 0 || a >= questions[i].options.length)) {
    throw new Error('请完成所有题目后再提交。');
  }
  const result = summarize(answers);
  return { ...result, advice: result.score >= 80 ? '本次辨识表现较好，可结合主题例句继续巩固。' : result.score >= 50 ? '建议先复习未掌握的声调规则，再学习主题例句。' : '建议先复习拼音结构和四声，再逐步进入主题学习。' };
}
export async function getTopics() { return structuredClone(topics); }
export async function getPlan(topicId: string) {
  const topic = topics.find(item => item.id === topicId);
  if (!topic) throw new Error('请选择一个有效的学习方向。');
  return { ...structuredClone(topic), schedule: '建议分 5 次学习，每次 20–25 分钟：认读词句 → 情境对话 → 迁移练习 → 单元小测。次日复习错题，完成方向学习后进行后测。' };
}
