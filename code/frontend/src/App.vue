<script setup lang="ts">
import { ref } from 'vue';
const learningBusy = ref(false);
import AccountGate from './features/auth/AccountGate.vue';
import LearningJourney from './features/assessment/LearningJourney.vue';
</script>

<template>
  <div class="shell">
    <header class="site-header"><a class="brand" href="./"><span class="logo">汉</span><span>OwlOwlGo <small>LEARN CHINESE</small></span></a><span class="header-note"><b>中文之旅</b><span>Learn at your own pace.</span></span></header>
    <main><AccountGate v-slot="{ user }" :learning-busy="learningBusy"><LearningJourney :key="user?.id ?? 'guest'" :user-id="user?.id" :display-name="user?.display_name" @saving-change="learningBusy = $event" /></AccountGate></main>
    <footer>OwlOwlGo · 中文之旅</footer>
  </div>
</template>
