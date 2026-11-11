/** Read-only UI prototype. No model calls, progress writes or stored conversations. */
export interface CompanionQuizContext {
  quizId: string;
  question: { id: string; prompt: string; category: string };
  submitted: boolean;
}

export interface CompanionContext {
  key: string;
  scene: 'welcome' | 'home' | 'topics' | 'assessment' | 'lesson' | 'posttest' | 'profile' | 'report';
  label: string;
  signedIn: boolean;
  lesson?: { title: string; goal: string; grammar: string; example: string; words: string };
  question?: CompanionQuizContext['question'];
  submitted?: boolean;
  mistakes: { prompt: string; selected: string; correct: string; explanation: string }[];
  profile?: { evidenceCount: number; repeatCount: number; focusAreas: string[]; nextSteps: string[] };
}

export type CompanionIntent = 'explain' | 'hint' | 'review' | 'profile' | 'next' | 'help';
export interface CompanionAction { intent: CompanionIntent; label: string }

export function companionActions(context: CompanionContext): CompanionAction[] {
  if (context.scene === 'profile' || context.scene === 'report') return [
    { intent: 'profile', label: '解读我的画像' },
    { intent: 'review', label: '带我复盘错题' },
    { intent: 'next', label: '接下来怎么练？' },
  ];
  if (context.scene === 'lesson') return [
    { intent: 'explain', label: '讲讲本课句型' },
    { intent: context.submitted ? 'review' : 'hint', label: context.submitted ? '带我复盘错题' : '给我一点提示' },
    { intent: 'next', label: '这节课怎么练？' },
  ];
  if (context.scene === 'assessment' || context.scene === 'posttest') return [
    { intent: context.submitted ? 'review' : 'hint', label: context.submitted ? '带我复盘错题' : '给我一点提示' },
    { intent: 'help', label: '可以怎么帮我？' },
    { intent: 'next', label: '怎么安排练习？' },
  ];
  return [
    { intent: 'next', label: '今天先学什么？' },
    { intent: 'profile', label: '读懂我的画像' },
    { intent: 'help', label: '你可以怎么帮我？' },
  ];
}

export function companionGreeting(context: CompanionContext): string {
  if (context.question) return context.submitted
    ? '这一题已经提交啦。想一起回顾解析，还是整理下一步练习？'
    : '这道题可以慢慢想。需要的话，我可以先给一点观察思路。';
  if (context.scene === 'profile') return '一起读懂这些作答记录，找到一个适合现在练习的小目标吧。';
  if (context.lesson) return `你正在学习「${context.lesson.title}」。想先读懂句型，还是看看怎么练？`;
  if (context.scene === 'topics') return '从感兴趣的生活情境开始吧。选好方向后，我可以陪你读例句、理清句型。';
  return '你好呀，我是小鸮。遇到不懂的句子，或想知道下一步怎么练，都可以来找我。';
}

function inferIntent(text: string): CompanionIntent | null {
  if (/提示|答案|选哪|怎么选/.test(text)) return 'hint';
  if (/错题|复盘|错了|为什么错/.test(text)) return 'review';
  if (/画像|薄弱|能力|掌握/.test(text)) return 'profile';
  if (/句型|语法|解释|例句|词语|单词/.test(text)) return 'explain';
  if (/下一步|怎么练|先学|分钟|安排/.test(text)) return 'next';
  if (/帮我|帮助|你好|你是谁/.test(text)) return 'help';
  return null;
}

export function companionReply(
  text: string, context: CompanionContext, intent?: CompanionIntent, hintStep = 1,
): string {
  const action = intent ?? inferIntent(text);
  if (action === 'hint') {
    if (!context.question) return '打开前测或单元小测后，我就能跟随当前题目。先看看题干问了什么，需要时再点“给我一点提示”。';
    if (context.submitted) return '这题已经提交，可以结合页面解析回顾。点“带我复盘错题”，我们就从实际作答开始。';
    const hints = [
      '第一步，先把题干中的问题用自己的话说一遍：它要你辨认一个规则，还是选择合适的表达？先别急着选。',
      '第二步，逐个读选项，检查它是否回应了题干的问题。把与题意不相关的表达先放到一边。',
      '第三步，回到本课例句或前测的规则介绍中找依据，再用自己的话说明选择理由。确定后再提交，解析会在提交后显示。',
    ];
    return `我们先看这一题：${context.question.prompt}\n\n${hints[Math.min(Math.max(hintStep, 1), 3) - 1]}`;
  }
  if (action === 'explain') {
    if (!context.lesson) return '进入具体单元后，可以试试“讲讲本课句型”。我会引用这一课已有的句型说明和例句，陪你先读懂再练习。';
    return `这节课想帮助你：${context.lesson.goal}。\n\n句型要点：${context.lesson.grammar}\n\n读一读本课例句：\n${context.lesson.example}\n\n试着找出可以替换的人物、地点或时间，再用自己的信息说一遍。`;
  }
  if (action === 'review') {
    if (context.question && !context.submitted) return '这次练习还没有提交。先独立尝试，我可以给观察思路；提交后再一起对照答案与解析复盘。';
    const wrong = context.mistakes[0];
    if (!wrong) return '这里暂时没有可复盘的错题。完成并提交一次测验后，我们可以结合真实作答回看；答对的题也值得隔一段时间再试试。';
    return `先回顾这一题：${wrong.prompt}\n\n你选择的是：${wrong.selected}\n参考答案是：${wrong.correct}\n\n题库解析：${wrong.explanation}\n\n复盘小任务：用自己的话说出两个表达的区别，再找一个不同例子练习。`;
  }
  if (action === 'profile') {
    if (!context.profile || !context.signedIn) return '登录并提交测验后，学习画像会显示真实作答记录。没有做过的维度会保持“尚未测评”，不用急着给自己下结论。';
    const { evidenceCount, repeatCount, focusAreas } = context.profile;
    if (!evidenceCount) return '你还没有形成新的作答证据。先完成前测或一个单元小测，再来看看画像；空白表示尚未测评，不是零分。';
    return `目前画像覆盖 ${evidenceCount} 道不同来源题目，记录了 ${repeatCount} 次重复练习。\n\n“首次作答”与“最近练习”分别反映不同表现，重复做同题不会增加覆盖。未测评的能力仍保持空白。\n\n${focusAreas.length ? `可以先关注：${focusAreas.slice(0, 3).join('、')}。从其中一道错题的解析开始复习。` : '已有记录中暂未列出优先巩固项，可以继续学习新单元，补充不同题目的证据。'}`;
  }
  if (action === 'next') {
    if (context.lesson) return `试试一个十分钟的小任务：\n\n① 读一遍「${context.lesson.title}」的词句。\n② 对照例句，围绕“${context.lesson.goal}”替换两处信息。\n③ 完成单元小测，再回看解析。\n\n这是练习建议，你可以按自己的节奏调整。`;
    const next = context.profile?.nextSteps[0];
    if (next) return `可以先从这条已有建议开始：\n${next}\n\n给自己留五到十分钟，只完成一个小目标。遇到不懂的句型，再打开对应单元看看例句。`;
    return '先完成一个小目标：登录后做入门前测，再选一个感兴趣的方向。已经有计划的话，就从首页的下一单元开始，每次学一点。';
  }
  if (action === 'help') return '我可以陪你读本课句型、给分步观察提示、回顾已提交的错题，也可以帮你读懂画像里的统计。\n\n现在是交互示例：回复由页面内容和预设文案组成，尚未连接真实 AI。可以点上面的快捷问题试一试。';
  return '我收到了。这一版还是交互示例，暂时不能自由回答所有问题。你可以试试“讲讲本课句型”“给我一点提示”或“解读我的画像”，看看伴学的使用方式。';
}
