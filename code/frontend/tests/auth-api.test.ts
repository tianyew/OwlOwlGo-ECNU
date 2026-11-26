// @vitest-environment happy-dom
import { afterEach, expect, it, vi } from 'vitest';
import { AUTH_EXPIRED_EVENT, authApi, AuthError } from '../src/shared/api/auth';
import { learningApi } from '../src/shared/api/learning';

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });

it('sends credentials with cookies and surfaces rate-limit errors', async () => {
  const fetch = vi.fn().mockResolvedValue(new Response(
    JSON.stringify({ detail: '操作过于频繁，请稍后重试。' }), { status: 429 },
  ));
  vi.stubGlobal('fetch', fetch);
  await expect(authApi.login({ username: 'alice', password: 'test-password' }))
    .rejects.toMatchObject({ status: 429, message: '操作过于频繁，请稍后重试。' });
  expect(fetch).toHaveBeenCalledWith('/api/v1/auth/login', expect.objectContaining({
    method: 'POST', credentials: 'same-origin',
    body: JSON.stringify({ username: 'alice', password: 'test-password' }),
  }));
});

it('aborts a stalled session check and clears its timer', async () => {
  vi.useFakeTimers();
  vi.stubGlobal('fetch', vi.fn((_url, options: RequestInit) => new Promise((_resolve, reject) => {
    options.signal!.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')));
  })));
  const check = expect(authApi.me()).rejects.toMatchObject({ status: 0, message: '连接超时，请重试以确认登录状态。' });
  await vi.advanceTimersByTimeAsync(10000);
  await check;
  expect(vi.getTimerCount()).toBe(0);
});

it('notifies the account gate when a protected learning request expires', async () => {
  const expired = vi.fn();
  window.addEventListener(AUTH_EXPIRED_EVENT, expired);
  try {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(
      JSON.stringify({ detail: '请先登录。' }), { status: 401 },
    )));
    await expect(learningApi.load()).rejects.toBeInstanceOf(AuthError);
    expect(expired).toHaveBeenCalledOnce();
  } finally { window.removeEventListener(AUTH_EXPIRED_EVENT, expired); }
});
