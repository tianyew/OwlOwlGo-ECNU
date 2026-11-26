<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { AUTH_EXPIRED_EVENT, authApi, AuthError, type User } from '../../shared/api/auth';
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
type Field = 'displayName' | 'username' | 'password' | 'confirmation';
const form = ref<HTMLFormElement>();
const touched = ref<Partial<Record<Field, boolean>>>({});
const submitted = ref(false);
const usernameError = ref('');
const fieldErrors = computed<Record<Field, string>>(() => {
  const name = displayName.value.trim();
  const account = username.value.trim().toLowerCase();
  const passwordLength = Array.from(password.value).length;
  const registering = mode.value === 'register';
  return {
    displayName: !registering ? '' : !name ? '请输入昵称。'
      : Array.from(name).length > 40 ? '昵称不能超过 40 个字符。' : '',
    username: !account ? '请输入账号。'
      : account.length < 3 || account.length > 32 ? '账号长度应为 3–32 位。'
      : !/^[a-z0-9_]+$/.test(account) ? '账号只能包含英文字母、数字或下划线，不能包含中文或空格。'
      : usernameError.value,
    password: !password.value ? '请输入密码。'
      : registering && passwordLength < 8 ? '密码至少需要 8 个字符。'
      : passwordLength > 128 ? '密码不能超过 128 个字符。' : '',
    confirmation: !registering ? '' : !confirmation.value ? '请再次输入密码。'
      : confirmation.value !== password.value ? '两次输入的密码不一致。' : '',
  };
});
function fieldError(field: Field) {
  return (submitted.value || touched.value[field]) ? fieldErrors.value[field] : '';
}
function description(field: Field) {
  return `${field}-help${fieldError(field) ? ` ${field}-error` : ''}`;
}
function resetValidation() {
  touched.value = {}; submitted.value = false; usernameError.value = '';
}
async function focusFirstError() {
  await nextTick();
  form.value?.querySelector<HTMLInputElement>('[aria-invalid="true"]')?.focus();
}
watch(username, () => { usernameError.value = ''; });
function message(reason: unknown) { return reason instanceof Error ? reason.message : '操作失败，请重试。'; }
async function restoreSession() {
  loading.value = true; error.value = '';
  try {
    user.value = await authApi.me();
    showForm.value = false;
  }
  catch (reason) { if (!(reason instanceof AuthError && reason.status === 401)) error.value = message(reason); }
  finally { loading.value = false; }
}
function sessionExpired() {
  if (!user.value) return;
  user.value = null; showForm.value = true; mode.value = 'login'; journeyKey.value++;
  password.value = ''; confirmation.value = '';
  resetValidation();
  error.value = '登录已过期，请重新登录。已保存的学习记录会保留，未保存的操作需要重新完成。';
}
onMounted(() => {
  window.addEventListener(AUTH_EXPIRED_EVENT, sessionExpired);
  void restoreSession();
});
onBeforeUnmount(() => window.removeEventListener(AUTH_EXPIRED_EVENT, sessionExpired));
function switchMode() {
  mode.value = mode.value === 'login' ? 'register' : 'login';
  password.value = ''; confirmation.value = ''; error.value = '';
  resetValidation();
}
async function submit() {
  if (busy.value) return;
  error.value = '';
  submitted.value = true;
  if (Object.values(fieldErrors.value).some(Boolean)) {
    await focusFirstError(); return;
  }
  busy.value = true;
  try {
    const credentials = { username: username.value.trim().toLowerCase(), password: password.value };
    user.value = mode.value === 'register'
      ? await authApi.register({ ...credentials, display_name: displayName.value.trim() })
      : await authApi.login(credentials);
    password.value = ''; confirmation.value = ''; showForm.value = false; journeyKey.value++;
    resetValidation();
  } catch (reason) {
    if (mode.value === 'register' && reason instanceof AuthError && reason.status === 409) {
      usernameError.value = '该账号已被注册，请更换账号，或点击下方「已有账号？去登录」。';
    } else { error.value = message(reason); }
  }
  finally { busy.value = false; }
  if (usernameError.value) await focusFirstError();
}
async function logout() {
  if (busy.value) return;
  busy.value = true; error.value = '';
  try {
    await authApi.logout(); user.value = null; showForm.value = true; mode.value = 'login';
    username.value = ''; displayName.value = ''; password.value = ''; confirmation.value = '';
    resetValidation();
    journeyKey.value++;
  } catch (reason) { error.value = message(reason); }
  finally { busy.value = false; }
}
function guest() {
  showForm.value = false; error.value = ''; password.value = ''; confirmation.value = '';
  resetValidation();
}
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
    <p v-if="error" class="account-error" role="alert">{{ error }} <button v-if="!user && !busy" class="secondary" @click="restoreSession">重新检查登录状态</button></p>
    <div v-if="showForm" class="account-layout">
      <aside class="account-story">

        <h2>让中文，<br><span>走进你的日常。</span></h2>
        <p>从一句问候，到一场对话。<br>找到适合你的起点，以自己的节奏向前。</p>
        <div class="story-art" aria-hidden="true"><span class="language-tile">你</span><span class="language-tile">nǐ</span></div>

      </aside>
      <section class="account-card">

      <h1>{{ mode === 'register' ? '创建你的学习账号' : '欢迎回来' }}</h1>
      <p>{{ mode === 'register' ? '注册后自动登录，开启你的中文之旅。' : '登录账号，或以游客身份体验学习流程。' }}</p>
      <form ref="form" novalidate @submit.prevent="submit">
        <p class="account-form-note">以下字段均为必填。</p>
        <div v-if="mode === 'register'" class="account-field">
          <label for="account-display-name">昵称</label>
          <input id="account-display-name" v-model="displayName" name="display_name" required autocomplete="nickname" placeholder="例如：小林" :disabled="busy" :aria-invalid="Boolean(fieldError('displayName'))" :aria-describedby="description('displayName')" @blur="touched.displayName = true">
          <small id="displayName-help">1–40 个字符，可使用中文；用于学习页面显示，可以与他人重复。</small>
          <p v-if="fieldError('displayName')" id="displayName-error" class="account-field-error" role="alert">{{ fieldError('displayName') }}</p>
        </div>
        <div class="account-field">
          <label for="account-username">账号</label>
          <input id="account-username" v-model="username" name="username" required autocomplete="username" autocapitalize="none" spellcheck="false" :placeholder="mode === 'register' ? '例如：xiaolin_01' : '请输入你的账号'" :disabled="busy" :aria-invalid="Boolean(fieldError('username'))" :aria-describedby="description('username')" @blur="touched.username = true">
          <small id="username-help">{{ mode === 'register' ? '3–32 位英文字母、数字或下划线，不区分大小写；用于登录，需要唯一。' : '请输入注册时设置的账号，不是昵称；账号不区分大小写。' }}</small>
          <p v-if="fieldError('username')" id="username-error" class="account-field-error" role="alert">{{ fieldError('username') }}</p>
        </div>
        <div class="account-field">
          <label for="account-password">密码</label>
          <input id="account-password" v-model="password" name="password" type="password" required :autocomplete="mode === 'register' ? 'new-password' : 'current-password'" :placeholder="mode === 'register' ? '请设置 8–128 个字符的密码' : '请输入登录密码'" :disabled="busy" :aria-invalid="Boolean(fieldError('password'))" :aria-describedby="description('password')" @blur="touched.password = true">
          <small id="password-help">{{ mode === 'register' ? '8–128 个字符，区分大小写。建议组合字母、数字和符号；空格也计入密码。' : '密码区分大小写，输入时请注意空格。' }}</small>
          <p v-if="fieldError('password')" id="password-error" class="account-field-error" role="alert">{{ fieldError('password') }}</p>
        </div>
        <div v-if="mode === 'register'" class="account-field">
          <label for="account-confirmation">确认密码</label>
          <input id="account-confirmation" v-model="confirmation" name="confirmation" type="password" required autocomplete="new-password" placeholder="请再次输入上面的密码" :disabled="busy" :aria-invalid="Boolean(fieldError('confirmation'))" :aria-describedby="description('confirmation')" @blur="touched.confirmation = true">
          <small id="confirmation-help">请与上面的密码保持完全一致，包括大小写和空格。</small>
          <p v-if="fieldError('confirmation')" id="confirmation-error" class="account-field-error" role="alert">{{ fieldError('confirmation') }}</p>
        </div>
        <button class="primary" type="submit" :disabled="busy">{{ busy ? '正在处理…' : mode === 'register' ? '注册并登录' : '登录' }}</button>
      </form>
      <div class="account-links"><button class="secondary" :disabled="busy" @click="switchMode">{{ mode === 'register' ? '已有账号？去登录' : '没有账号？去注册' }}</button><button class="secondary" :disabled="busy" @click="guest">先以游客体验</button></div>
      </section>
    </div>
    <div v-else :key="journeyKey"><slot :user="user" /></div>
  </template>
</template>

<style scoped>
.account-field { display: grid; gap: 6px; min-width: 0; }
.account-form-note { margin: 0; color: var(--muted); font-size: 13px; }
.account-field .account-field-error { margin: 0; padding: 0; background: transparent; border-radius: 0; color: #a33c2e; font-size: 13px; line-height: 1.6; }
.account-field input[aria-invalid="true"] { border-color: #a33c2e; }
.account-field input[aria-invalid="true"]:focus { outline: 2px solid #a33c2e; outline-offset: 2px; }
</style>
