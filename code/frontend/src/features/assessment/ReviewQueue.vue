<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { learningApi, type ReviewItem } from '../../shared/api/learning';

defineProps<{ courseAvailable: (item: ReviewItem) => boolean }>();
const emit = defineEmits<{ back: []; course: [ReviewItem]; assessment: [] }>();
const items = ref<ReviewItem[]>([]);
const selected = ref<ReviewItem>();
const loading = ref(true);
const error = ref('');
async function load() {
  loading.value = true;
  error.value = '';
  try {
    items.value = (await learningApi.review()).items;
    selected.value = items.value[0];
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : '错题加载失败。';
  } finally {
    loading.value = false;
  }
}
onMounted(load);
</script>

<template>
  <section class="journey-panel">
    <button class="text-button" @click="emit('back')">← 返回学习记录</button>
    <h1>错题复习</h1>
    <p>最多展示 10 道最近一次正式作答仍答错的题。</p>
    <p v-if="loading" role="status">正在加载错题…</p>
    <div v-else-if="error" role="alert">{{ error }} <button class="secondary" @click="load">重试</button></div>
    <p v-else-if="!items.length">目前没有符合规则的待复习错题。</p>
    <template v-else>
      <ul>
        <li v-for="item in items" :key="item.source_question_id">
          <button class="text-button" :aria-pressed="selected === item" @click="selected = item">
            {{ item.prompt }} · {{ item.category }}
          </button>
          <time v-if="item.last_submitted_at" :datetime="item.last_submitted_at">{{ new Date(item.last_submitted_at).toLocaleString() }}</time>
        </li>
      </ul>
      <article v-if="selected" class="report-card">
        <h2>{{ selected.prompt }}</h2>
        <p>你的答案：{{ selected.options[selected.selected_index] }}</p>
        <p>正确答案：{{ selected.options[selected.correct_index] }}</p>
        <p>{{ selected.explanation }}</p>
        <p>{{ selected.reason }}</p>
        <button v-if="courseAvailable(selected)" class="secondary" @click="emit('course', selected)">查看原课程</button>
        <button v-else-if="selected.quiz_id === 'assessment'" class="secondary" @click="emit('assessment')">查看前测报告</button>
        <p v-else>暂无可查看的原课程。</p>
      </article>
    </template>
  </section>
</template>
