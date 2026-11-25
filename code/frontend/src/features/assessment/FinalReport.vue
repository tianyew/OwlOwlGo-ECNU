<script setup lang="ts">
import type { LearnerProfile as Profile, QuizResult } from '../../shared/api/learning';
import LearnerProfile from './LearnerProfile.vue';
defineProps<{ topic: string; result: QuizResult; assessment?: QuizResult; completed: number; topicComplete: boolean; profile: Profile; canRetry?: boolean }>();
const emit = defineEmits<{ plan: []; retry: []; review: [] }>();
</script>
<template>
  <section class="final-report">
    <h1>{{ topic }} · 学习回顾</h1>
    <div class="report-hero"><div><span class="home-kicker">本次方向后测</span><strong class="report-score">{{ result.score }}<small> / 100</small></strong><p>答对 {{ result.correct }} / {{ result.total }} 题 · 当前累计完成 {{ completed }} / 5 个单元</p></div><div><h2>{{ topicComplete ? '本方向已完成' : '继续巩固本方向' }}</h2><p>方向完成条件：5 个单元均通过，且方向后测曾达到 60 分。</p><p v-if="assessment">本轮拼音与声调前测：{{ assessment.score }} / 100。前后测内容不同，分数分别展示。</p></div></div>
    <p v-if="result.created_at">本次提交时间：{{ new Date(result.created_at).toLocaleString() }}</p>
    <h2>当前累计学习画像</h2>
    <LearnerProfile :profile="profile" @review="emit('review')" @continue="emit('plan')" />
    <div class="question-actions"><button class="secondary" @click="emit('review')">去复习</button><button class="secondary" @click="emit('plan')">回到学习规划</button><button v-if="canRetry" class="primary" @click="emit('retry')">重新进行后测 →</button></div>
    <p v-if="!canRetry">如需重做这个方向的后测，请先在学习规划中选择该方向。</p>
  </section>
</template>
