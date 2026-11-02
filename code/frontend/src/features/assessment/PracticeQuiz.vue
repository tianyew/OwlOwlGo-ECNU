<script setup lang="ts">
import { computed, ref, watch, nextTick } from 'vue';
import type { CheckQuestion } from '../../shared/api/demo';
export interface Attempt { answers: number[]; submitted: boolean }
const props = defineProps<{ questions: CheckQuestion[]; modelValue: Attempt; title: string; paginated?: boolean }>();
const emit = defineEmits<{ 'update:modelValue': [value: Attempt]; complete: [score: number] }>();
const page = ref(0);
const quizPanel = ref<HTMLElement>();
const visibleQuestions = computed(() => props.questions.map((question, index) => ({ question, index })).filter(item => !props.paginated || item.index === page.value));
const answered = computed(() => props.questions.filter((q, i) => props.modelValue.answers[i] >= 0 && props.modelValue.answers[i] < q.options.length).length);
watch(() => props.modelValue.answers.length, length => { if (!length) page.value = 0; });
async function turnPage(index: number) {
  if (index < 0 || index >= props.questions.length) return;
  page.value = index; await nextTick(); quizPanel.value?.focus();
}
function reset() { page.value = 0; emit('update:modelValue', { answers: [], submitted: false }); }
const ready = computed(() => props.questions.every((q, i) => Number.isInteger(props.modelValue.answers[i]) && props.modelValue.answers[i] >= 0 && props.modelValue.answers[i] < q.options.length));
const correct = computed(() => props.questions.filter((q, i) => props.modelValue.answers[i] === q.answer).length);
function choose(index: number, value: number) {
  const answers = [...props.modelValue.answers];
  while (answers.length < props.questions.length) answers.push(-1);
  answers[index] = value; emit('update:modelValue', { answers, submitted: false });
}
function submit() {
  if (!ready.value || props.modelValue.submitted) return;
  emit('update:modelValue', { answers: [...props.modelValue.answers], submitted: true });
  emit('complete', Math.round(correct.value / props.questions.length * 100));
}
</script>

<template>
  <section ref="quizPanel" class="practice-quiz" :aria-label="title" tabindex="-1">
    <div class="review-heading"><h3>{{ title }}</h3><span class="muted">{{ questions.length }} 题 · 单项选择</span></div>
    <p class="muted">先独立作答，提交后查看解析；错题可以返回学习内容复习。</p>
    <p v-if="paginated" class="quiz-page-status" role="status">第 {{ page + 1 }} / {{ questions.length }} 题 · 已作答 {{ answered }} / {{ questions.length }}</p>
    <fieldset v-for="{ question, index } in visibleQuestions" :key="index" class="practice-question" :disabled="modelValue.submitted">
      <legend>{{ index + 1 }}. {{ question.prompt }}</legend>
      <label v-for="(option, choice) in question.options" :key="choice" class="practice-option" :class="{ chosen: modelValue.answers[index] === choice, correct: modelValue.submitted && choice === question.answer, wrong: modelValue.submitted && modelValue.answers[index] === choice && choice !== question.answer }">
        <input type="radio" :name="`${title}-${index}`" :checked="modelValue.answers[index] === choice" @change="choose(index, choice)"><span>{{ option }}</span>
      </label>
      <p v-if="modelValue.submitted" class="practice-feedback"><strong>{{ modelValue.answers[index] === question.answer ? '✓ 回答正确' : '待巩固 · 正确答案：' + question.options[question.answer] }}</strong><br>{{ question.explanation }}</p>
    </fieldset>
    <div v-if="modelValue.submitted" class="quiz-result" role="status"><strong>{{ Math.round(correct / questions.length * 100) }} 分</strong><span>答对 {{ correct }} / {{ questions.length }} 题</span><button class="secondary" @click="reset">重新练习</button></div>
    <nav v-if="paginated" class="pagination" aria-label="后测题目分页"><button class="secondary" :disabled="page === 0" @click="turnPage(page - 1)">← 上一题</button><span>第 {{ page + 1 }} / {{ questions.length }} 题</span><button v-if="page < questions.length - 1" class="primary" @click="turnPage(page + 1)">下一题 →</button><button v-else-if="!modelValue.submitted" class="primary" :disabled="!ready" @click="submit">提交{{ title }}</button><span v-else>已提交</span></nav>
    <p v-if="paginated && page === questions.length - 1 && !ready && !modelValue.submitted" class="muted">还有 {{ questions.length - answered }} 题未作答，请返回补全后提交。</p>
    <button v-if="!paginated && !modelValue.submitted" class="primary" :disabled="!ready" @click="submit">提交{{ title }}</button>
  </section>
</template>
