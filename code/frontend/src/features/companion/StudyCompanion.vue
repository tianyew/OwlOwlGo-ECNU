<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue';
import AppIcon from '../../shared/components/AppIcon.vue';
import OwlAvatar from './OwlAvatar.vue';
import { companionActions, companionGreeting, companionReply, type CompanionContext, type CompanionIntent } from './demo';

const props = defineProps<{ context: CompanionContext }>();
const open = ref(false);
const input = ref('');
const launcher = ref<HTMLButtonElement>();
const editor = ref<HTMLTextAreaElement>();
const transcript = ref<HTMLElement>();
const messages = ref<{ id: number; role: 'user' | 'assistant'; text: string }[]>([]);
const actions = computed(() => companionActions(props.context));
const greeting = computed(() => companionGreeting(props.context));
let nextId = 0;
let hintStep = 0;

async function toggle() {
  if (open.value) return close();
  open.value = true;
  await nextTick(); editor.value?.focus();
}
async function close() {
  open.value = false;
  await nextTick(); launcher.value?.focus();
}
async function clear() {
  messages.value = []; input.value = ''; hintStep = 0;
  await nextTick(); editor.value?.focus();
}
async function send(text = input.value, intent?: CompanionIntent) {
  const question = text.trim().slice(0, 300);
  if (!question) return;
  if (intent === 'hint' || (!intent && /提示|答案|选哪|怎么选/.test(question))) hintStep++;
  const reply = companionReply(question, props.context, intent, hintStep);
  messages.value = [...messages.value,
    { id: nextId++, role: 'user' as const, text: question },
    { id: nextId++, role: 'assistant' as const, text: reply },
  ].slice(-24);
  input.value = '';
  await nextTick();
  if (transcript.value) transcript.value.scrollTop = transcript.value.scrollHeight;
  editor.value?.focus();
}
function keydown(event: KeyboardEvent) {
  if (event.key !== 'Enter' || event.shiftKey || event.isComposing || event.keyCode === 229) return;
  event.preventDefault(); void send();
}
watch(() => props.context.key, () => {
  // A new question/page gets a fresh demo conversation, never another learner's history.
  messages.value = []; input.value = ''; hintStep = 0;
});
</script>

<template>
  <Teleport to="body">
    <div class="study-companion">
      <section v-if="open" id="study-companion-panel" class="companion-panel" role="dialog" aria-modal="false" aria-labelledby="study-companion-title" @keydown.esc.stop.prevent="close">
        <header class="companion-header">
          <span class="companion-header-avatar"><OwlAvatar /></span>
          <div class="companion-heading"><h2 id="study-companion-title">小鸮 <span>AI 伴学</span></h2><p>一个问题，一小步。</p></div>
          <button type="button" class="companion-icon-button" aria-label="收起 AI 伴学" @click="close"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg></button>
        </header>
        <div class="companion-demo-note"><span class="companion-demo-dot" aria-hidden="true"></span><strong>交互示例</strong><span>预设回复，尚未连接真实 AI</span></div>
        <div class="companion-context" role="status"><AppIcon :name="context.scene === 'profile' ? 'chart' : 'book'" /><span>{{ context.label }}</span></div>
        <div ref="transcript" class="companion-transcript">
          <div class="companion-welcome"><div class="companion-welcome-owl"><OwlAvatar /></div><p>{{ greeting }}</p><span v-if="context.question" class="companion-question">当前题目：{{ context.question.prompt }}</span></div>
          <div class="companion-messages" role="log" aria-label="伴学示例对话" aria-live="polite" aria-relevant="additions" tabindex="0">
            <article v-for="message in messages" :key="message.id" class="companion-message" :class="'companion-message-' + message.role"><span class="companion-message-author">{{ message.role === 'user' ? '你' : '小鸮 · 示例回复' }}</span><p>{{ message.text }}</p></article>
          </div>
        </div>
        <div class="companion-bottom">
          <div class="companion-actions" aria-label="伴学快捷提问"><button v-for="action in actions" :key="action.intent" type="button" @click="send(action.label, action.intent)"><AppIcon :name="action.intent === 'hint' ? 'bulb' : action.intent === 'profile' ? 'chart' : 'book'" />{{ action.label }}</button></div>
          <form class="companion-composer" @submit.prevent="send()"><label class="sr-only" for="companion-question-input">向小鸮提问</label><textarea id="companion-question-input" ref="editor" v-model="input" maxlength="300" rows="2" placeholder="试着问：这节课怎么练？" @keydown="keydown"></textarea><button type="submit" class="companion-send" :disabled="!input.trim()" aria-label="发送提问"><AppIcon name="arrow" /></button></form>
          <div class="companion-footer"><span>对话仅保留在当前页面 · {{ input.length }}/300</span><button type="button" :disabled="!messages.length" @click="clear">清空对话</button></div>
        </div>
      </section>
      <button ref="launcher" type="button" class="companion-launcher" :class="{ 'companion-launcher-open': open }" :aria-label="open ? '收起 AI 伴学' : '打开 AI 伴学：小鸮'" :aria-expanded="open" aria-controls="study-companion-panel" @click="toggle"><span class="companion-launcher-owl"><OwlAvatar :waving="!open" /></span><span class="companion-launcher-label">AI 伴学</span></button>
    </div>
  </Teleport>
</template>

<style scoped>
.study-companion { --companion-blue: #0071e3; position: fixed; right: 24px; bottom: max(20px, env(safe-area-inset-bottom)); z-index: 60; color: #293544; font-family: inherit; }
.companion-launcher { display: flex; flex-direction: column; align-items: center; justify-content: center; position: relative; width: 80px; height: 90px; padding: 0; border: 0; background: transparent; color: #0057b3; filter: drop-shadow(0 5px 9px #154d8624); }
.companion-launcher:hover { transform: translateY(-3px); }
.companion-launcher-owl { display: block; width: 76px; height: 76px; }
.companion-launcher-label { position: relative; margin-top: -7px; padding: 4px 12px; border: 2px solid #b9d9f6; border-radius: 999px; background: white; font-size: 12px; font-weight: 750; white-space: nowrap; box-shadow: 0 2px 0 #d3e7fa; }
.companion-launcher-open .companion-launcher-label { color: white; background: var(--companion-blue); border-color: var(--companion-blue); }
.companion-panel { position: absolute; right: 0; bottom: 106px; display: flex; flex-direction: column; width: 390px; height: min(610px, calc(100dvh - 150px)); max-height: calc(100dvh - 150px); overflow: hidden; background: white; border: 2px solid #b9d9f6; border-radius: 24px; box-shadow: 0 12px 45px #254e792b, 0 4px 0 #d3e7fa; }
.companion-header { display: flex; align-items: center; gap: 10px; flex-shrink: 0; padding: 16px 18px 12px; background: #f4f9ff; }
.companion-header-avatar { width: 48px; height: 48px; flex-shrink: 0; }
.companion-heading { flex: 1; min-width: 0; }.companion-heading h2 { margin: 0; font-size: 19px; letter-spacing: 0; }.companion-heading h2 span { margin-left: 5px; color: #0071e3; font-size: 12px; font-weight: 650; }.companion-heading p { margin: 4px 0 0; color: #657386; font-size: 12px; }
.companion-icon-button { display: grid; place-items: center; width: 36px; height: 36px; padding: 8px; flex-shrink: 0; border: 1px solid #e1e6ec; border-radius: 11px; color: #657386; background: white; }.companion-icon-button svg { width: 18px; height: 18px; }.companion-icon-button:hover { color: #0071e3; background: #edf6ff; }
.companion-demo-note { display: flex; align-items: center; gap: 6px; padding: 9px 18px; flex-shrink: 0; background: #fff8e9; color: #82632a; font-size: 11px; line-height: 1.5; }.companion-demo-note strong { white-space: nowrap; font-weight: 650; }.companion-demo-dot { width: 6px; height: 6px; background: #d8aa4d; border-radius: 50%; flex-shrink: 0; }
.companion-context { display: flex; align-items: center; gap: 7px; flex-shrink: 0; padding: 11px 18px; border-bottom: 1px solid #edf0f4; color: #657386; font-size: 12px; line-height: 1.5; }.companion-context .app-icon { width: 15px; height: 15px; flex-shrink: 0; }.companion-context span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.companion-transcript { flex: 1; min-height: 0; padding: 18px; overflow-y: auto; overscroll-behavior: contain; scrollbar-width: thin; }
.companion-welcome { padding: 6px 2px 16px; text-align: center; }.companion-welcome-owl { width: 64px; height: 64px; margin: 0 auto 10px; }.companion-welcome p { margin: 0 auto; max-width: 280px; color: #4a5c70; font-size: 14px; line-height: 1.8; }.companion-question { display: block; margin-top: 12px; padding: 10px; border-radius: 12px; background: #f5f8fc; color: #657386; font-size: 12px; line-height: 1.7; text-align: left; }
.companion-messages { display: flex; flex-direction: column; gap: 15px; }.companion-messages:empty { display: none; }
.companion-message { max-width: 96%; }.companion-message-author { display: block; margin-bottom: 5px; color: #758496; font-size: 10px; }.companion-message p { margin: 0; padding: 12px 14px; border: 1px solid #e1e6ec; border-radius: 3px 15px 15px 15px; background: #f7f9fc; font-size: 13px; line-height: 1.8; white-space: pre-wrap; overflow-wrap: anywhere; }
.companion-message-user { align-self: flex-end; }.companion-message-user .companion-message-author { text-align: right; }.companion-message-user p { border-color: #d2e6fa; background: #edf6ff; color: #145997; border-radius: 15px 3px 15px 15px; }
.companion-bottom { padding: 12px 14px 10px; flex-shrink: 0; border-top: 1px solid #edf0f4; background: white; }
.companion-actions { display: flex; flex-wrap: wrap; gap: 7px; margin-bottom: 11px; }.companion-actions button { display: inline-flex; align-items: center; gap: 5px; padding: 7px 9px; border: 1px solid #cfe1f3; border-radius: 10px; color: #2568a8; background: #f4f9ff; font-size: 11px; font-weight: 600; line-height: 1.5; }.companion-actions button:hover { background: #e6f2ff; border-color: #98c4ec; }.companion-actions .app-icon { width: 13px; height: 13px; flex-shrink: 0; }
.companion-composer { display: flex; align-items: flex-end; gap: 8px; padding: 10px; border: 1.5px solid #dbe3ed; border-radius: 14px; background: #fafbfe; }.companion-composer:focus-within { border-color: #0071e3; box-shadow: 0 0 0 2px #0071e312; }
.companion-composer textarea { flex: 1; min-width: 0; max-height: 100px; padding: 2px; resize: vertical; border: 0; outline: 0; color: #293544; background: transparent; font: inherit; font-size: 13px; line-height: 1.6; }.companion-composer textarea::placeholder { color: #8795a6; }
.companion-send { display: grid; place-items: center; width: 34px; height: 34px; padding: 7px; flex-shrink: 0; border: 1px solid #0071e3; border-radius: 11px; color: white; background: #0071e3; }.companion-send .app-icon { width: 18px; height: 18px; transform: rotate(-90deg); }.companion-send:disabled { opacity: 1; border-color: #e1e6ec; color: #98a5b3; background: #e9eef4; }
.companion-footer { display: flex; align-items: center; justify-content: space-between; gap: 6px; margin-top: 8px; color: #8995a4; font-size: 10px; }.companion-footer button { min-height: 28px; padding: 3px 0 3px 6px; border: 0; color: #657386; background: transparent; font-size: 10px; }
.study-companion button:focus-visible, .companion-messages:focus-visible { outline: 3px solid #0071e3; outline-offset: 3px; }
@media (max-width: 600px) {
  .study-companion { right: 14px; bottom: max(14px, env(safe-area-inset-bottom)); }
  .companion-launcher { width: 66px; height: 80px; }.companion-launcher-owl { width: 66px; height: 66px; }.companion-launcher-label { font-size: 11px; padding: 4px 10px; }
  .companion-panel { position: fixed; left: 12px; right: 12px; bottom: calc(105px + env(safe-area-inset-bottom)); width: auto; height: min(590px, calc(100dvh - 130px - env(safe-area-inset-bottom))); max-height: calc(100dvh - 130px - env(safe-area-inset-bottom)); border-radius: 21px; }
  .companion-transcript { padding: 14px; }.companion-header { padding: 12px 14px 10px; }.companion-welcome-owl { width: 52px; height: 52px; }
  .companion-composer textarea { font-size: 16px; }
}
@media (max-height: 550px) { .companion-welcome-owl { display: none; }.companion-header-avatar { width: 36px; height: 36px; }.companion-context { padding-top: 6px; padding-bottom: 6px; }.companion-demo-note { padding-top: 5px; padding-bottom: 5px; } }
@media (prefers-reduced-motion: reduce) { .companion-launcher:hover { transform: none; }.study-companion button { transition: none; } }
</style>
