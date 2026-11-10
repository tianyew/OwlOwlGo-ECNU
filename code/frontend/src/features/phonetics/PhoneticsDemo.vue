<script setup lang="ts">
import { computed, ref } from 'vue';
import ServerUnitQuiz from '../assessment/ServerUnitQuiz.vue';
import type { QuizDraft, QuizResult, QuizSubmission, SubmissionResponse } from '../../shared/api/learning';
const props = defineProps<{
  signedIn: boolean; disabled: boolean; draft?: QuizDraft; result?: QuizResult;
  submit: (quizId: string, body: QuizSubmission) => Promise<SubmissionResponse>;
}>();
const emit = defineEmits<{ complete: []; restart: []; browse: []; draft: [id: string, draft: QuizDraft] }>();
const started = ref(Boolean(props.draft || props.result));
const breakdown = computed(() => [...new Set(props.result?.items.map(item => item.category) ?? [])].map(category => {
  const items = props.result!.items.filter(item => item.category === category);
  return { category, total: items.length, correct: items.filter(item => item.is_correct).length };
}));
const tones = [
  { mark: 'mā', name: '一声', note: '高而平 · Level', path: 'M 12 16 L 108 16' },
  { mark: 'má', name: '二声', note: '向上升 · Rising', path: 'M 12 62 L 108 16' },
  { mark: 'mǎ', name: '三声', note: '先降后升 · Dipping', path: 'M 12 42 L 48 72 L 108 18' },
  { mark: 'mà', name: '四声', note: '快速下降 · Falling', path: 'M 12 16 L 108 72' },
];
</script>
<template>
  <section class="phonetics-demo">
    <div class="section-heading"><div><p class="eyebrow">PINYIN & TONES / 入门小测</p><h1>{{ result ? '看看你的声调起点' : '拼音与声调' }}</h1></div></div>
    <template v-if="!started">
      <div class="welcome"><div><span class="overline">先认识声音，再走进汉语。</span><h2>同一个 ma，<br>四种声调，四种意思。</h2><p>从拼音结构到四声辨识，再到日常连读中的变调。用一组小题，找到你的学习起点。</p><p class="muted" lang="en">A short quiz on pinyin, four tones and basic tone changes.</p><button class="primary" @click="started = true">开始测评 →</button><div class="quiz-meta"><span>8 道选择题</span><span>约 3 分钟</span><span>全部提交后查看解析</span></div></div><div class="tone-art"><span class="tone-character">声</span><p>mā · má · mǎ · mà</p></div></div>
      <div class="tones" aria-label="四声速览"><article v-for="tone in tones" :key="tone.name"><div class="tone-label"><strong>{{ tone.mark }}</strong><span>{{ tone.name }}</span></div><svg viewBox="0 0 120 88" role="img" :aria-label="tone.note"><path :d="tone.path" /></svg><p>{{ tone.note }}</p></article></div>
    </template>
    <template v-else>
      <div v-if="result" class="result-hero"><div class="score-circle"><strong>{{ result.score }}</strong><span>/ 100</span></div><div><h2>本次前测结果</h2><p>答对 {{ result.correct }} / {{ result.total }} 题</p></div></div>
      <div v-if="result" class="breakdown"><article v-for="item in breakdown" :key="item.category"><strong>{{ item.category }}</strong><span>{{ item.correct }} / {{ item.total }}</span></article></div>
      <slot v-if="result" name="analysis" />
      <ServerUnitQuiz quiz-id="assessment" :signed-in="signedIn" :disabled="disabled" :draft="draft" :submit="submit" @draft="(id, value) => emit('draft', id, value)" />
      <div v-if="result" class="question-actions"><button class="secondary" :disabled="disabled" @click="emit('restart')">重新测评</button><button class="primary" :disabled="disabled" @click="emit('complete')">选择学习方向 →</button></div>
    </template>
    <button v-if="!signedIn" class="secondary" @click="emit('browse')">先浏览学习方向 →</button>
  </section>
</template>
