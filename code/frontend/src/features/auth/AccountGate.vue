<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { authApi, AuthError, type User } from '../../shared/api/auth';
defineProps<{ learningBusy?: boolean }>();
const user = ref<User | null>(null);
const loading = ref(true);
const busy = ref(false);
const showForm = ref(true);
const mode = ref<'login' | 'register'>('login');
const username = ref('');
const displayName = ref('');
const password = ref('');
const confirmation = ref('');
const error = ref('');
const journeyKey = ref(0);
function message(reason: unknown) { return reason instanceof Error ? reason.message : '操作失败，请重试。'; }
onMounted(async () => {
  try {
    user.value = await Promise.race([
      authApi.me(),
      new Promise<never>((_, reject) => window.setTimeout(
        () => reject(new AuthError('登录状态检查超时。请启动后端，或先以游客身份体验。', 0)),
        3000,
      )),
    ]);
    showForm.value = false;
  }
  catch (reason) { if (!(reason instanceof AuthError && reason.status === 401)) error.value = message(reason); }
  finally { loading.value = false; }
});
function switchMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login';
  password.value = ''; confirmation.value = ''; error.value = '';
}
async function submit() {
  if (busy.value) return;
  error.value = '';
  if (mode.value === 'register' && password.value !== confirmation.value) {
    error.value = '两次输入的密码不一致。'; return;
  }
  busy.value = true;
  try {
    const credentials = { username: username.value.trim(), password: password.value };
    user.value = mode.value === 'register'
      ? await authApi.register({ ...credentials, display_name: displayName.value.trim() })
      : await authApi.login(credentials);
    password.value = ''; confirmation.value = ''; showForm.value = false; journeyKey.value++;
  } catch (reason) { error.value = message(reason); }
  finally { busy.value = false; }
}
async function logout() {
  if (busy.value) return;
  busy.value = true; error.value = '';
  try {
    await authApi.logout(); user.value = null; showForm.value = true; mode.value = 'login';
    username.value = ''; displayName.value = ''; password.value = ''; confirmation.value = '';
    journeyKey.value++;
  } catch (reason) { error.value = message(reason); }
  finally { busy.value = false; }
}
function guest() { showForm.value = false; error.value = ''; password.value = ''; confirmation.value = ''; }
</script>

<template>
  <p v-if="loading" role="status" class="account-loading">正在检查登录状态…</p>
  <template v-else>
    <div class="account-bar">
      <span v-if="user">你好，<strong>{{ user.display_name }}</strong> <small>@{{ user.username }}</small></span>
      <span v-else>游客体验</span>
      <button v-if="user" class="secondary" :disabled="busy || learningBusy" @click="logout">{{ busy ? '正在退出…' : '退出登录' }}</button>
      <button v-else-if="!showForm" class="secondary" @click="showForm = true; error = ''">登录 / 注册</button>
    </div>
    <p v-if="error" class="account-error" role="alert">{{ error }}</p>
    <div v-if="showForm" class="account-layout">
      <aside class="account-story">

        <h2>让中文，<br><span>走进你的日常。</span></h2>
        <p>从一句问候，到一场对话。<br>找到适合你的起点，以自己的节奏向前。</p>
        <div class="story-art" aria-hidden="true"><span class="language-tile">你</span><span class="language-tile">nǐ</span></div>

      </aside>
      <section class="account-card">

      <h1>{{ mode === 'register' ? '创建你的学习账号' : '欢迎回来' }}</h1>
      <p>{{ mode === 'register' ? '注册后自动登录，开启你的中文之旅。' : '登录账号，或以游客身份体验学习流程。' }}</p>
      <form @submit.prevent="submit">
        <label v-if="mode === 'register'">昵称<input v-model="displayName" required maxlength="40" autocomplete="nickname" :disabled="busy"></label>
        <label>账号<input v-model="username" required minlength="3" maxlength="32" pattern="[A-Za-z0-9_]{3,32}" autocomplete="username" autocapitalize="none" spellcheck="false" :disabled="busy" :aria-describedby="mode === 'register' ? 'username-help' : undefined"></label>
        <small v-if="mode === 'register'" id="username-help">3–32 位字母、数字或下划线。</small>
        <label>密码<input v-model="password" type="password" required :minlength="mode === 'register' ? 8 : 1" maxlength="128" :autocomplete="mode === 'register' ? 'new-password' : 'current-password'" :disabled="busy" :aria-describedby="mode === 'register' ? 'password-help' : undefined"></label>
        <small v-if="mode === 'register'" id="password-help">8–128 位。</small>
        <label v-if="mode === 'register'">确认密码<input v-model="confirmation" type="password" required minlength="8" maxlength="128" autocomplete="new-password" :disabled="busy"></label>
        <button class="primary" type="submit" :disabled="busy">{{ busy ? '正在处理…' : mode === 'register' ? '注册并登录' : '登录' }}</button>
      </form>
      <div class="account-links"><button class="secondary" :disabled="busy" @click="switchMode">{{ mode === 'register' ? '已有账号？去登录' : '没有账号？去注册' }}</button><button class="secondary" :disabled="busy" @click="guest">先以游客体验</button></div>
      </section>
    </div>
    <div v-else :key="journeyKey"><slot :user="user" /></div>
  </template>
</template>
