// @vitest-environment happy-dom
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createApp, nextTick, type App } from 'vue';
import AccountGate from '../src/features/auth/AccountGate.vue';
import { authApi, AuthError } from '../src/shared/api/auth';
vi.mock('../src/shared/api/auth', async (original) => {
  const module = await original<typeof import('../src/shared/api/auth')>();
  return { ...module, authApi: { me: vi.fn(), login: vi.fn(), register: vi.fn(), logout: vi.fn() } };
});
let app: App;
let host: HTMLDivElement;
const user = { id: 'one', username: 'alice', display_name: '安娜' };
async function settle() { for (let i = 0; i < 6; i++) await nextTick(); }
async function click(text: string) {
  const button = [...host.querySelectorAll('button')].find(b => b.textContent?.includes(text));
  expect(button).toBeDefined(); button!.click(); await settle();
}
async function fill(values: string[]) {
  host.querySelectorAll('input').forEach((input, i) => {
    input.value = values[i]; input.dispatchEvent(new Event('input', { bubbles: true }));
  }); await settle();
}
async function submit() {
  host.querySelector('form')!.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  await settle();
}
async function mount() {
  host = document.createElement('div'); document.body.appendChild(host);
  app = createApp(AccountGate); app.mount(host); await settle();
}
beforeEach(() => { vi.resetAllMocks(); vi.mocked(authApi.me).mockRejectedValue(new AuthError('请登录', 401)); });
afterEach(() => { app?.unmount(); host?.remove(); });
describe('account flow', () => {
  it('registers after confirmation, shows the account and logs out', async () => {
    vi.mocked(authApi.register).mockResolvedValue(user);
    vi.mocked(authApi.logout).mockResolvedValue();
    await mount(); await click('去注册');
    await fill(['安娜', 'alice', 'password-123', 'different-123']); await submit();
    expect(host.textContent).toContain('两次输入的密码不一致');
    expect(authApi.register).not.toHaveBeenCalled();
    await fill(['安娜', 'alice', 'password-123', 'password-123']); await submit();
    expect(authApi.register).toHaveBeenCalledWith({ display_name: '安娜', username: 'alice', password: 'password-123' });
    expect(host.textContent).toContain('安娜'); expect(host.querySelector('form')).toBeNull();
    await click('退出登录'); expect(authApi.logout).toHaveBeenCalledOnce();
    expect(host.querySelector('form')).not.toBeNull(); expect(host.textContent).not.toContain('@alice');
  });
  it('restores sessions and preserves the signed in state on failed logout', async () => {
    vi.mocked(authApi.me).mockResolvedValue(user);
    vi.mocked(authApi.logout).mockRejectedValue(new Error('网络不可用'));
    await mount(); expect(host.textContent).toContain('@alice');
    await click('退出登录'); expect(host.textContent).toContain('网络不可用');
    expect(host.textContent).toContain('@alice');
  });
  it('reports login failure and allows guest access', async () => {
    vi.mocked(authApi.login).mockRejectedValue(new AuthError('账号或密码不正确', 401));
    await mount(); await fill(['alice', 'wrong-password']); await submit();
    expect(host.textContent).toContain('账号或密码不正确');
    await click('先以游客体验'); expect(host.querySelector('form')).toBeNull();
    await click('登录 / 注册'); expect(host.querySelector('form')).not.toBeNull();
    expect((host.querySelector('input[type="password"]') as HTMLInputElement).value).toBe('');
  });
});
