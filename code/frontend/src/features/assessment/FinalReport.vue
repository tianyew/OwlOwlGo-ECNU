<script setup lang="ts">
defineProps<{ topic: string; score: number; correct: number; total: number; completed: number }>();
const emit = defineEmits<{ plan: []; retry: [] }>();
const dimensions = [{ name: '词句理解', value: 85, note: '建立词语、句型与具体情境的联系' }, { name: '情境表达', value: 80, note: '从选择合适表达，过渡到主动组织语言' }, { name: '综合应用', value: 70, note: '在连续对话中补充时间、地点和原因' }];
</script>
<template>
  <section class="final-report">
    <p class="eyebrow">LEARNING REVIEW / 阶段诊断报告</p><h1>让学过的中文，成为能用的中文。</h1><p class="report-subtitle">{{ topic }} · 本阶段学习回顾</p>
    <div class="report-hero"><div><span class="home-kicker">本次后测 · 实际作答结果</span><strong class="report-score">{{ score }}<small> / 100</small></strong><p>答对 {{ correct }} / {{ total }} 题 · 已完成 {{ completed }} 个学习单元</p></div><div><h2>下一步，从“理解”走向“表达”。</h2><p>用熟悉的词句描述自己的生活，再把表达带到新的情境中。</p><span class="demo-tag">以下能力画像与建议为固定示例</span></div></div>
    <p class="scope-note">上方分数依据本次后测作答计算。下方画像和建议展示预设报告样式，暂未根据分数生成；本次选择题不评估实际口语、听力或正式汉语等级。</p>
    <div class="report-grid"><article class="report-card"><h2>学习能力画像</h2><p class="muted">固定示例 · 用于展示未来报告形式</p><div v-for="item in dimensions" :key="item.name" class="report-dimension"><div><strong>{{ item.name }}</strong><span>{{ item.value }} / 100</span></div><div class="dimension-track"><i :style="{ width: item.value + '%' }"></i></div><p>{{ item.note }}</p></div></article><article class="report-card"><p class="eyebrow">YOUR NEXT STEP</p><h2>把一句话，说得更完整。</h2><p>在熟悉句型中逐步加入对象、时间、地点或原因，练习两到三轮交流。</p><h3>建议继续保持</h3><ul><li>用情境对话记词，而不是只看单词表。</li><li>完成单元后回顾错题，并用自己的信息改写例句。</li></ul><h3>建议重点练习</h3><ul><li>区分表达相近、使用场景不同的句子。</li><li>把单句扩展为“说明情况—提出请求—确认信息”。</li></ul></article></div>
    <article class="report-card"><p class="eyebrow">A LITTLE PRACTICE, EVERY DAY</p><h2>接下来一周，试试这样练。</h2><ol class="report-week"><li><strong>第 1–2 天 · 找回关键词</strong><p>每天 10 分钟，复习两个单元；遮住拼音认读词语，重做错题。</p></li><li><strong>第 3–4 天 · 替换成自己的话</strong><p>每天选择一个句型，替换人物、地点和时间，写出三句新表达。</p></li><li><strong>第 5–6 天 · 完成两轮对话</strong><p>扮演对话双方，加入一个新问题，再练习礼貌回应与信息确认。</p></li><li><strong>第 7 天 · 回顾与再尝试</strong><p>回看单元任务，完成一次无提示表达，再做后测检查词句理解。</p></li></ol></article>
    <div class="question-actions"><button class="secondary" @click="emit('plan')">回到学习规划</button><button class="primary" @click="emit('retry')">重新进行后测 →</button></div>
  </section>
</template>
