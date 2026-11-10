<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { AuthError } from '../../shared/api/auth';
import { curriculumApi, type Diagnosis, type Topic } from '../../shared/api/curriculum';
import { learningApi, emptyState, type LearningState, type SavedProgress, type QuizSubmission, type QuizDraft, type Analysis, type LearnerProfile as Profile, type QuizResult } from '../../shared/api/learning';
import PhoneticsDemo from '../phonetics/PhoneticsDemo.vue';
import HomeDashboard from '../home/HomeDashboard.vue';
import ServerUnitQuiz from './ServerUnitQuiz.vue';
import LearningAnalysis from './LearningAnalysis.vue';
import LearnerProfile from './LearnerProfile.vue';
import FinalReport from './FinalReport.vue';
const props = defineProps<{ userId?: string; displayName?: string }>();
const emit = defineEmits<{ savingChange: [value: boolean] }>();
const signedIn = computed(() => Boolean(props.userId));
const state = ref<LearningState>(emptyState());
const choices = ref<Topic[]>([]);
const results = ref<Record<string, QuizResult>>({});
const profile = ref<Profile>();
const topicCompletion = ref<Record<string, boolean>>({});
const analysis = ref<Analysis | null>(null);
const view = ref<'home' | 'journey' | 'report' | 'profile'>(props.userId ? 'home' : 'journey');
const outcome = ref<'plan' | 'posttest' | 'final'>('plan');
const openedUnit = ref(0);
const topicDraft = ref('');
const restoredKey = ref(0);
const quizViewKey = ref(0);
const plan = computed(() => choices.value.find(topic => topic.id === state.value.topic));
const assessment = computed(() => results.value.assessment);
const postResult = computed(() => plan.value ? results.value[plan.value.posttest_id] : undefined);
const diagnosis = computed<Diagnosis | undefined>(() => assessment.value ? {
  score: assessment.value.score, correct: assessment.value.correct,
  advice: assessment.value.score >= 80 ? '可结合主题例句继续巩固本次规则。' : '建议复习前测错题，再结合主题例句练习。',
} : undefined);
const loading = ref(true);
const loadError = ref('');
const saving = ref(false);
const grading = ref(false);
const dirty = ref(false);
const saveFailed = ref(false);
const conflict = ref(false);
const saveMessage = ref('');
const revision = ref(0);
const analyzing = ref(false);
const analysisError = ref('');
const blocked = computed(() => dirty.value || saving.value || grading.value || conflict.value);
const heading = ref<HTMLElement>();
let pending: LearningState | null = null;
let applying = false;
let disposed = false;
let lastAnalysis = '';
function snapshot(): LearningState { return JSON.parse(JSON.stringify(state.value)); }
async function apply(saved: SavedProgress, preserveLocal = false) {
  if (disposed) return;
  applying = true;
  const local = snapshot();
  const sameAssessment = results.value.assessment?.submission_id === saved.results.assessment?.submission_id;
  state.value = { ...emptyState(), ...saved.state };
  if (preserveLocal) {
    state.value.drafts = local.drafts;
    if (saved.state.quiz.stage === 'result') {
      state.value.stage = local.stage; state.value.topic = local.topic;
      state.value.onboarding_complete = local.onboarding_complete;
    }
  }
  revision.value = saved.revision; results.value = saved.results;
  profile.value = saved.profile; topicCompletion.value = saved.topic_completion;
  analysis.value = saved.analysis ?? (sameAssessment ? analysis.value : null);
  await nextTick(); applying = false;
}
async function restore() {
  loading.value = true; loadError.value = '';
  try {
    const [catalog, saved] = await Promise.all([curriculumApi.load(), props.userId ? learningApi.load() : Promise.resolve(null)]);
    if (disposed) return;
    choices.value = catalog.topics; pending = null;
    if (saved) await apply(saved);
    topicDraft.value = state.value.topic ?? '';
    restoredKey.value++; dirty.value = false; saveFailed.value = false; conflict.value = false;
  } catch (reason) { loadError.value = reason instanceof Error ? reason.message : '学习内容加载失败，请重试。'; }
  finally { loading.value = false; }
}
async function flushSave() {
  if (!props.userId || saving.value || grading.value || conflict.value || disposed) return;
  saving.value = true; saveFailed.value = false;
  try {
    while (pending) {
      const value = pending; pending = null;
      try {
        const saved = await learningApi.save(value, revision.value);
        await apply(saved, Boolean(pending));
      } catch (reason) {
        pending = pending ?? value; saveFailed.value = true;
        conflict.value = reason instanceof AuthError && reason.status === 409;
        saveMessage.value = reason instanceof Error ? reason.message : '保存失败，请重试。';
        return;
      }
    }
    dirty.value = false;
  } finally { saving.value = false; }
}
function mutationError(reason: unknown) {
  if (reason instanceof AuthError && reason.status === 409) {
    conflict.value = true; saveFailed.value = true; saveMessage.value = reason.message;
  }
}
async function submitQuiz(id: string, body: QuizSubmission) {
  if (blocked.value) throw new Error('请先保存或重新加载学习进度。');
  grading.value = true;
  try {
    const response = await learningApi.submit(id, body, revision.value);
    await apply(response.progress, Boolean(pending));
    return response;
  } catch (reason) { mutationError(reason); throw reason; }
  finally { grading.value = false; if (pending) void flushSave(); }
}
function updateDraft(id: string, draft: QuizDraft) {
  state.value.drafts = { ...state.value.drafts, [id]: draft };
}
async function restart() {
  if (blocked.value) return;
  grading.value = true;
  try {
    if (props.userId) await apply(await learningApi.reset(revision.value));
    else state.value = emptyState();
    topicDraft.value = ''; view.value = 'journey'; outcome.value = 'plan'; restoredKey.value++;
    analysisError.value = ''; lastAnalysis = '';
  } catch (reason) {
    mutationError(reason); saveFailed.value = true;
    saveMessage.value = reason instanceof Error ? reason.message : '重新测评失败，请重试。';
  } finally { grading.value = false; }
}
async function runAnalysis() {
  if (!props.userId || !assessment.value || loading.value || blocked.value || analyzing.value) return;
  const context = assessment.value.submission_id;
  lastAnalysis = context; analyzing.value = true; analysisError.value = '';
  try {
    const value = await learningApi.analyze();
    if (!disposed && assessment.value?.submission_id === context) analysis.value = value;
  } catch (reason) {
    if (!disposed && assessment.value?.submission_id === context) analysisError.value = reason instanceof Error ? reason.message : '分析失败，请重试。';
  } finally { analyzing.value = false; }
}
watch(state, () => {
  if (loading.value || applying || loadError.value || !props.userId) return;
  pending = snapshot(); dirty.value = true; void flushSave();
}, { deep: true, flush: 'post' });
watch([loading, blocked, analyzing, assessment, analysis], () => {
  if (!assessment.value) { lastAnalysis = ''; return; }
  if (!analysis.value && lastAnalysis !== assessment.value.submission_id) void runAnalysis();
}, { flush: 'post' });
watch([dirty, saving, grading], () => emit('savingChange', dirty.value || saving.value || grading.value));
async function focusHeading() { await nextTick(); heading.value?.focus(); window.scrollTo({ top: 0 }); }
function selectTopic() { state.value.stage = 'topics'; view.value = 'journey'; void focusHeading(); }
function confirm() {
  if (!topicDraft.value || blocked.value) return;
  state.value.topic = topicDraft.value; state.value.stage = 'plan';
  openedUnit.value = 0; outcome.value = 'plan'; void focusHeading();
}
function changeTopic() { topicDraft.value = state.value.topic ?? ''; outcome.value = 'plan'; selectTopic(); }
function goHome() { view.value = 'home'; window.scrollTo({ top: 0 }); }
function openPlan(index = 0) {
  if (!plan.value) return;
  openedUnit.value = index; state.value.stage = 'plan'; outcome.value = 'plan'; view.value = 'journey'; void focusHeading();
}
function turnUnit(index: number) { if (plan.value && index >= 0 && index < plan.value.units.length) { openedUnit.value = index; void focusHeading(); } }
function openPost() { outcome.value = 'posttest'; view.value = 'journey'; void focusHeading(); }
function retryPost() {
  if (!plan.value) return;
  updateDraft(plan.value.posttest_id, { content_version: 1, current: 0, answers: [] });
  quizViewKey.value++; openPost();
}
function finishSetup() { state.value.onboarding_complete = true; goHome(); }
function beforeUnload(event: BeforeUnloadEvent) { if (dirty.value || saving.value || grading.value) { event.preventDefault(); event.returnValue = ''; } }
onMounted(() => { void restore(); window.addEventListener('beforeunload', beforeUnload); });
onBeforeUnmount(() => { disposed = true; window.removeEventListener('beforeunload', beforeUnload); });
</script>
<template>
  <p v-if="loading" role="status">正在加载学习内容与进度…</p>
  <div v-else-if="loadError" role="alert">{{ loadError }} <button class="secondary" @click="restore">重新加载进度</button></div>
  <template v-else>
    <div v-if="saveFailed" class="save-status" role="alert">{{ saveMessage }} <button v-if="!conflict && dirty" class="secondary" @click="flushSave">重试保存</button><button class="secondary" @click="restore">重新加载已保存进度</button></div>
    <fieldset class="journey-controls" :disabled="grading" style="border: 0; padding: 0; margin: 0; min-width: 0">
    <HomeDashboard v-if="view === 'home' && signedIn" :display-name="displayName" :setup-complete="state.onboarding_complete" :assessment-done="Boolean(assessment)" :answers-count="state.drafts.assessment?.answers.length ?? 0" :plan="plan" :completed="state.completed[state.topic ?? ''] ?? []" :diagnosis="diagnosis" @setup="view = 'journey'" @learn="openPlan" @plan="openPlan()" @analysis="view = 'report'" @profile="view = 'profile'" @direction="changeTopic" @posttest="openPost" />
    <section v-else-if="view === 'profile' && profile" class="journey-panel"><button class="text-button" @click="goHome">← 返回首页</button><h1>我的学习画像</h1><LearnerProfile :profile="profile" /></section>
    <section v-else-if="view === 'report'" class="journey-panel"><button class="text-button" @click="goHome">← 返回首页</button><h1>本次前测报告</h1><p>前测得分 {{ assessment?.score ?? '—' }} / 100 · 拼音与声调文字辨识</p><LearningAnalysis :analysis="analysis" :assessment="assessment" :analyzing="analyzing" :error="analysisError" :signed-in="signedIn" :waiting="blocked" @retry="runAnalysis" /></section>
    <template v-else>
      <button v-if="signedIn" class="text-button back-home" @click="goHome">← 返回首页</button>
      <nav class="journey-steps" aria-label="学习流程"><span :aria-current="state.stage === 'assessment' ? 'step' : undefined">01 前测与诊断</span><span :aria-current="state.stage === 'topics' ? 'step' : undefined">02 选择方向</span><span :aria-current="state.stage === 'plan' && outcome === 'plan' ? 'step' : undefined">03 学习规划</span><span :aria-current="outcome === 'posttest' ? 'step' : undefined">04 后测</span><span :aria-current="outcome === 'final' ? 'step' : undefined">05 学习报告</span></nav>
      <PhoneticsDemo v-if="state.stage === 'assessment'" :key="restoredKey" :signed-in="signedIn" :disabled="blocked" :draft="state.drafts.assessment" :result="assessment" :submit="submitQuiz" @draft="updateDraft" @complete="selectTopic" @restart="restart" @browse="selectTopic"><template #analysis><LearningAnalysis :analysis="analysis" :assessment="assessment" :analyzing="analyzing" :error="analysisError" :signed-in="signedIn" :waiting="blocked" @retry="runAnalysis" /></template></PhoneticsDemo>
      <section v-else-if="outcome === 'final' && plan && postResult && profile" class="journey-panel"><FinalReport :topic="plan.title" :result="postResult" :assessment="assessment" :completed="(state.completed[plan.id] ?? []).length" :topic-complete="topicCompletion[plan.id] ?? false" :profile="profile" @plan="openPlan()" @retry="retryPost" /></section>
      <section v-else-if="outcome === 'posttest' && plan" class="journey-panel"><p class="eyebrow">CHECK YOUR LEARNING</p><h1 ref="heading" tabindex="-1">{{ plan.title }} · 后测</h1><p>回顾五个单元的词句理解与情境辨识，完成 10 道题后提交。</p><ServerUnitQuiz :key="plan.posttest_id + restoredKey + quizViewKey" :quiz-id="plan.posttest_id" :signed-in="signedIn" :disabled="blocked" :draft="state.drafts[plan.posttest_id]" :submit="submitQuiz" @draft="updateDraft" /><div class="question-actions"><button class="secondary" @click="openPlan()">返回学习规划</button><button v-if="postResult && !state.drafts[plan.posttest_id]" class="primary" @click="outcome = 'final'">查看学习报告 →</button></div></section>
      <section v-else class="journey-panel">
        <div class="section-heading"><div><p class="eyebrow">YOUR CHINESE JOURNEY</p><h1 ref="heading" tabindex="-1">{{ state.stage === 'topics' ? '想用汉语探索什么？' : plan?.title + ' · 学习规划' }}</h1></div></div>
        <aside v-if="diagnosis" class="diagnosis-summary"><strong>本次前测 {{ diagnosis.score }} / 100</strong><p>{{ diagnosis.advice }}</p></aside>
        <template v-if="state.stage === 'topics'"><p>选择一个感兴趣的方向，以语言学习为主线。</p><fieldset class="topic-grid"><legend class="sr-only">学习方向</legend><label v-for="topic in choices" :key="topic.id" class="topic-card" :class="{ selected: topicDraft === topic.id }"><input v-model="topicDraft" type="radio" name="topic" :value="topic.id"><strong>{{ topic.title }}</strong><span lang="en">{{ topic.english }}</span><p>{{ topic.description }}</p></label></fieldset><div class="question-actions"><button class="secondary" :disabled="blocked" @click="restart">重新前测</button><button class="primary" :disabled="!topicDraft || blocked" @click="confirm">确认方向，查看学习规划 →</button></div></template>
        <template v-else-if="plan">
          <div v-if="!state.onboarding_complete && signedIn" class="setup-finish"><div><strong>你的第一份学习规划已准备好。</strong><p>查看单元目标，确认后回到首页开始学习。</p></div><button class="primary" :disabled="blocked" @click="finishSetup">完成设置，进入首页 →</button></div>
          <p>本方向已完成 {{ (state.completed[plan.id] ?? []).length }} / {{ plan.units.length }} 个单元</p><p>{{ plan.description }}</p><p>{{ plan.schedule }}</p><p v-if="topicCompletion[plan.id]">本方向已完成，欢迎继续复习。</p>
          <nav class="pagination" aria-label="学习单元分页"><button class="secondary" :disabled="openedUnit === 0" @click="turnUnit(openedUnit - 1)">← 上一单元</button><span>第 {{ openedUnit + 1 }} / {{ plan.units.length }} 单元</span><button class="secondary" :disabled="openedUnit === plan.units.length - 1" @click="turnUnit(openedUnit + 1)">下一单元 →</button></nav>
          <ol class="unit-list"><li v-for="{ unit, index } in [{ unit: plan.units[openedUnit], index: openedUnit }]" :key="plan.id + index"><article class="unit-page"><header class="unit-page-heading"><span class="unit-number">{{ (state.completed[plan.id] ?? []).includes(index) ? '✓' : index + 1 }}</span><span><strong>{{ unit.title }}</strong><small>{{ unit.goal }}</small></span><span>{{ (state.completed[plan.id] ?? []).includes(index) ? '已完成 · 复习' : '开始学习' }}</span></header><div class="unit-detail"><h3>这一课，你可以做到</h3><p>{{ unit.goal }}</p><p><strong>词汇与拼音：</strong>{{ unit.words }}</p><div class="lesson-note"><strong>核心句型</strong><p>{{ unit.grammar }}</p><p>{{ unit.example }}</p></div><h3>走进真实情境</h3><div class="lesson-dialogue"><p v-for="(line, i) in unit.dialogue" :key="i">{{ line }}</p></div><h3>从理解到运用</h3><ol class="practice-tasks"><li v-for="task in unit.practices" :key="task">{{ task }}</li></ol><ServerUnitQuiz :key="unit.quiz_id + restoredKey" :quiz-id="unit.quiz_id" :signed-in="signedIn" :disabled="blocked" :draft="state.drafts[unit.quiz_id]" :submit="submitQuiz" @draft="updateDraft" /><p class="scope-note">小测全部答对后完成本单元；完成记录会保留，最新练习成绩另行记录。</p></div></article></li></ol>
          <nav class="pagination" aria-label="单元底部分页"><button class="secondary" :disabled="openedUnit === 0" @click="turnUnit(openedUnit - 1)">← 上一单元</button><span>第 {{ openedUnit + 1 }} / {{ plan.units.length }} 单元</span><button v-if="openedUnit < plan.units.length - 1" class="primary" @click="turnUnit(openedUnit + 1)">下一单元 →</button><button v-else class="primary" @click="openPost">进入后测 →</button></nav>
          <article class="posttest-entry"><div><h2>学习之后，看看掌握了多少。</h2><p>可先尝试后测了解待复习内容；方向完成需要五个单元均通过，且后测曾达到 60 分。</p></div><button class="primary" @click="openPost">{{ postResult ? '查看后测结果' : '开始后测' }} →</button></article>
          <div class="question-actions"><button class="secondary" @click="changeTopic">修改学习方向</button><button class="secondary" :disabled="blocked" @click="restart">重新前测</button><button v-if="signedIn" class="secondary" @click="view = 'profile'">查看学习画像</button></div>
        </template>
      </section>
    </template>
    </fieldset>
  </template>
</template>
