<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue';
import type { Diagnosis } from '../../shared/api/curriculum';
import { useLearningProgress } from './useLearningProgress';
import PhoneticsDemo from '../phonetics/PhoneticsDemo.vue';
import HomeDashboard from '../home/HomeDashboard.vue';
import ServerUnitQuiz from './ServerUnitQuiz.vue';
import LearningAnalysis from './LearningAnalysis.vue';
import LearnerProfile from './LearnerProfile.vue';
import FinalReport from './FinalReport.vue';
import AppIcon from '../../shared/components/AppIcon.vue';
import StudyCompanion from '../companion/StudyCompanion.vue';
import type { CompanionContext, CompanionQuizContext } from '../companion/demo';
const props = defineProps<{ userId?: string; displayName?: string }>();
const emit = defineEmits<{ savingChange: [value: boolean] }>();
const signedIn = computed(() => Boolean(props.userId));
const {
  state, choices, results, profile, topicCompletion, analysis, assessment,
  loading, loadError, saving, grading, dirty, saveFailed, conflict, saveMessage,
  analyzing, analysisError, blocked, busy, restoredKey,
  restore, flushSave, submitQuiz, updateDraft, resetAssessment, runAnalysis,
} = useLearningProgress(() => props.userId);
const view = ref<'home' | 'journey' | 'report' | 'profile'>(props.userId ? 'home' : 'journey');
const outcome = ref<'plan' | 'posttest' | 'final'>('plan');
const openedUnit = ref(0);
const topicDraft = ref('');
const quizViewKey = ref(0);
const plan = computed(() => choices.value.find(topic => topic.id === state.value.topic));
const postResult = computed(() => plan.value ? results.value[plan.value.posttest_id] : undefined);
const diagnosis = computed<Diagnosis | undefined>(() => assessment.value ? {
  score: assessment.value.score, correct: assessment.value.correct,
  advice: assessment.value.score >= 80 ? '可结合主题例句继续巩固本次规则。' : '建议复习前测错题，再结合主题例句练习。',
} : undefined);
const heading = ref<HTMLElement>();
const workspace = ref<HTMLElement>();
const navActive = computed(() => view.value === 'home' ? 'home' : view.value === 'profile' || view.value === 'report' ? 'profile' : state.value.stage === 'topics' ? 'topics' : 'learn');
const pageTitle = computed(() => ({ home: '学习首页', profile: '学习记录', topics: '探索学习方向', learn: '我的学习' })[navActive.value]);
const completedCount = computed(() => (state.value.completed[state.value.topic ?? ''] ?? []).length);
const companionQuiz = ref<CompanionQuizContext | null>(null);
const companionQuizId = computed(() => {
  if (view.value !== 'journey' || state.value.stage === 'topics') return null;
  if (state.value.stage === 'assessment') return 'assessment';
  if (outcome.value === 'posttest') return plan.value?.posttest_id ?? null;
  if (outcome.value === 'plan') return plan.value?.units[openedUnit.value]?.quiz_id ?? null;
  return null;
});
function updateCompanionQuiz(value: CompanionQuizContext) {
  if (value.quizId === companionQuizId.value) companionQuiz.value = value;
}
watch([companionQuizId, restoredKey], () => { companionQuiz.value = null; }, { flush: 'sync' });
const companionContext = computed<CompanionContext>(() => {
  let scene: CompanionContext['scene'] = 'welcome';
  if (!loading.value && !loadError.value) {
    scene = view.value === 'home' ? 'home' : view.value === 'profile' ? 'profile'
      : view.value === 'report' ? 'report' : state.value.stage === 'assessment' ? 'assessment'
      : state.value.stage === 'topics' ? 'topics' : outcome.value === 'posttest' ? 'posttest'
      : outcome.value === 'final' ? 'report' : 'lesson';
  }
  const unit = scene === 'lesson' ? plan.value?.units[openedUnit.value] : undefined;
  const quiz = companionQuiz.value?.quizId === companionQuizId.value ? companionQuiz.value : null;
  const submitted = quiz?.submitted ?? false;
  const result = quiz && submitted ? results.value[quiz.quizId] : undefined;
  const recent = signedIn.value ? Object.values(results.value).sort((a, b) =>
    (Date.parse(b.created_at ?? '') || 0) - (Date.parse(a.created_at ?? '') || 0)) : [];
  const review = quiz ? (submitted && result ? [result] : [])
    : ['home', 'profile', 'report'].includes(scene) ? recent : [];
  const labels = { welcome: '学习空间', home: '学习首页', topics: '选择学习方向',
    assessment: '拼音与声调前测', posttest: `${plan.value?.title ?? ''} · 方向后测`,
    lesson: `${plan.value?.title ?? ''} · 第 ${openedUnit.value + 1} 单元`,
    profile: '我的学习画像', report: view.value === 'report' ? '前测报告' : '阶段学习报告' };
  return {
    key: `${scene}:${unit?.id ?? ''}:${quiz?.question.id ?? companionQuizId.value ?? ''}:${submitted ? result?.submission_id ?? 'result' : 'practice'}`,
    scene, label: unit ? `${labels.lesson} · ${unit.title}` : labels[scene], signedIn: signedIn.value,
    lesson: unit ? { title: unit.title, goal: unit.goal, grammar: unit.grammar, example: unit.example, words: unit.words } : undefined,
    question: quiz?.question, submitted,
    mistakes: review.flatMap(item => item.items.filter(q => !q.is_correct).map(q => ({
      prompt: q.prompt, selected: q.options[q.selected_index], correct: q.options[q.correct_index], explanation: q.explanation,
    }))).slice(0, 3),
    profile: signedIn.value && profile.value ? { evidenceCount: profile.value.evidence_count,
      repeatCount: profile.value.repeat_count, focusAreas: profile.value.focus_areas, nextSteps: profile.value.next_steps } : undefined,
  };
});
function resumeLearning() { view.value = 'journey'; outcome.value = 'plan'; void focusHeading(); }
function goLearning() {
  if (plan.value) openPlan(openedUnit.value);
  else { state.value.stage = 'assessment'; resumeLearning(); }
}
function openProfile() { view.value = 'profile'; void focusHeading(); }
watch([view, () => state.value.stage, outcome], () => { void focusHeading(); });
watch(restoredKey, () => { topicDraft.value = state.value.topic ?? ''; });
watch(busy, value => emit('savingChange', value));
async function restart() {
  if (await resetAssessment()) {
    topicDraft.value = ''; view.value = 'journey'; outcome.value = 'plan';
  }
}
async function focusHeading() { await nextTick(); (heading.value ?? workspace.value)?.focus(); window.scrollTo({ top: 0 }); }
function selectTopic() { outcome.value = 'plan'; state.value.stage = 'topics'; view.value = 'journey'; void focusHeading(); }
function confirm() {
  if (!topicDraft.value || blocked.value) return;
  state.value.topic = topicDraft.value; state.value.stage = 'plan';
  openedUnit.value = 0; outcome.value = 'plan'; void focusHeading();
}
function changeTopic() { topicDraft.value = state.value.topic ?? ''; outcome.value = 'plan'; selectTopic(); }
function goHome() { view.value = 'home'; void focusHeading(); }
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
onBeforeUnmount(() => emit('savingChange', false));
</script>
<template>
  <div v-if="loading" class="workspace-loading" role="status"><span class="loading-orbit" aria-hidden="true"></span><h2>正在准备你的学习空间</h2><p>正在加载学习内容与进度…</p><div class="skeleton-lines" aria-hidden="true"><i></i><i></i><i></i></div></div>
  <div v-else-if="loadError" class="workspace-loading load-error" role="alert"><AppIcon name="book" /><h2>学习内容暂时没有加载成功</h2><p>{{ loadError }}</p><p class="muted">请检查网络连接后重试，已保存的学习记录仍会保留。</p><button class="primary" @click="restore">重新加载进度</button></div>
  <div v-else class="learning-workspace">
    <aside class="learning-sidebar" aria-label="学习导航">
      <div class="sidebar-intro"><strong>学习空间</strong></div>
      <nav class="workspace-nav" aria-label="主导航">
        <button :aria-current="navActive === 'home' ? 'page' : undefined" :disabled="grading" @click="goHome"><AppIcon name="home" /><span>学习首页</span></button>
        <button :aria-current="navActive === 'learn' ? 'page' : undefined" :disabled="grading" @click="goLearning"><AppIcon name="book" /><span>我的学习</span><span class="nav-dot" v-if="state.drafts.assessment && !assessment"></span></button>
        <button :aria-current="navActive === 'topics' ? 'page' : undefined" :disabled="grading || (signedIn && !assessment)" :title="signedIn && !assessment ? '完成前测后选择学习方向' : '浏览四个学习方向'" @click="changeTopic"><AppIcon name="compass" /><span>学习方向</span></button>
        <button :aria-current="navActive === 'profile' ? 'page' : undefined" :disabled="grading || !signedIn" @click="openProfile"><AppIcon name="chart" /><span>学习画像</span></button>
      </nav>
      <p v-if="!signedIn" class="sidebar-hint">登录后可保存学习记录。</p>
      <p v-else-if="!assessment" class="sidebar-hint">完成前测后解锁学习方向。</p>
      <div v-if="plan" class="sidebar-plan"><AppIcon :name="plan.id" /><strong>{{ plan.title }}</strong><p>{{ completedCount }} / {{ plan.units.length }} 个单元已完成</p><progress :value="completedCount" :max="plan.units.length" aria-label="当前方向完成进度"></progress></div>
      <details class="sidebar-help">
        <summary><AppIcon name="bulb" /><strong>学习小贴士</strong><AppIcon name="chevron" class="help-chevron" /></summary>
        <div class="sidebar-help-content"><p>先读例句，再做练习。提交后查看解析，答错可以重练。</p><p>离开前，确认页面显示「进度已保存」。</p></div>
      </details>
    </aside>
    <div ref="workspace" class="workspace-main" tabindex="-1">
      <div class="workspace-toolbar"><strong>{{ pageTitle }}</strong><span class="sync-indicator" :class="{ warning: saveFailed, pending: dirty || saving || grading }" role="status"><span aria-hidden="true">{{ saveFailed ? '!' : dirty || saving || grading ? '◌' : '✓' }}</span>{{ !signedIn ? '游客浏览模式' : saveFailed ? '进度尚未保存' : grading ? '正在提交作答…' : dirty || saving ? '正在保存进度…' : '进度已保存' }}</span></div>
    <div v-if="saveFailed" class="save-status" role="alert">{{ saveMessage }} <button v-if="!conflict && dirty" class="secondary" @click="flushSave">重试保存</button><button class="secondary" @click="restore">重新加载已保存进度</button></div>
    <fieldset class="journey-controls" :disabled="grading" style="border: 0; padding: 0; margin: 0; min-width: 0">
    <HomeDashboard v-if="view === 'home'" :display-name="displayName" :topics="choices" :setup-complete="state.onboarding_complete" :assessment-done="Boolean(assessment)" :answers-count="state.drafts.assessment?.answers.length ?? 0" :plan="plan" :completed="state.completed[state.topic ?? ''] ?? []" :diagnosis="diagnosis" @setup="resumeLearning" @learn="openPlan" @plan="openPlan()" @analysis="view = 'report'" @profile="openProfile" @direction="changeTopic" @posttest="openPost" />
    <section v-else-if="view === 'profile' && profile" class="journey-panel"><button class="text-button" @click="goHome">← 返回首页</button><h1>我的学习画像</h1><LearnerProfile :profile="profile" /></section>
    <section v-else-if="view === 'report'" class="journey-panel"><button class="text-button" @click="goHome">← 返回首页</button><h1>本次前测报告</h1><p>前测得分 {{ assessment?.score ?? '—' }} / 100 · 拼音与声调文字辨识</p><LearningAnalysis :analysis="analysis" :assessment="assessment" :analyzing="analyzing" :error="analysisError" :signed-in="signedIn" :waiting="blocked" @retry="runAnalysis" /></section>
    <template v-else>
      <button v-if="signedIn" class="text-button back-home" @click="goHome">← 返回首页</button>
      <nav class="journey-steps" aria-label="学习流程"><span :aria-current="state.stage === 'assessment' ? 'step' : undefined">01 前测与诊断</span><span :aria-current="state.stage === 'topics' ? 'step' : undefined">02 选择方向</span><span :aria-current="state.stage === 'plan' && outcome === 'plan' ? 'step' : undefined">03 学习规划</span><span :aria-current="outcome === 'posttest' ? 'step' : undefined">04 后测</span><span :aria-current="outcome === 'final' ? 'step' : undefined">05 学习报告</span></nav>
      <PhoneticsDemo v-if="state.stage === 'assessment'" :key="restoredKey" :signed-in="signedIn" :disabled="blocked" :draft="state.drafts.assessment" :result="assessment" :submit="submitQuiz" @draft="updateDraft" @context="updateCompanionQuiz" @complete="selectTopic" @restart="restart" @browse="selectTopic"><template #analysis><LearningAnalysis :analysis="analysis" :assessment="assessment" :analyzing="analyzing" :error="analysisError" :signed-in="signedIn" :waiting="blocked" @retry="runAnalysis" /></template></PhoneticsDemo>
      <section v-else-if="outcome === 'final' && plan && postResult && profile" class="journey-panel"><FinalReport :topic="plan.title" :result="postResult" :assessment="assessment" :completed="(state.completed[plan.id] ?? []).length" :topic-complete="topicCompletion[plan.id] ?? false" :profile="profile" @plan="openPlan()" @retry="retryPost" /></section>
      <section v-else-if="outcome === 'posttest' && plan" class="journey-panel"><h1 ref="heading" tabindex="-1">{{ plan.title }} · 后测</h1><p>回顾五个单元的词句理解与情境辨识，完成 10 道题后提交。</p><ServerUnitQuiz :key="plan.posttest_id + restoredKey + quizViewKey" :quiz-id="plan.posttest_id" :signed-in="signedIn" :disabled="blocked" :draft="state.drafts[plan.posttest_id]" :submit="submitQuiz" @draft="updateDraft" @context="updateCompanionQuiz" /><div class="question-actions"><button class="secondary" @click="openPlan()">返回学习规划</button><button v-if="postResult && !state.drafts[plan.posttest_id]" class="primary" @click="outcome = 'final'">查看学习报告 →</button></div></section>
      <section v-else class="journey-panel">
        <div class="section-heading"><div><h1 ref="heading" tabindex="-1">{{ state.stage === 'topics' ? '想用汉语探索什么？' : plan?.title + ' · 学习规划' }}</h1></div></div>
        <aside v-if="diagnosis" class="diagnosis-summary"><strong>本次前测 {{ diagnosis.score }} / 100</strong><p>{{ diagnosis.advice }}</p></aside>
        <template v-if="state.stage === 'topics'"><p>选择一个感兴趣的方向，以语言学习为主线。</p><fieldset class="topic-grid"><legend class="sr-only">学习方向</legend><label v-for="topic in choices" :key="topic.id" :data-topic="topic.id" class="topic-card" :class="{ selected: topicDraft === topic.id }"><input v-model="topicDraft" type="radio" name="topic" :value="topic.id"><span class="topic-symbol"><AppIcon :name="topic.id" /></span><strong>{{ topic.title }}</strong><p>{{ topic.description }}</p><span class="topic-card-meta">{{ topic.units.length }} 个单元 <span>{{ topicDraft === topic.id ? '✓ 已选择' : '' }}</span></span></label></fieldset><div class="question-actions"><button class="secondary" :disabled="blocked" @click="restart">重新前测</button><button class="primary" :disabled="!topicDraft || blocked" @click="confirm">确认方向，查看学习规划 →</button></div></template>
        <template v-else-if="plan">
          <div v-if="!state.onboarding_complete && signedIn" class="setup-finish"><div><strong>你的第一份学习规划已准备好。</strong></div><button class="primary" :disabled="blocked" @click="finishSetup">完成设置，进入首页 →</button></div>
          <p>本方向已完成 {{ (state.completed[plan.id] ?? []).length }} / {{ plan.units.length }} 个单元</p><details class="context-help"><summary>学习安排</summary><p>{{ plan.description }}</p><p>{{ plan.schedule }}</p></details><p v-if="topicCompletion[plan.id]">本方向已完成，欢迎继续复习。</p>
          <nav class="pagination" aria-label="学习单元分页"><button class="secondary" :disabled="openedUnit === 0" @click="turnUnit(openedUnit - 1)">← 上一单元</button><span>第 {{ openedUnit + 1 }} / {{ plan.units.length }} 单元</span><button class="secondary" :disabled="openedUnit === plan.units.length - 1" @click="turnUnit(openedUnit + 1)">下一单元 →</button></nav>
          <ol class="unit-list"><li v-for="{ unit, index } in [{ unit: plan.units[openedUnit], index: openedUnit }]" :key="plan.id + index"><article class="unit-page"><header class="unit-page-heading"><span class="unit-number">{{ (state.completed[plan.id] ?? []).includes(index) ? '✓' : index + 1 }}</span><span><strong>{{ unit.title }}</strong></span><span>{{ (state.completed[plan.id] ?? []).includes(index) ? '已完成 · 复习' : '开始学习' }}</span></header><div class="unit-detail"><h3>这一课，你可以做到</h3><p>{{ unit.goal }}</p><p><strong>词汇与拼音：</strong>{{ unit.words }}</p><div class="lesson-note"><strong>核心句型</strong><p>{{ unit.grammar }}</p><p>{{ unit.example }}</p></div><h3>走进真实情境</h3><div class="lesson-dialogue"><p v-for="(line, i) in unit.dialogue" :key="i">{{ line }}</p></div><h3>从理解到运用</h3><ol class="practice-tasks"><li v-for="task in unit.practices" :key="task">{{ task }}</li></ol><ServerUnitQuiz :key="unit.quiz_id + restoredKey" :quiz-id="unit.quiz_id" :signed-in="signedIn" :disabled="blocked" :draft="state.drafts[unit.quiz_id]" :submit="submitQuiz" @draft="updateDraft" @context="updateCompanionQuiz" /></div></article></li></ol>
          <nav class="pagination" aria-label="单元底部分页"><button class="secondary" :disabled="openedUnit === 0" @click="turnUnit(openedUnit - 1)">← 上一单元</button><span>第 {{ openedUnit + 1 }} / {{ plan.units.length }} 单元</span><button v-if="openedUnit < plan.units.length - 1" class="primary" @click="turnUnit(openedUnit + 1)">下一单元 →</button><button v-else class="primary" @click="openPost">进入后测 →</button></nav>
          <article class="posttest-entry"><div><h2>学习之后，看看掌握了多少。</h2><p>可先尝试后测了解待复习内容；方向完成需要五个单元均通过，且后测曾达到 60 分。</p></div><button class="primary" @click="openPost">{{ postResult ? '查看后测结果' : '开始后测' }} →</button></article>
          <nav class="plan-tools" aria-label="学习管理">
            <button class="plan-tool" @click="changeTopic"><AppIcon name="compass" /><span>修改学习方向</span></button>
            <button v-if="signedIn" class="plan-tool plan-tool-profile" @click="openProfile"><AppIcon name="chart" /><span>查看学习画像</span></button>
            <button class="plan-tool plan-tool-reset" :disabled="blocked" @click="restart"><AppIcon name="restart" /><span>重新前测</span></button>
          </nav>
        </template>
      </section>
    </template>
    </fieldset>
    </div>
  </div>
  <StudyCompanion :context="companionContext" />
</template>
