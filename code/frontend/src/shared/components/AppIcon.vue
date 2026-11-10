<script setup lang="ts">
defineProps<{ name: string }>();
const paths: Record<string, string> = {
  home: 'm3 10 9-7 9 7v10a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1Z',
  book: 'M12 5C9 3 5 3 2 4v15c3-1 7-1 10 1 3-2 7-2 10-1V4c-3-1-7-1-10 1Zm0 0v15',
  compass: 'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM16 8l-3 5-5 3 3-5Z',
  chart: 'M4 3v17h17M8 15v-4m5 4V7m5 8v-5',
  check: 'm5 12 4 4L19 6',
  play: 'm9 5 11 7-11 7Z',
  arrow: 'M4 12h16m-6-6 6 6-6 6',
  restart: 'M3 10a9 9 0 1 1 2 8M3 4v6h6',
  chevron: 'm8 10 4 4 4-4',
  bulb: 'M9 18h6m-5 3h4M8 14a6 6 0 1 1 8 0c-1 1-1 2-1 2H9s0-1-1-2Z',
  leaf: 'M20 4C9 2 3 7 5 14s15 7 15-10ZM5 20l10-11',
  shield: 'M12 3 3 7v5c0 5 9 9 9 9s9-4 9-9V7Zm-4 9 3 3 5-6',
  travel: 'm3 11 18-8-8 18-2-8Z',
  daily: 'M4 9h13v7a4 4 0 0 1-4 4H8a4 4 0 0 1-4-4Zm13 1h2a3 3 0 0 1 0 6h-2M7 3v3m5-3v3',
  campus: 'm2 9 10-6 10 6-10 6Zm4 3v6c4 3 8 3 12 0v-6m4-3v8',
  poetry: 'M6 3h12v18l-6-3-6 3ZM9 7h6m-6 4h6',
};
</script>

<template>
  <svg class="app-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path :d="paths[name] ?? paths.book" /></svg>
</template>
