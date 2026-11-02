<script setup lang="ts">
import { computed } from 'vue';
import type { Diagnosis, Topic } from '../../shared/api/demo';
const props = defineProps<{
  displayName?: string; setupComplete: boolean; assessmentDone: boolean;
  answersCount: number; plan?: Topic; completed: number[]; diagnosis?: Diagnosis;
}>();
const emit = defineEmits<{
  posttest: []; setup: []; learn: [index: number]; plan: []; analysis: []; direction: [];
}>();
const nextUnit = computed(() => props.plan?.units.findIndex((_, i) => !props.completed.includes(i)) ?? -1);
const percent = computed(() => props.plan ? Math.round(props.completed.length / props.plan.units.length * 100) : 0);
const setupCount = computed(() => Number(props.assessmentDone) + Number(Boolean(props.plan)));
</script>

<template>
  <section class="home-dashboard" aria-label="学习首页">
    <div class="home-heading"><div><p class="eyebrow">YOUR SPACE TO GROW</p><h1>{{ displayName ? `${displayName}，你好。` : '欢迎来到中文之旅。' }}</h1><p>一点一滴，让中文成为日常。</p></div><span class="home-label">HOME / 学习首页</span></div>
    <template v-if="!setupComplete">
      <article class="home-welcome">
        <div><span class="home-kicker">第一步 · 完成学习设置</span><h2>先了解你，<br><span>再开始适合你的学习。</span></h2><p>完成一个简短前测，选择感兴趣的方向，<br>查看你的第一份学习计划。</p><button class="primary" @click="emit('setup')">{{ answersCount || assessmentDone ? '继续完成学习设置' : '开始学习设置' }} <span>↗</span></button><small>{{ assessmentDone ? '前测已完成，接下来确认方向与规划。' : answersCount ? `前测已提交 ${answersCount} / 8 题，可从上次继续。` : '8 道入门题 · 按自己的节奏完成' }}</small></div>
        <div class="setup-checklist"><div class="setup-checklist-heading"><strong>你的开始，只需三步</strong><span>{{ setupCount }} / 3</span></div><ol><li :class="{ done: assessmentDone }"><span>{{ assessmentDone ? '✓' : '01' }}</span><div><strong>了解学习起点</strong><p>完成前测，查看诊断与建议</p></div></li><li :class="{ done: Boolean(plan) }"><span>{{ plan ? '✓' : '02' }}</span><div><strong>选择兴趣方向</strong><p>{{ plan ? plan.title : '旅游、生活、校园或古诗' }}</p></div></li><li><span>03</span><div><strong>确认学习规划</strong><p>查看单元目标，完成首次设置</p></div></li></ol></div>
      </article>
      <div class="home-note"><span>为你的兴趣而学。</span><p>主题帮助你组织语言学习内容。首次设置完成后，这里将成为你的学习进度与继续学习入口。</p></div>
    </template>
    <template v-else-if="plan">
      <article class="home-continue"><div><span class="home-kicker">{{ nextUnit < 0 ? '这一程，已完成' : '接着上次，继续向前' }} · {{ plan.title }}</span><h2>{{ nextUnit < 0 ? '每一次练习，都算数。' : plan.units[nextUnit].title }}</h2><p>{{ nextUnit < 0 ? '本方向的单元已全部标记完成。重温所学，或探索新的兴趣方向。' : plan.units[nextUnit].goal }}</p><div class="home-actions"><button class="primary" @click="nextUnit < 0 ? emit('plan') : emit('learn', nextUnit)">{{ nextUnit < 0 ? '回顾学习内容' : '继续学习' }} <span>↗</span></button><button class="secondary" @click="emit('plan')">查看学习规划</button></div></div><div class="home-progress"><div class="home-progress-ring" :style="{ '--progress': `${percent}%` }"><span><strong>{{ percent }}<small>%</small></strong><small>当前方向进度</small></span></div><p>{{ completed.length }} / {{ plan.units.length }} 个单元已完成</p></div></article>
      <div class="home-cards">
        <article><p class="eyebrow">YOUR STARTING POINT</p><h3>学习起点</h3><p class="home-score">{{ diagnosis?.score ?? '—' }}<span> / 100</span></p><p>{{ diagnosis?.advice }}</p><small>拼音与声调文字辨识</small><button class="text-button" @click="emit('analysis')">查看前测报告 ↗</button></article>
        <article><p class="eyebrow">YOUR INTEREST</p><h3>{{ plan.title }}</h3><p>{{ plan.description }}</p><div class="home-card-bottom"><span>{{ plan.units.length }} 个学习单元</span><button class="text-button" @click="emit('direction')">修改方向 ↗</button></div></article>
      </div>
      <article class="posttest-entry"><div><p class="eyebrow">AFTER YOUR LEARNING</p><h2>后测与诊断报告</h2><p>完成方向学习后，检查词句理解和情境应用，规划下一步练习。</p></div><button class="primary" @click="emit('posttest')">进入后测 →</button></article><section class="home-units"><div class="home-section-title"><h2>我的学习单元</h2><span>{{ plan.title }}</span></div><button v-for="(unit,index) in plan.units" :key="index" class="home-unit" @click="emit('learn', index)"><span class="home-unit-number" :class="{ done: completed.includes(index) }">{{ completed.includes(index) ? '✓' : String(index + 1).padStart(2, '0') }}</span><span><strong>{{ unit.title }}</strong><small>{{ unit.goal }}</small></span><span class="home-unit-action">{{ completed.includes(index) ? '复习' : index === nextUnit ? '继续' : '查看' }} ↗</span></button></section>
    </template>
  </section>
</template>
