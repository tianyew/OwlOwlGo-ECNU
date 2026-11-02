<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted, onBeforeUnmount } from 'vue';
import { AuthError } from '../../shared/api/auth';
import { learningApi, emptyQuiz, type QuizState, type LearningState, type Analysis } from '../../shared/api/learning';
import LearningAnalysis from './LearningAnalysis.vue';
import PracticeQuiz from './PracticeQuiz.vue';
import FinalReport from './FinalReport.vue';
import { postQuestions } from '../../shared/api/curriculum';
import HomeDashboard from '../home/HomeDashboard.vue';
import PhoneticsDemo from '../phonetics/PhoneticsDemo.vue';
import { getTopics, getPlan, submitAnswers, type Diagnosis, type Topic } from '../../shared/api/demo';
const props = defineProps<{ userId?: string; displayName?: string }>();
const emit = defineEmits<{ savingChange: [value: boolean] }>();
const view = ref<'home' | 'journey' | 'report'>(props.userId ? 'home' : 'journey');
const onboardingComplete = ref(false);
const topicDraft = ref('');
const openedUnit = ref(0);
async function turnUnit(index: number) {
  if (!plan.value || index < 0 || index >= plan.value.units.length) return;
  openedUnit.value = index; await nextTick(); heading.value?.focus(); window.scrollTo({ top: 0 });
}
async function goHome() { view.value = 'home'; await nextTick(); window.scrollTo({ top: 0 }); }
async function openJourney() { view.value = 'journey'; await nextTick(); window.scrollTo({ top: 0 }); }
async function openPlan(index?: number) {
  if (!plan.value) return;
  stage.value = 'plan'; outcome.value = 'plan'; openedUnit.value = index ?? 0;
  await openJourney();
}
async function finishSetup() { onboardingComplete.value = true; await goHome(); }
async function openAnalysis() {
  view.value = 'report'; await nextTick(); window.scrollTo({ top: 0 });
}
const loading = ref(Boolean(props.userId));
const loadError = ref('');
const quiz = ref<QuizState>(emptyQuiz());
const completed = ref<Record<string, number[]>>({});
const checks = ref<Record<string, { answers: number[]; submitted: boolean }>>({});
const posttests = ref<Record<string, { answers: number[]; submitted: boolean }>>({});
const outcome = ref<'plan' | 'posttest' | 'final'>('plan');
const postItems = computed(() => plan.value ? postQuestions(plan.value) : []);
const postAttempt = computed(() => posttests.value[selected.value] ?? { answers: [], submitted: false });
const postCorrect = computed(() => postItems.value.filter((q, i) => postAttempt.value.answers[i] === q.answer).length);
const allUnitsDone = computed(() => Boolean(plan.value && plan.value.units.every((_, i) => (completed.value[selected.value] ?? []).includes(i))));
function updateCheck(index: number, attempt: { answers: number[]; submitted: boolean }) {
  checks.value = { ...checks.value, [selected.value + ':' + index]: attempt };
  const units = completed.value[selected.value] ?? [];
  const passed = attempt.submitted && plan.value!.units[index].quiz.every((q, i) => attempt.answers[i] === q.answer);
  completed.value = { ...completed.value, [selected.value]: passed ? [...new Set([...units, index])].sort() : units.filter(i => i !== index) };
}
function updatePost(attempt: { answers: number[]; submitted: boolean }) {
  posttests.value = { ...posttests.value, [selected.value]: attempt };
}
async function openPost() { outcome.value = 'posttest'; await openJourney(); await focusHeading(); }
function retryPost() { updatePost({ answers: [], submitted: false }); outcome.value = 'posttest'; window.scrollTo({ top: 0 }); }

const analysis = ref<Analysis | null>(null);
const analyzing = ref(false);
const analysisError = ref('');
const saveMessage = ref('');
const saveFailed = ref(false);
const conflict = ref(false);
const dirty = ref(false);
const saving = ref(false);
const revision = ref(0);
const restoredKey = ref(0);
let pending: LearningState | null = null;
let disposed = false;
function snapshot(): LearningState {
  return JSON.parse(JSON.stringify({ content_version: 1, onboarding_complete: onboardingComplete.value, stage: stage.value, quiz: quiz.value,
    topic: selected.value || null, completed: completed.value, checks: checks.value, posttests: posttests.value }));
}
async function flushSave() {
  if (saving.value || conflict.value || disposed || !props.userId) return;
  saving.value = true; saveFailed.value = false;
  try {
    while (pending) {
      const value = pending; pending = null; saveMessage.value = '正在保存…';
      try {
        const saved = await learningApi.save(value, revision.value);
        revision.value = saved.revision;
        if (!pending) analysis.value = saved.analysis;
      } catch (reason) {
        pending = pending ?? value; saveFailed.value = true;
        conflict.value = reason instanceof AuthError && reason.status === 409;
        saveMessage.value = reason instanceof Error ? reason.message : '保存失败，请重试。';
        return;
      }
    }
    dirty.value = false; saveMessage.value = '学习进度已保存';
  } finally { saving.value = false; }
}
async function restore() {
  loading.value = true; loadError.value = '';
  try {
    const saved = await learningApi.load();
    revision.value = saved.revision; quiz.value = saved.state.quiz;
    stage.value = saved.state.stage; selected.value = saved.state.topic ?? '';
    topicDraft.value = selected.value;
    onboardingComplete.value = saved.state.onboarding_complete ?? saved.state.stage === 'plan';
    completed.value = saved.state.completed; checks.value = saved.state.checks ?? {}; posttests.value = saved.state.posttests ?? {}; analysis.value = saved.analysis;
    choices.value = await getTopics();
    diagnosis.value = quiz.value.stage === 'result' ? await submitAnswers(quiz.value.answers) : undefined;
    plan.value = selected.value ? await getPlan(selected.value) : undefined;
    restoredKey.value++; pending = null; dirty.value = false; saveFailed.value = false; conflict.value = false;
    saveMessage.value = saved.updated_at ? '已恢复保存的学习进度' : '登录后自动保存学习进度';
    await nextTick();
  } catch (reason) { loadError.value = reason instanceof Error ? reason.message : '进度加载失败'; }
  finally { loading.value = false; }
}
let lastAttempt = '';
const analysisContext = computed(() => JSON.stringify([quiz.value.stage, quiz.value.answers]));
async function runAnalysis() {
  if (disposed || !props.userId || loading.value || loadError.value || analyzing.value || dirty.value || saving.value || quiz.value.stage !== 'result') return;
  const context = analysisContext.value;
  lastAttempt = context;
  analyzing.value = true; analysisError.value = '';
  try {
    const result = await learningApi.analyze();
    if (!disposed && context === analysisContext.value) analysis.value = result;
  } catch (reason) {
    if (!disposed && context === analysisContext.value) analysisError.value = reason instanceof Error ? reason.message : '分析失败，请重试';
  } finally { analyzing.value = false; }
}
const stage = ref<'assessment' | 'topics' | 'plan'>('assessment');
const diagnosis = ref<Diagnosis>();
const choices = ref<Topic[]>([]);
const selected = ref('');
const plan = ref<Awaited<ReturnType<typeof getPlan>>>();
const busy = ref(false);
const error = ref('');
const heading = ref<HTMLElement>();
watch([stage, quiz, selected, completed, onboardingComplete, checks, posttests], () => {
  if (loading.value || loadError.value || !props.userId) return;
  pending = snapshot(); dirty.value = true; void flushSave();
}, { deep: true, flush: 'post' });
watch(analysisContext, () => { if (!loading.value) { analysis.value = null; analysisError.value = ''; } }, { flush: 'post' });
watch([loading, dirty, saving, analyzing, analysis, analysisContext], () => {
  if (quiz.value.stage !== 'result') { lastAttempt = ''; return; }
  if (!analysis.value && lastAttempt !== analysisContext.value) void runAnalysis();
}, { flush: 'post' });
watch([dirty, saving], () => emit('savingChange', dirty.value || saving.value));
function beforeUnload(event: BeforeUnloadEvent) {
  if (dirty.value) { event.preventDefault(); event.returnValue = ''; }
}
onMounted(() => { if (props.userId) void restore(); window.addEventListener('beforeunload', beforeUnload); });
onBeforeUnmount(() => { disposed = true; window.removeEventListener('beforeunload', beforeUnload); });
async function focusHeading() { await nextTick(); heading.value?.focus(); }
async function selectTopic(result: Diagnosis) {
  diagnosis.value = result; busy.value = true; error.value = '';
  try { choices.value = await getTopics(); stage.value = 'topics'; await focusHeading(); }
  catch { error.value = '学习方向加载失败，请重试。'; }
  finally { busy.value = false; }
}
async function confirm() {
  if (!topicDraft.value || busy.value) return;
  busy.value = true; error.value = '';
  try { plan.value = await getPlan(topicDraft.value); selected.value = topicDraft.value; openedUnit.value = 0; outcome.value = 'plan'; stage.value = 'plan'; await focusHeading(); }
  catch { error.value = '学习计划加载失败，请重试。'; }
  finally { busy.value = false; }
}
function restart() {
  onboardingComplete.value = false; topicDraft.value = ''; quiz.value = emptyQuiz(); restoredKey.value++; diagnosis.value = undefined; selected.value = ''; plan.value = undefined;
  error.value = ''; stage.value = 'assessment'; outcome.value = 'plan'; checks.value = {}; posttests.value = {}; completed.value = {};
}
function changeTopic() { outcome.value = 'plan'; topicDraft.value = selected.value; stage.value = 'topics'; view.value = 'journey'; focusHeading(); }
</script>

<template>
  <p v-if="loading" role="status">正在恢复学习进度…</p>
  <div v-else-if="loadError" role="alert">{{ loadError }} <button class="secondary" @click="restore">重新加载进度</button></div>
  <template v-else>
  <div v-if="userId && saveFailed" class="save-status" role="alert">{{ saveMessage }} <button v-if="saveFailed && !conflict" class="secondary" @click="flushSave">重试保存</button><button v-if="conflict" class="secondary" @click="restore">重新加载已保存进度</button></div>
  <HomeDashboard v-if="view === 'home'" :display-name="displayName" :setup-complete="onboardingComplete" :assessment-done="quiz.stage === 'result'" :answers-count="quiz.answers.length" :plan="plan" :completed="completed[selected] ?? []" :diagnosis="diagnosis" @setup="openJourney" @learn="openPlan" @plan="openPlan()" @analysis="openAnalysis" @direction="changeTopic" @posttest="openPost" />
  <section v-else-if="view === 'report'" class="journey-panel">
    <button class="text-button back-home" @click="goHome">← 返回首页</button>
    <h1>本次前测报告</h1><p>前测得分 {{ diagnosis?.score ?? '—' }} / 100 · 拼音与声调文字辨识</p>
    <LearningAnalysis :analysis="analysis" :analyzing="analyzing" :error="analysisError" :signed-in="Boolean(userId)" :waiting="dirty || saving" :answers="quiz.answers" @retry="runAnalysis" />
  </section>
  <template v-else>
  <button v-if="userId" class="text-button back-home" @click="goHome">← 返回首页</button>
  <nav class="journey-steps" aria-label="学习流程"><span :aria-current="stage === 'assessment' ? 'step' : undefined">01 前测与诊断</span><span :aria-current="stage === 'topics' ? 'step' : undefined">02 选择方向</span><span :aria-current="stage === 'plan' && outcome === 'plan' ? 'step' : undefined">03 学习规划</span><span :aria-current="outcome === 'posttest' ? 'step' : undefined">04 后测</span><span :aria-current="outcome === 'final' ? 'step' : undefined">05 诊断报告</span></nav>
  <p v-if="error" role="alert">{{ error }}</p>
  <PhoneticsDemo v-if="stage === 'assessment'" :key="restoredKey" :saved="quiz" @progress="quiz = $event" @complete="selectTopic" @restart="diagnosis = undefined">
    <template #analysis><LearningAnalysis v-if="quiz.stage === 'result'" :analysis="analysis" :analyzing="analyzing" :error="analysisError" :signed-in="Boolean(userId)" :waiting="dirty || saving" :answers="quiz.answers" @retry="runAnalysis" /></template>
  </PhoneticsDemo>
  <section v-else-if="outcome === 'final' && plan && postAttempt.submitted" class="journey-panel">
    <FinalReport :topic="plan.title" :score="Math.round(postCorrect / postItems.length * 100)" :correct="postCorrect" :total="postItems.length" :completed="(completed[selected] ?? []).length" @plan="openPlan()" @retry="retryPost" />
  </section>
  <section v-else-if="outcome === 'posttest' && plan" class="journey-panel">
    <p class="eyebrow">CHECK YOUR LEARNING</p><h1 ref="heading" tabindex="-1">{{ plan.title }} · 后测</h1>
    <p class="report-subtitle">回顾五个单元的词句理解、情境表达与综合应用。全部作答后提交，查看得分和逐题解析。</p>
    <PracticeQuiz :key="selected + '-post'" :questions="postItems" :model-value="postAttempt" paginated title="方向后测" @update:model-value="updatePost" />
    <div class="question-actions"><button class="secondary" @click="openPlan()">返回学习规划</button><button v-if="postAttempt.submitted" class="primary" @click="outcome = 'final'">查看诊断报告 →</button></div>
  </section>
  <section v-else class="journey-panel">
    <div class="section-heading"><div><p class="eyebrow">YOUR CHINESE JOURNEY</p><h1 ref="heading" tabindex="-1">{{ stage === 'topics' ? '想用汉语探索什么？' : plan?.title + ' · 学习规划' }}</h1></div></div>
    <aside class="diagnosis-summary"><strong>本次前测 {{ diagnosis?.score }} / 100</strong><p>{{ diagnosis?.advice }}</p></aside>
    <template v-if="stage === 'topics'">
      <p>选择一个感兴趣的方向，以语言学习为主线。Choose one topic.</p>
      <fieldset class="topic-grid" :disabled="busy"><legend class="sr-only">学习方向</legend><label v-for="topic in choices" :key="topic.id" class="topic-card" :class="{ selected: topicDraft === topic.id }"><input v-model="topicDraft" type="radio" name="topic" :value="topic.id"><strong>{{ topic.title }}</strong><span lang="en">{{ topic.english }}</span><p>{{ topic.description }}</p></label></fieldset>
      <div class="question-actions"><button class="secondary" @click="restart">重新前测</button><button class="primary" :disabled="!topicDraft || busy" @click="confirm">{{ busy ? '正在读取…' : '确认方向，查看学习规划 →' }}</button></div>
    </template>
    <template v-else-if="plan">
      <div v-if="!onboardingComplete && userId" class="setup-finish"><div><strong>你的第一份学习规划已准备好。</strong><p>查看下方单元目标，确认后回到首页开始学习。</p></div><button class="primary" :disabled="busy || saving || dirty" @click="finishSetup">完成设置，进入首页 →</button></div>
      <p>本方向已完成 {{ (completed[selected] ?? []).length }} / {{ plan.units.length }} 个单元</p><p>{{ plan.description }}</p><p>{{ plan.schedule }}</p>
      <div class="path-overview"><span>01–02 基础表达</span><span>03–04 情境练习</span><span>05 综合应用</span><span>后测与学习回顾 →</span></div>
      <nav class="pagination" aria-label="学习单元分页"><button class="secondary" :disabled="openedUnit === 0" @click="turnUnit(openedUnit - 1)">← 上一单元</button><span>第 {{ openedUnit + 1 }} / {{ plan.units.length }} 单元</span><button class="secondary" :disabled="openedUnit === plan.units.length - 1" @click="turnUnit(openedUnit + 1)">下一单元 →</button></nav>
      <ol class="unit-list"><li v-for="{ unit, index } in [{ unit: plan.units[openedUnit], index: openedUnit }]" :key="plan.id + index"><article class="unit-page"><header class="unit-page-heading"><span class="unit-number">{{ (completed[selected] ?? []).includes(index) ? '✓' : index + 1 }}</span><span><strong>{{ unit.title }}</strong><small>{{ unit.goal }}</small></span><span>{{ (completed[selected] ?? []).includes(index) ? '已巩固 · 复习' : '开始学习' }}</span></header><div class="unit-detail">
        <p class="eyebrow">{{ index < 2 ? 'BUILD YOUR FOUNDATION' : index < 4 ? 'PRACTISE IN CONTEXT' : 'PUT IT TOGETHER' }} · 约 20 分钟</p>
        <h3>这一课，你可以做到</h3><p>{{ unit.goal }}</p><p><strong>词汇与拼音：</strong>{{ unit.words }}</p>
        <div class="lesson-note"><strong>核心句型</strong><p>{{ unit.grammar }}</p><p>{{ unit.example }}</p></div>
        <h3>走进真实情境</h3><div class="lesson-dialogue"><p v-for="(line, lineIndex) in unit.dialogue" :key="lineIndex">{{ line }}</p></div>
        <h3>从理解到运用</h3><ol class="practice-tasks"><li v-for="task in unit.practices" :key="task">{{ task }}</li></ol>
        <PracticeQuiz :questions="unit.quiz" :model-value="checks[selected + ':' + index] ?? { answers: [], submitted: false }" :title="unit.title + ' · 单元小测'" @update:model-value="updateCheck(index, $event)" />
        <p class="scope-note">小测全部答对后自动完成本单元；有错题时先看解析，再重新练习。</p>
      </div></article></li></ol>
      <nav class="pagination" aria-label="单元底部分页"><button class="secondary" :disabled="openedUnit === 0" @click="turnUnit(openedUnit - 1)">← 上一单元</button><span>第 {{ openedUnit + 1 }} / {{ plan.units.length }} 单元</span><button v-if="openedUnit < plan.units.length - 1" class="primary" @click="turnUnit(openedUnit + 1)">下一单元 →</button><button v-else class="primary" @click="openPost">进入后测 →</button></nav>
      <article class="posttest-entry"><div><p class="eyebrow">LOOK BACK, MOVE FORWARD</p><h2>学习之后，看看掌握了多少。</h2><p>用 {{ postItems.length }} 道后测题回顾本方向，再查看诊断报告与下一步练习建议。</p><p class="muted">{{ allUnitsDone ? '所有单元已完成，可以开始后测。' : '建议按顺序完成单元与小测；也可以先尝试后测，了解需要复习的内容。' }}</p></div><button class="primary" @click="openPost">{{ postAttempt.submitted ? '查看后测结果' : '开始后测' }} →</button></article>
      <div class="question-actions"><button class="secondary" @click="changeTopic">修改学习方向</button><button class="secondary" @click="restart">重新前测</button></div>
    </template>
  </section>
  </template>
  </template>
</template>
