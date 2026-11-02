import { questions, summarize } from '../../features/phonetics/questions';

export type Diagnosis = ReturnType<typeof summarize> & { advice: string };
export interface Unit { title: string; goal: string; words: string; example: string; task: string }
export interface Topic { id: string; title: string; english: string; description: string; units: Unit[] }
export const topics: Topic[] = [
  { id: 'travel', title: '旅游出行', english: 'Travel', description: '在问路、交通与点餐中使用汉语。', units: [
    { title: '礼貌问路', goal: '识别地点词，用“在哪儿”询问位置。', words: '车站 chēzhàn · station；哪里 nǎlǐ · where', example: '请问，车站在哪儿？ / Excuse me, where is the station?', task: '将“车站”替换为“地铁站”，练习问路。' },
    { title: '乘坐交通工具', goal: '表达目的地，询问是否到达。', words: '去 qù · go；机场 jīchǎng · airport', example: '这辆车去机场吗？ / Does this bus go to the airport?', task: '根据目的地，组合一个询问公交路线的句子。' },
    { title: '餐厅点餐', goal: '用“我想要”表达需求。', words: '米饭 mǐfàn · rice；茶 chá · tea', example: '我想要一杯茶。 / I would like a cup of tea.', task: '选一种饮品，写出你的点单句子。' },
  ] },
  { id: 'daily', title: '日常生活', english: 'Daily life', description: '从问候到购物，练习常用表达。', units: [
    { title: '认识新朋友', goal: '问候并介绍自己的名字。', words: '你好 nǐ hǎo · hello；名字 míngzi · name', example: '你好，我叫安娜。 / Hello, my name is Anna.', task: '使用自己的名字完成一句自我介绍。' },
    { title: '买东西', goal: '询问价格和表达购买数量。', words: '多少 duōshao · how much；钱 qián · money', example: '这个多少钱？ / How much is this?', task: '为一件日用品写一句询价表达。' },
    { title: '约定时间', goal: '用简单句表达时间安排。', words: '明天 míngtiān · tomorrow；见 jiàn · meet', example: '我们明天见。 / See you tomorrow.', task: '用“今天”或“明天”约朋友见面。' },
  ] },
  { id: 'campus', title: '校园交流', english: 'Campus', description: '在课堂和校园中表达需求。', units: [
    { title: '寻找教室', goal: '询问校园地点。', words: '教室 jiàoshì · classroom；图书馆 túshūguǎn · library', example: '图书馆在哪儿？ / Where is the library?', task: '替换地点词，询问教室位置。' },
    { title: '课堂求助', goal: '礼貌请求重复和解释。', words: '老师 lǎoshī · teacher；再 zài · again', example: '老师，请再说一遍。 / Teacher, please say it again.', task: '模拟没有听清时如何请求帮助。' },
    { title: '介绍课程', goal: '用“喜欢”表达课程偏好。', words: '喜欢 xǐhuan · like；中文 Zhōngwén · Chinese', example: '我喜欢中文课。 / I like Chinese class.', task: '替换课程名称，说出自己的兴趣。' },
  ] },
  { id: 'poetry', title: '古诗入门', english: 'Poetry', description: '借助短诗学习词语与现代汉语表达。', units: [
    { title: '认识诗中的景物', goal: '理解月、山等常见景物词。', words: '月 yuè · moon；山 shān · mountain', example: '床前明月光。 / Bright moonlight before the bed.（李白《静夜思》）', task: '找出诗句中表示月亮的词，了解“月”的现代常用说法“月亮”。' },
    { title: '理解动作词', goal: '通过诗句识别“举头”“低头”。', words: '举头 jǔ tóu · raise one’s head；低头 dī tóu · lower one’s head', example: '举头望明月，低头思故乡。（李白《静夜思》）', task: '将“举头”改述为现代汉语“抬起头”。' },
    { title: '表达思念', goal: '从诗句过渡到日常情感表达。', words: '故乡 gùxiāng · hometown；想 xiǎng · miss / think', example: '我想家了。 / I miss home.', task: '用“我想……”写一句表达思念的话。' },
  ] },
];

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
  return { ...structuredClone(topic), schedule: '建议每次 15 分钟，按顺序学习 3 个单元；可按自己的节奏调整。' };
}
