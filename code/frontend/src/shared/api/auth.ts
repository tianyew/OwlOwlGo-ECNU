export interface User { id: string; username: string; display_name: string }
export interface Credentials { username: string; password: string }
export interface Registration extends Credentials { display_name: string }
export const AUTH_EXPIRED_EVENT = 'owl:auth-expired';
export function notifyAuthExpired() { window.dispatchEvent(new Event(AUTH_EXPIRED_EVENT)); }
export class AuthError extends Error {
  constructor(message: string, public status: number) { super(message); }
}
async function request<T>(path: string, body?: object): Promise<T> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 10000);
  try {
    const response = await fetch(`/api/v1/auth/${path}`, {
      method: body ? 'POST' : 'GET', credentials: 'same-origin',
      signal: controller.signal,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    if (!response.ok) {
      const error = await response.json().catch(() => null);
      throw new AuthError(typeof error?.detail === 'string' ? error.detail : '账号服务暂时不可用，请稍后重试。', response.status);
    }
    if (response.status === 204) return undefined as T;
    return await response.json();
  } catch (reason) {
    if (reason instanceof AuthError) throw reason;
    throw new AuthError(controller.signal.aborted
      ? '连接超时，请重试以确认登录状态。'
      : '暂时无法连接，请稍后重试。', 0);
  } finally { window.clearTimeout(timeout); }
}
export const authApi = {
  me: () => request<User>('me'),
  login: (body: Credentials) => request<User>('login', body),
  register: (body: Registration) => request<User>('register', body),
  logout: () => request<void>('logout', {}),
};
