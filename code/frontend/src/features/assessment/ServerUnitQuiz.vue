<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue';
import { learningApi, type Quiz, type QuizDraft, type QuizResult, type QuizSubmission, type SubmissionResponse } from '../../shared/api/learning';
const props = defineProps<{
  quizId: string; disabled: boolean; signedIn: boolean; draft?: QuizDraft;
  submit: (quizId: string, body: QuizSubmission) => Promise<SubmissionResponse>;
}>();
const emit = defineEmits<{ draft: [quizId: string, draft: QuizDraft]; loaded: [quiz: Quiz]; result: [value: QuizResult] }>();
const quiz = ref<Quiz>();
const answers = ref<Record<string, number>>({});
const result = ref<QuizResult | null>(null);
const completed = ref(false);
const loading = ref(true);
const submitting = ref(false);
const error = ref('');
const page = ref(0);
const panel = ref<HTMLElement>();
let submissionId = '';
let disposed = false;
const paginated = computed(() => quiz.value?.kind !== 'unit');
const visible = computed(() => quiz.value?.questions.map((question, index) => ({ question, index })).filter(item => !paginated.value || item.index === page.value) ?? []);
const ready = computed(() => Boolean(quiz.value?.questions.every(q => Number.isInteger(answers.value[q.id]))));
const answered = computed(() => Object.keys(answers.value).length);
async function load() {
  loading.value = true; error.value = '';
  try {
    const loaded = await learningApi.quiz(props.quizId);
    if (disposed) return;
    quiz.value = loaded; completed.value = loaded.unit_completed;
    const draft = props.draft ?? loaded.draft;
    result.value = draft ? null : loaded.result;
    const saved = draft?.answers ?? loaded.result?.items ?? [];
    answers.value = Object.fromEntries(saved.map(item => [item.question_id, item.selected_index]));
    page.value = draft?.current ?? 0;
    emit('loaded', loaded);
  } catch (reason) {
    if (!disposed) error.value = reason instanceof Error ? reason.message : '题目加载失败，请重试。';
  } finally { loading.value = false; }
}
function saveDraft() {
  if (!props.signedIn || !quiz.value || result.value) return;
  emit('draft', props.quizId, { content_version: quiz.value.content_version, current: page.value,
    answers: quiz.value.questions.filter(q => Number.isInteger(answers.value[q.id])).map(q => ({ question_id: q.id, selected_index: answers.value[q.id] })) });
}
function choose(id: string, index: number) {
  answers.value = { ...answers.value, [id]: index }; submissionId = ''; error.value = ''; saveDraft();
}
async function turn(index: number) {
  if (!quiz.value || index < 0 || index >= quiz.value.questions.length) return;
  page.value = index; saveDraft(); await nextTick(); panel.value?.focus();
}
function retry() {
  result.value = null; answers.value = {}; page.value = 0; submissionId = ''; error.value = ''; saveDraft();
}
async function submit() {
  if (!quiz.value || !ready.value || !props.signedIn || props.disabled || submitting.value || result.value) return;
  submitting.value = true; error.value = '';
  submissionId ||= crypto.randomUUID();
  try {
    const response = await props.submit(props.quizId, {
      submission_id: submissionId, content_version: quiz.value.content_version,
      answers: quiz.value.questions.map(q => ({ question_id: q.id, selected_index: answers.value[q.id] })),
    });
    if (disposed) return;
    result.value = response.result;
    completed.value = quiz.value.kind === 'unit' && (response.progress.state.completed[response.result.topic ?? '']?.includes(response.result.unit_index ?? -1) ?? false);
    emit('result', response.result);
  } catch (reason) {
    if (!disposed) error.value = reason instanceof Error ? reason.message : '提交失败，请重试。';
  } finally { submitting.value = false; }
}
onMounted(load);
onBeforeUnmount(() => { disposed = true; });
</script>
<template>
  <section ref="panel" class="practice-quiz" :aria-label="quiz?.title ?? '测验'" :aria-busy="loading || submitting" tabindex="-1">
    <p v-if="loading" role="status">正在加载题目…</p>
    <div v-if="error" role="alert">{{ error }} <button v-if="!quiz" class="secondary" @click="load">重新加载题目</button></div>
    <template v-if="quiz && !loading">
      <div class="review-heading"><h3>{{ quiz.title }}</h3><span class="muted">{{ quiz.questions.length }} 题 · 单项选择</span></div>
      <p class="muted">先完成作答，提交后查看成绩与解析。</p>
      <p v-if="!signedIn" class="scope-note">登录后可提交测验并保存成绩；当前可浏览题目与课程。</p>
      <p v-if="paginated" class="quiz-page-status" role="status">第 {{ page + 1 }} / {{ quiz.questions.length }} 题 · 已作答 {{ answered }} / {{ quiz.questions.length }}</p>
      <fieldset v-for="{ question, index } in visible" :key="question.id" class="practice-question" :disabled="Boolean(result) || submitting || !signedIn">
        <legend>{{ index + 1 }}. {{ question.prompt }}</legend><p v-if="question.example" class="question-example">{{ question.example }}</p><p v-if="question.subtitle" class="muted" lang="en">{{ question.subtitle }}</p>
        <label v-for="(option, choice) in question.options" :key="choice" class="practice-option" :class="{
          chosen: answers[question.id] === choice,
          correct: result?.items[index].correct_index === choice,
          wrong: result && answers[question.id] === choice && !result.items[index].is_correct,
        }">
          <input type="radio" :name="question.id" :checked="answers[question.id] === choice" @change="choose(question.id, choice)"><span>{{ option }}</span>
        </label>
        <p v-if="result" class="practice-feedback"><strong>{{ result.items[index].is_correct ? '✓ 回答正确' : '待巩固 · 正确答案：' + question.options[result.items[index].correct_index] }}</strong><br>{{ result.items[index].explanation }}</p>
      </fieldset>
      <div v-if="result" class="quiz-result" role="status"><strong>{{ result.score }} 分</strong><span>答对 {{ result.correct }} / {{ result.total }} 题</span><span v-if="quiz.kind !== 'assessment'">{{ result.passed ? '本次测验已通过' : '本次尚未通过，请复习后重试' }}</span><button v-if="quiz.kind !== 'assessment'" class="secondary" :disabled="disabled" @click="retry">重新练习</button></div>
      <p v-if="completed" class="scope-note">本单元已完成；再次练习会保留已通过的记录。</p>
      <nav v-if="paginated" class="pagination" aria-label="题目分页"><button class="secondary" :disabled="page === 0 || submitting" @click="turn(page - 1)">← 上一题</button><span>第 {{ page + 1 }} / {{ quiz.questions.length }} 题</span><button v-if="page < quiz.questions.length - 1" class="primary" :disabled="submitting" @click="turn(page + 1)">下一题 →</button></nav>
      <p v-if="disabled && !result && !submitting" role="status">正在保存进度；若保存失败，请使用页面上方的重试或重新加载按钮。</p>
      <button v-if="!result && (!paginated || page === quiz.questions.length - 1)" class="primary" :disabled="!ready || !signedIn || disabled || submitting" @click="submit">{{ submitting ? '正在提交…' : '提交' + quiz.title }}</button>
      <p v-if="!result && paginated && page === quiz.questions.length - 1 && !ready" class="muted">还有 {{ quiz.questions.length - answered }} 题未作答，请返回补全后提交。</p>
    </template>
  </section>
</template>
