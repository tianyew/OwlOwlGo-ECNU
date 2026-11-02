<script setup lang="ts">
import { ref, computed, nextTick, watch, onMounted, onBeforeUnmount } from 'vue';
import { AuthError } from '../../shared/api/auth';
import { learningApi, emptyQuiz, type QuizState, type LearningState, type Analysis } from '../../shared/api/learning';
import LearningAnalysis from './LearningAnalysis.vue';
import HomeDashboard from '../home/HomeDashboard.vue';
import PhoneticsDemo from '../phonetics/PhoneticsDemo.vue';
import { getTopics, getPlan, submitAnswers, type Diagnosis, type Topic } from '../../shared/api/demo';
const props = defineProps<{ userId?: string; displayName?: string }>();
const emit = defineEmits<{ savingChange: [value: boolean] }>();
const view = ref<'home' | 'journey' | 'report'>(props.userId ? 'home' : 'journey');
const onboardingComplete = ref(false);
const topicDraft = ref('');
const openedUnit = ref<number | null>(null);
const unitDetails = ref<HTMLDetailsElement[]>([]);
async function goHome() { view.value = 'home'; await nextTick(); window.scrollTo({ top: 0 }); }
async function openJourney() { view.value = 'journey'; await nextTick(); window.scrollTo({ top: 0 }); }
async function openPlan(index?: number) {
  if (!plan.value) return;
  stage.value = 'plan'; openedUnit.value = index ?? null;
  await openJourney();
  if (index !== undefined) {
    unitDetails.value[index]?.scrollIntoView({ block: 'center' });
    unitDetails.value[index]?.querySelector('summary')?.focus();
  }
}
async function finishSetup() { onboardingComplete.value = true; await goHome(); }
async function openAnalysis() {
  view.value = 'report'; await nextTick(); window.scrollTo({ top: 0 });
}
const loading = ref(Boolean(props.userId));
const loadError = ref('');
const quiz = ref<QuizState>(emptyQuiz());
const completed = ref<Record<string, number[]>>({});
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
    topic: selected.value || null, completed: completed.value }));
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
    completed.value = saved.state.completed; analysis.value = saved.analysis;
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
function toggleUnit(index: number) {
  const units = completed.value[selected.value] ?? [];
  completed.value = { ...completed.value, [selected.value]: units.includes(index)
    ? units.filter(item => item !== index) : [...units, index].sort() };
}
const stage = ref<'assessment' | 'topics' | 'plan'>('assessment');
const diagnosis = ref<Diagnosis>();
const choices = ref<Topic[]>([]);
const selected = ref('');
const plan = ref<Awaited<ReturnType<typeof getPlan>>>();
const busy = ref(false);
const error = ref('');
const heading = ref<HTMLElement>();
watch([stage, quiz, selected, completed, onboardingComplete], () => {
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
  try { plan.value = await getPlan(topicDraft.value); selected.value = topicDraft.value; stage.value = 'plan'; await focusHeading(); }
  catch { error.value = '学习计划加载失败，请重试。'; }
  finally { busy.value = false; }
}
function restart() {
  onboardingComplete.value = false; topicDraft.value = ''; quiz.value = emptyQuiz(); restoredKey.value++; diagnosis.value = undefined; selected.value = ''; plan.value = undefined;
  error.value = ''; stage.value = 'assessment';
}
function changeTopic() { topicDraft.value = selected.value; stage.value = 'topics'; view.value = 'journey'; focusHeading(); }
</script>

<template>
  <p v-if="loading" role="status">正在恢复学习进度…</p>
  <div v-else-if="loadError" role="alert">{{ loadError }} <button class="secondary" @click="restore">重新加载进度</button></div>
  <template v-else>
  <div v-if="userId && saveFailed" class="save-status" role="alert">{{ saveMessage }} <button v-if="saveFailed && !conflict" class="secondary" @click="flushSave">重试保存</button><button v-if="conflict" class="secondary" @click="restore">重新加载已保存进度</button></div>
  <HomeDashboard v-if="view === 'home'" :display-name="displayName" :setup-complete="onboardingComplete" :assessment-done="quiz.stage === 'result'" :answers-count="quiz.answers.length" :plan="plan" :completed="completed[selected] ?? []" :diagnosis="diagnosis" @setup="openJourney" @learn="openPlan" @plan="openPlan()" @analysis="openAnalysis" @direction="changeTopic" />
  <section v-else-if="view === 'report'" class="journey-panel">
    <button class="text-button back-home" @click="goHome">← 返回首页</button>
    <h1>本次前测报告</h1><p>前测得分 {{ diagnosis?.score ?? '—' }} / 100 · 拼音与声调文字辨识</p>
    <LearningAnalysis :analysis="analysis" :analyzing="analyzing" :error="analysisError" :signed-in="Boolean(userId)" :waiting="dirty || saving" :answers="quiz.answers" @retry="runAnalysis" />
  </section>
  <template v-else>
  <button v-if="userId" class="text-button back-home" @click="goHome">← 返回首页</button>
  <nav class="journey-steps" aria-label="学习流程"><span :aria-current="stage === 'assessment' ? 'step' : undefined">01 前测与诊断</span><span :aria-current="stage === 'topics' ? 'step' : undefined">02 选择方向</span><span :aria-current="stage === 'plan' ? 'step' : undefined">03 学习规划</span></nav>
  <p v-if="error" role="alert">{{ error }}</p>
  <PhoneticsDemo v-if="stage === 'assessment'" :key="restoredKey" :saved="quiz" @progress="quiz = $event" @complete="selectTopic" @restart="diagnosis = undefined">
    <template #analysis><LearningAnalysis v-if="quiz.stage === 'result'" :analysis="analysis" :analyzing="analyzing" :error="analysisError" :signed-in="Boolean(userId)" :waiting="dirty || saving" :answers="quiz.answers" @retry="runAnalysis" /></template>
  </PhoneticsDemo>
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
      <ol class="unit-list"><li v-for="(unit, index) in plan.units" :key="plan.id + index"><details ref="unitDetails" :open="openedUnit === index"><summary><span class="unit-number">{{ index + 1 }}</span><span><strong>{{ unit.title }}</strong><small>{{ unit.goal }}</small></span><span>查看详情</span></summary><div class="unit-detail"><p><strong>学习目标：</strong>{{ unit.goal }}</p><p><strong>词汇与拼音：</strong>{{ unit.words }}</p><p><strong>例句：</strong>{{ unit.example }}</p><p><strong>建议练习：</strong>{{ unit.task }}</p><button class="secondary" @click="toggleUnit(index)">{{ (completed[selected] ?? []).includes(index) ? '已完成 · 取消标记' : '标记本单元完成' }}</button></div></details></li></ol>
      <div class="question-actions"><button class="secondary" @click="changeTopic">修改学习方向</button><button class="secondary" @click="restart">重新前测</button></div>
    </template>
  </section>
  </template>
  </template>
</template>
