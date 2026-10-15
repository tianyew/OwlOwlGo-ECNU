<script setup lang="ts">
import { computed, nextTick, ref } from 'vue';
import { questions, summarize } from './questions';

const stage = ref<'intro' | 'quiz' | 'result'>('intro');
const current = ref(0);
const selected = ref<number | null>(null);
const submitted = ref(false);
const answers = ref<number[]>([]);
const question = computed(() => questions[current.value]);
const result = computed(() => summarize(answers.value));
const progress = computed(() => answers.value.length / questions.length * 100);
const title = ref<HTMLElement | null>(null);
async function focusTitle() {
  await nextTick();
  title.value?.focus();
}
function start() {
  current.value = 0; selected.value = null; submitted.value = false; answers.value = [];
  stage.value = 'quiz'; focusTitle();
}
function submit() {
  if (selected.value === null || submitted.value) return;
  answers.value.push(selected.value);
  submitted.value = true;
}
function next() {
  if (!submitted.value) return;
  if (current.value === questions.length - 1) stage.value = 'result';
  else { current.value++; selected.value = null; submitted.value = false; }
  focusTitle();
}
const tones = [
  { mark: 'mā', name: '一声', note: '高而平 · Level', path: 'M 12 16 L 108 16' },
  { mark: 'má', name: '二声', note: '向上升 · Rising', path: 'M 12 62 L 108 16' },
  { mark: 'mǎ', name: '三声', note: '先降后升 · Dipping', path: 'M 12 42 L 48 72 L 108 18' },
  { mark: 'mà', name: '四声', note: '快速下降 · Falling', path: 'M 12 16 L 108 72' },
];
</script>

<template>
  <section class="phonetics-demo">
    <div class="section-heading"><div><p class="eyebrow">PINYIN & TONES / 入门小测</p><h1 ref="title" tabindex="-1">{{ stage === 'result' ? '看看你的声调起点' : '拼音与声调' }}</h1></div><span class="demo-tag">固定题目 Demo</span></div>
    <template v-if="stage === 'intro'">
      <div class="welcome"><div><span class="overline">先认识声音，再走进汉语。</span><h2>同一个 ma，<br>四种声调，四种意思。</h2><p>从拼音结构到四声辨识，再到日常连读中的变调。<br>用一组小题，找到你的学习起点。</p><p lang="en" class="muted">A short quiz on pinyin, four tones and basic tone changes.</p><button class="primary" @click="start">开始测评 <span>Start quiz →</span></button><div class="quiz-meta"><span>8 道选择题</span><span>约 3 分钟</span><span>提交后即时解析</span></div></div><div class="tone-art"><span class="tone-character">声</span><p>mā · má · mǎ · mà</p><small>A different tone. A different meaning.</small></div></div>
      <div class="tones" aria-label="四声速览"><article v-for="tone in tones" :key="tone.name"><div class="tone-label"><strong>{{ tone.mark }}</strong><span>{{ tone.name }}</span></div><svg viewBox="0 0 120 88" role="img" :aria-label="tone.note"><path :d="tone.path" /></svg><p>{{ tone.note }}</p></article></div>
      <p class="scope-note">本演示测评拼音与声调规则的文字辨识，不采集声音，不评估实际发音。分数仅反映本次 8 道题的作答。</p>
    </template>
    <template v-else-if="stage === 'quiz'">
      <div class="quiz-top"><span>第 {{ current + 1 }} / {{ questions.length }} 题 · {{ question.category }}</span><span>已提交 {{ answers.length }} 题</span></div><progress :value="progress" max="100" aria-label="测评完成进度"></progress>
      <article class="question-card" :key="question.id"><p class="question-example">{{ question.example }}</p><h2>{{ question.prompt }}</h2><p class="muted" lang="en">{{ question.subtitle }}</p><fieldset :disabled="submitted"><legend class="sr-only">选择一个答案</legend><label v-for="(option,index) in question.options" :key="option" class="answer-option" :class="{ chosen: selected === index, correct: submitted && index === question.answer, wrong: submitted && selected === index && index !== question.answer }"><input v-model="selected" type="radio" :name="question.id" :value="index"><span class="option-letter">{{ String.fromCharCode(65 + index) }}</span><span>{{ option }}</span><span v-if="submitted && index === question.answer" class="answer-mark">✓ 正确答案</span><span v-else-if="submitted && selected === index" class="answer-mark">✕ 你的选择</span></label></fieldset>
      <div v-if="submitted" class="explanation" :class="{ 'incorrect-feedback': selected !== question.answer }" role="status"><strong>{{ selected === question.answer ? '答对了，继续保持！' : '这题记下来，下次就会了。' }}</strong><p>{{ question.explanation }}</p></div>
      <div class="question-actions"><span class="muted">{{ submitted ? '本题已记录，点击继续' : '选好后提交，每题计分一次' }}</span><button v-if="!submitted" class="primary" :disabled="selected === null" @click="submit">提交答案 Check answer</button><button v-else class="primary" @click="next">{{ current === questions.length - 1 ? '查看测评结果' : '下一题' }} →</button></div></article>
    </template>
    <template v-else>
      <article class="result-hero"><div class="score-circle"><strong>{{ result.score }}</strong><span>/ 100</span></div><div><span class="overline">本次小测完成 · Quiz complete</span><h2>{{ result.correct === questions.length ? '全对！继续探索汉语的声音。' : result.correct >= 5 ? '基础不错，再巩固几个知识点。' : '从基础出发，每一步都算数。' }}</h2><p>答对 {{ result.correct }} / {{ questions.length }} 题 · 每题等权，百分制四舍五入</p><p class="muted">这是固定题目的知识辨识练习，不能代表汉语等级或口语水平。</p></div></article>
      <div class="breakdown"><article v-for="item in result.breakdown" :key="item.category"><h3>{{ item.category }}</h3><strong>{{ item.correct }} <small>/ {{ item.total }}</small></strong><p>{{ item.correct === item.total ? '本组全部答对，可以继续进阶。' : '建议先复习下方对应题目的解析。' }}</p></article></div>
      <section class="review"><div class="review-heading"><h2>逐题回顾</h2><button class="secondary" @click="start">重新测评 ↺</button></div><details v-for="(item,index) in questions" :key="item.id"><summary><span :class="answers[index] === item.answer ? 'review-correct' : 'review-wrong'">{{ answers[index] === item.answer ? '✓' : '✕' }}</span><span>{{ index + 1 }}. {{ item.prompt }}</span><small>{{ answers[index] === item.answer ? '答对' : '待巩固' }}</small></summary><div class="review-detail"><p>你的答案：{{ item.options[answers[index]] }}</p><p>正确答案：{{ item.options[item.answer] }}</p><p>{{ item.explanation }}</p></div></details></section>
    </template>
  </section>
</template>
