<script setup lang="ts">
import type { LearnerProfile } from '../../shared/api/learning';
defineProps<{ profile: LearnerProfile }>();
function status(value: string) {
  return ({ unmeasured: '尚未测评', insufficient: '证据不足', emerging: '初步证据', stable: '证据较多' } as Record<string, string>)[value] ?? value;
}
</script>
<template>
  <section class="learner-profile">
    <h2>学习能力画像</h2><p>{{ profile.scope }}</p><p>已记录 {{ profile.submission_count }} 次提交，覆盖 {{ profile.evidence_count }} 道不同题目；重复练习 {{ profile.repeat_count }} 次。</p>
    <p class="scope-note">画像汇总全部已记录方向与前测证据。下表显示首次作答正确率；未测评的能力保持空白。</p>
    <div class="profile-table-wrap"><table class="profile-table"><caption>语言能力 × 认知目标 · 首次作答证据</caption><thead><tr><th scope="col">能力维度</th><th v-for="cell in profile.matrix[0]?.cells" :key="cell.bloom" scope="col">{{ cell.name }}</th></tr></thead><tbody><tr v-for="dimension in profile.matrix" :key="dimension.dimension"><th scope="row">{{ dimension.name }}</th><td v-for="cell in dimension.cells" :key="cell.bloom"><strong>{{ cell.score === null ? '—' : cell.score + '%' }}</strong><small>{{ status(cell.evidence_status) }} · {{ cell.evidence_count }} 题</small></td></tr></tbody></table></div>
    <div class="report-grid"><article class="report-card"><h3>知识点作答记录</h3><p v-if="!profile.knowledge_points.length">完成测验后，这里会显示知识点证据。</p><div v-for="point in profile.knowledge_points" :key="point.name" class="report-dimension"><strong>{{ point.name }}</strong><p>首次作答 {{ point.score }}% · 最近练习 {{ point.latest_score }}% · {{ point.evidence_count }} 道不同题目</p></div></article><article class="report-card"><h3>下一步练习</h3><ul><li v-for="step in profile.next_steps" :key="step">{{ step }}</li></ul></article></div>
  </section>
</template>
<style scoped>
.profile-table-wrap { overflow-x: auto; margin: 24px 0; }
.profile-table { border-collapse: collapse; width: 100%; min-width: 680px; text-align: left; }
.profile-table caption { text-align: left; padding: 12px 0; }
.profile-table th, .profile-table td { padding: 12px; border-bottom: 1px solid #e5e7eb; }
.profile-table small { display: block; font-size: 11px; margin-top: 6px; color: #666; white-space: nowrap; }
</style>
