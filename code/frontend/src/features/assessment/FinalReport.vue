<script setup lang="ts">
import type { LearnerProfile as Profile, QuizResult } from '../../shared/api/learning';
import LearnerProfile from './LearnerProfile.vue';
defineProps<{ topic: string; result: QuizResult; assessment?: QuizResult; completed: number; topicComplete: boolean; profile: Profile }>();
const emit = defineEmits<{ plan: []; retry: [] }>();
</script>
<template>
  <section class="final-report">
    <p class="eyebrow">LEARNING REVIEW / 阶段学习报告</p><h1>{{ topic }} · 学习回顾</h1>
    <div class="report-hero"><div><span class="home-kicker">本次方向后测</span><strong class="report-score">{{ result.score }}<small> / 100</small></strong><p>答对 {{ result.correct }} / {{ result.total }} 题 · 已完成 {{ completed }} / 5 个单元</p></div><div><h2>{{ topicComplete ? '本方向已完成' : '继续巩固本方向' }}</h2><p>方向完成条件：5 个单元均通过，且方向后测曾达到 60 分。</p><p v-if="assessment">本轮拼音与声调前测：{{ assessment.score }} / 100。前后测内容不同，分数分别展示。</p></div></div>
    <LearnerProfile :profile="profile" />
    <div class="question-actions"><button class="secondary" @click="emit('plan')">回到学习规划</button><button class="primary" @click="emit('retry')">重新进行后测 →</button></div>
  </section>
</template>
