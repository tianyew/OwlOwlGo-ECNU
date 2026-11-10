<script setup lang="ts">
import type { Analysis, QuizResult } from '../../shared/api/learning';
const props = defineProps<{ analysis: Analysis | null; assessment?: QuizResult; analyzing: boolean; error: string; signedIn: boolean; waiting: boolean }>();
defineEmits<{ retry: [] }>();
function question(id: string) { return props.assessment?.items.find(item => item.question_id === id); }
</script>
<template>
  <section id="learning-analysis" class="analysis-panel" aria-label="个性化学习建议" :aria-busy="analyzing">
    <h2>从这次作答，找到下一步。</h2>
    <p v-if="!signedIn">登录后，系统会分析作答并保留建议。</p>
    <p v-else-if="analyzing" role="status">正在结合你的作答逐题分析…你可以继续选择学习方向。</p>
    <p v-else-if="waiting" role="status">保存作答后将自动更新学习建议。</p>
    <div v-if="error" role="alert"><p>{{ error }}</p><button class="secondary" :disabled="analyzing || waiting" @click="$emit('retry')">重试分析</button></div>
    <article v-if="analysis" class="analysis-result">
      <p>{{ analysis.summary }}</p>
      <template v-if="analysis.strengths.length"><h3>这次做得好的地方</h3><ul><li v-for="item in analysis.strengths" :key="item">{{ item }}</li></ul></template>
      <template v-if="analysis.focus_areas.length"><h3>优先巩固</h3><ul><li v-for="item in analysis.focus_areas" :key="item">{{ item }}</li></ul></template>
      <template v-if="analysis.question_feedback.length"><h3>从错题找到线索</h3><div v-for="item in analysis.question_feedback" :key="item.question_id" class="feedback-card"><h4>{{ question(item.question_id)?.prompt }}</h4><p class="muted">你的选择：{{ question(item.question_id)?.options[question(item.question_id)!.selected_index] }} · 正确答案：{{ question(item.question_id)?.options[question(item.question_id)!.correct_index] }}</p><p>{{ item.observation }}</p><p>{{ item.suggestion }}</p></div></template>
      <h3>接下来可以这样练</h3><ol class="practice-list"><li v-for="task in analysis.practice_tasks" :key="task.title"><h4>{{ task.title }}</h4><p class="muted">{{ task.reason }}</p><p>{{ task.activity }}</p><p><strong>自查：</strong>{{ task.success_criterion }}</p></li></ol>
      <h3>学习安排建议</h3><ul><li v-for="item in analysis.next_steps" :key="item">{{ item }}</li></ul>
    </article>
  </section>
</template>
<style scoped>
.feedback-card, .practice-list li { padding: 20px; margin: 12px 0; border-radius: 16px; background: #f5f5f7; }
h4 { margin: 0 0 10px; font-size: 16px; }
p { line-height: 1.7; }
</style>
