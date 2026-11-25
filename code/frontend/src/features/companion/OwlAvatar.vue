<script setup lang="ts">
withDefaults(defineProps<{ waving?: boolean }>(), { waving: false });
</script>

<template>
  <svg class="owl-avatar" :class="{ 'owl-waving': waving }" viewBox="0 0 100 100" fill="none" aria-hidden="true">
    <ellipse cx="50" cy="90" rx="27" ry="5" fill="#b9d9f6" opacity=".5" />
    <path d="m23 35-3-19 20 10M60 26l20-10-3 21" fill="#2789eb" stroke="#0868cb" stroke-width="3" stroke-linejoin="round" />
    <path d="M21 44c0-20 58-20 58 0v24c0 17-13 24-29 24S21 85 21 68Z" fill="#2789eb" stroke="#0868cb" stroke-width="3" />
    <ellipse cx="50" cy="68" rx="21" ry="20" fill="#dceeff" />
    <path d="M22 49c-6 4-9 13-6 23 4-1 9-7 11-13" fill="#1173d8" stroke="#0868cb" stroke-width="3" stroke-linecap="round" />
    <path class="owl-wing" d="M78 50c8-4 13-13 13-21-9 1-17 8-19 15" fill="#2789eb" stroke="#0868cb" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" />
    <path d="M50 34c-8-14-30-6-28 10 1 14 17 20 28 12 11 8 27 2 28-12 2-16-20-24-28-10Z" fill="white" />
    <g class="owl-eyes"><ellipse cx="36" cy="43" rx="6" ry="8" fill="#233b59" /><ellipse cx="64" cy="43" rx="6" ry="8" fill="#233b59" /><circle cx="38" cy="40" r="2" fill="white" /><circle cx="66" cy="40" r="2" fill="white" /></g>
    <path d="m45 52 5 7 5-7" fill="#ffbd59" stroke="#e8a23a" stroke-width="2" stroke-linejoin="round" />
    <ellipse cx="29" cy="54" rx="5" ry="3" fill="#ffd9ce" /><ellipse cx="71" cy="54" rx="5" ry="3" fill="#ffd9ce" />
    <path d="m36 88-3 5m10-5-1 5m15-5 1 5m6-5 3 5" stroke="#e8a23a" stroke-width="4" stroke-linecap="round" />
    <path d="m44 69 6 4 6-4m-12 9 6 4 6-4" stroke="#a6ccef" stroke-width="2" stroke-linecap="round" />
  </svg>
</template>

<style scoped>
.owl-avatar { display: block; width: 100%; height: 100%; overflow: visible; }
.owl-waving .owl-wing { transform-origin: 76px 49px; animation: owl-wave 4.8s ease-in-out infinite; }
.owl-waving .owl-eyes { transform-origin: 50px 43px; animation: owl-blink 6s ease-in-out infinite; }
@keyframes owl-wave { 0%, 70%, 100% { transform: rotate(0deg); } 78% { transform: rotate(12deg); } 86% { transform: rotate(-5deg); } 92% { transform: rotate(8deg); } }
@keyframes owl-blink { 0%, 46%, 50%, 100% { transform: scaleY(1); } 48% { transform: scaleY(.12); } }
@media (prefers-reduced-motion: reduce) { .owl-waving .owl-wing, .owl-waving .owl-eyes { animation: none; } }
</style>
