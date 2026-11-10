<script setup lang="ts">
import { computed } from 'vue';
import type { Diagnosis, Topic } from '../../shared/api/demo';
import AppIcon from '../../shared/components/AppIcon.vue';
const props = defineProps<{
  displayName?: string; setupComplete: boolean; assessmentDone: boolean;
  answersCount: number; plan?: Topic; completed: number[]; diagnosis?: Diagnosis; topics: Topic[];
}>();
const emit = defineEmits<{
  posttest: []; setup: []; learn: [index: number]; plan: []; analysis: []; profile: []; direction: [];
}>();
const nextUnit = computed(() => props.plan?.units.findIndex((_, i) => !props.completed.includes(i)) ?? -1);
const percent = computed(() => props.plan ? Math.round(props.completed.length / props.plan.units.length * 100) : 0);
const setupCount = computed(() => Number(props.assessmentDone) + Number(Boolean(props.plan)));
</script>

<template>
  <section class="home-dashboard" aria-label="学习首页">
    <div class="home-heading">
      <div><h1>{{ displayName ? `${displayName}，今天也一起进步。` : '你好，欢迎来到中文之旅。' }}</h1></div>
    </div>
    <template v-if="!setupComplete">
      <article class="home-welcome">
        <div class="hero-copy"><span class="home-kicker">第一步 · 完成学习设置</span><h2>你的中文之旅，<br>从<span>了解自己</span>开始。</h2><p>完成前测，选择喜欢的方向，开始学习。</p><button class="primary" @click="emit('setup')">{{ answersCount || assessmentDone ? '继续完成学习设置' : '开始学习设置' }} <AppIcon name="arrow" /></button><p class="hero-meta">{{ assessmentDone ? '前测已完成' : answersCount ? `前测已作答 ${answersCount} / 8 题，可从上次继续。` : '8 道题 · 约 3 分钟' }}</p></div>
        <div class="home-letter-art" aria-hidden="true"><span class="art-orbit"></span><div class="hanzi-card"><small>nǐ hǎo</small><strong>你好</strong></div></div>
      </article>
      <div class="setup-strip"><div class="setup-strip-label"><strong>只需三步，找到你的方向</strong><span class="count-badge">{{ setupCount }} / 3</span></div><ol><li :class="{ done: assessmentDone }"><span>{{ assessmentDone ? '✓' : '01' }}</span><div><strong>了解学习起点</strong></div></li><li :class="{ done: Boolean(plan) }"><span>{{ plan ? '✓' : '02' }}</span><div><strong>选择兴趣方向</strong></div></li><li><span>03</span><div><strong>开启学习计划</strong></div></li></ol></div>
      <section class="discover-section"><div class="home-section-title"><div><h2>中文，连接你喜欢的世界</h2></div></div><div class="discover-grid"><article v-for="topic in topics" :key="topic.id" :data-topic="topic.id" class="discover-card"><span class="topic-symbol"><AppIcon :name="topic.id" /></span><h3>{{ topic.title }}</h3><p>{{ topic.description }}</p></article></div></section>
    </template>
    <template v-else-if="plan">
      <article class="home-continue"><div><span class="home-kicker">{{ plan.title }}</span><h2>{{ nextUnit < 0 ? '每一次练习，都算数。' : plan.units[nextUnit].title }}</h2><p>{{ nextUnit < 0 ? '你已通过本方向的所有单元。接下来完成后测，或重温已学内容。' : plan.units[nextUnit].goal }}</p><div class="home-actions"><button class="primary" @click="nextUnit < 0 ? emit('posttest') : emit('learn', nextUnit)">{{ nextUnit < 0 ? '进入后测' : '继续学习' }} <AppIcon name="arrow" /></button><button class="secondary" @click="emit('plan')">查看学习规划</button></div></div><div class="home-progress"><div class="home-progress-ring" :style="{ '--progress': `${percent}%` }"><span><strong>{{ percent }}<small>%</small></strong><small>单元进度</small></span></div><p>{{ completed.length }} / {{ plan.units.length }} 个单元已完成</p></div></article>
      <div class="home-learning-layout">
        <section class="home-units" aria-labelledby="unit-path-title">
          <div class="home-section-title"><h2 id="unit-path-title">我的学习单元</h2><span class="count-badge">{{ completed.length }} / {{ plan.units.length }}</span></div>
          <ol class="learning-path">
            <li v-for="(unit, index) in plan.units" :key="unit.id" :class="{ 'path-completed': completed.includes(index), 'path-current': index === nextUnit }">
              <button class="home-unit" :class="{ 'is-next': index === nextUnit }" :aria-current="index === nextUnit ? 'step' : undefined" @click="emit('learn', index)">
                <span class="path-node" aria-hidden="true"><AppIcon :name="completed.includes(index) ? 'check' : index === nextUnit ? 'play' : 'book'" /></span>
                <span class="path-copy"><strong>{{ unit.title }}</strong><small>{{ unit.goal }}</small><span class="path-action">{{ completed.includes(index) ? '已完成 · 复习' : index === nextUnit ? '接着学' : '查看单元' }} <AppIcon name="arrow" /></span></span>
              </button>
            </li>
          </ol>
        </section>
        <aside class="home-cards" aria-label="学习概览">
          <article><span class="overview-icon"><AppIcon name="check" /></span><h3>拼音与声调前测</h3><p class="home-score">{{ diagnosis?.score ?? '—' }}<span> / 100</span></p><button class="text-button" @click="emit('analysis')">查看前测报告 <AppIcon name="arrow" /></button></article>
          <article><span class="overview-icon"><AppIcon :name="plan.id" /></span><h3>{{ plan.title }}</h3><p>{{ plan.description }}</p><div class="home-card-bottom"><button class="text-button" @click="emit('direction')">修改方向 <AppIcon name="arrow" /></button></div></article>
          <article class="profile-shortcut"><span class="overview-icon"><AppIcon name="chart" /></span><h3>看见每一步成长</h3><p>从真实作答中，了解下一步方向。</p><button class="text-button" @click="emit('profile')">查看学习画像 <AppIcon name="arrow" /></button></article>
        </aside>
      </div>
      <article class="posttest-entry"><div><h2>学过之后，再认识自己一次。</h2><p>完成方向后测，查看成绩与真实作答证据。</p></div><button class="primary" @click="emit('posttest')">进入后测 <AppIcon name="arrow" /></button></article>
    </template>
  </section>
</template>
