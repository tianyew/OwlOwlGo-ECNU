<script setup lang="ts">
import PhoneticsDemo from './features/phonetics/PhoneticsDemo.vue';
</script>

<template>
  <div class="shell">
    <header class="site-header"><a class="brand" href="./"><span class="logo">汉</span><span>OwlOwlGo <small>中文之旅</small></span></a><span class="header-note">语言 × 文化 · Learn Chinese</span></header>
    <main><PhoneticsDemo /></main>
    <section class="planned-modules" aria-label="后续模块"><span>后续探索</span><span>汉字学习 <small>规划中</small></span><span>情境汉语 <small>规划中</small></span><span>文化探索 <small>规划中</small></span><span>复习与进度 <small>规划中</small></span></section>
    <footer>OwlOwlGo · 中文之旅 <span>拼音与声调交互演示 · 无需登录 · 本次作答不持久保存</span></footer>
  </div>
</template>
