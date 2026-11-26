import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { AuthError } from '../../shared/api/auth';
import { curriculumApi, type Topic } from '../../shared/api/curriculum';
import {
  learningApi, emptyState, type LearningState, type SavedProgress, type QuizSubmission,
  type QuizDraft, type Analysis, type LearnerProfile, type QuizResult,
} from '../../shared/api/learning';

/** Per-account progress lifecycle. The owner must remount when the account changes. */
export function useLearningProgress(getUserId: () => string | undefined) {
  const state = ref<LearningState>(emptyState());
  const choices = ref<Topic[]>([]);
  const results = ref<Record<string, QuizResult>>({});
  const profile = ref<LearnerProfile>();
  const topicCompletion = ref<Record<string, boolean>>({});
  const analysis = ref<Analysis | null>(null);
  const restoredKey = ref(0);
  const assessment = computed(() => results.value.assessment);
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
  const busy = computed(() => dirty.value || saving.value || grading.value);
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
      const [catalog, saved] = await Promise.all([curriculumApi.load(), getUserId() ? learningApi.load() : Promise.resolve(null)]);
      if (disposed) return;
      choices.value = catalog.topics; pending = null;
      if (saved) await apply(saved);
      restoredKey.value++; dirty.value = false; saveFailed.value = false; conflict.value = false;
    } catch (reason) { loadError.value = reason instanceof Error ? reason.message : '学习内容加载失败，请重试。'; }
    finally { loading.value = false; }
  }
  async function flushSave() {
    if (!getUserId() || saving.value || grading.value || conflict.value || disposed) return;
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
  async function resetAssessment(): Promise<boolean> {
    if (blocked.value) return false;
    grading.value = true;
    try {
      if (getUserId()) await apply(await learningApi.reset(revision.value));
      else state.value = emptyState();
      restoredKey.value++;
      analysisError.value = ''; lastAnalysis = '';
      return true;
    } catch (reason) {
      mutationError(reason); saveFailed.value = true;
      saveMessage.value = reason instanceof Error ? reason.message : '重新测评失败，请重试。';
      return false;
    } finally { grading.value = false; }
  }
  async function runAnalysis() {
    if (!getUserId() || !assessment.value || loading.value || blocked.value || analyzing.value) return;
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
    if (loading.value || applying || loadError.value || !getUserId()) return;
    pending = snapshot(); dirty.value = true; void flushSave();
  }, { deep: true, flush: 'post' });
  watch([loading, blocked, analyzing, assessment, analysis], () => {
    if (!assessment.value) { lastAnalysis = ''; return; }
    if (!analysis.value && lastAnalysis !== assessment.value.submission_id) void runAnalysis();
  }, { flush: 'post' });
  function beforeUnload(event: BeforeUnloadEvent) {
    if (busy.value) { event.preventDefault(); event.returnValue = ''; }
  }
  onMounted(() => { void restore(); window.addEventListener('beforeunload', beforeUnload); });
  onBeforeUnmount(() => { disposed = true; window.removeEventListener('beforeunload', beforeUnload); });
  return {
    state, choices, results, profile, topicCompletion, analysis, assessment,
    loading, loadError, saving, grading, dirty, saveFailed, conflict, saveMessage,
    analyzing, analysisError, blocked, busy, restoredKey,
    restore, flushSave, submitQuiz, updateDraft, resetAssessment, runAnalysis,
  };
}
