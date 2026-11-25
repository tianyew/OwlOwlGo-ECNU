<script setup lang="ts">
import { ref } from 'vue';
const learningBusy = ref(false);
import AccountGate from './features/auth/AccountGate.vue';
import LearningJourney from './features/assessment/LearningJourney.vue';
</script>

<template>
  <div class="shell">
    <a class="skip-link" href="#main-content">跳到主要内容</a>
    <header class="site-header"><a class="brand" href="./" aria-label="OwlOwlGo 首页"><span class="logo">汉</span><span>OwlOwlGo</span></a></header>
    <main id="main-content" tabindex="-1"><AccountGate v-slot="{ user }" :learning-busy="learningBusy"><LearningJourney :key="user?.id ?? 'guest'" :user-id="user?.id" :display-name="user?.display_name" @saving-change="learningBusy = $event" /></AccountGate></main>
  </div>
</template>
