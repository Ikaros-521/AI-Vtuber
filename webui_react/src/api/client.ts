/** 后端 API 客户端。开发期走 vite 代理，部署后同源。 */

export interface ApiResult {
  code: number
  message?: string
  [key: string]: unknown
}

async function request<T extends ApiResult>(url: string, init?: RequestInit): Promise<T> {
  const resp = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!resp.ok && resp.status !== 409 && resp.status !== 422) {
    throw new Error(`HTTP ${resp.status}`)
  }
  return (await resp.json()) as T
}

function get<T extends ApiResult>(url: string) {
  return request<T>(url)
}

function post<T extends ApiResult>(url: string, body?: unknown) {
  return request<T>(url, { method: 'POST', body: body === undefined ? undefined : JSON.stringify(body) })
}

// ---------- 配置 ----------

export interface ConfigGetResult extends ApiResult {
  config: Record<string, unknown>
  sha256: string
  path: string
}

export interface ConfigSaveResult extends ApiResult {
  sha256?: string
  path?: (string | number)[]
}

export const api = {
  getConfig: () => get<ConfigGetResult>('/api/config'),

  saveConfig: (baseSha256: string, changes: { path: (string | number)[]; value: unknown }[]) =>
    post<ConfigSaveResult>('/api/config/save', { base_sha256: baseSha256, changes }),

  // ---------- 运行控制 ----------
  opsStatus: () => get<ApiResult & { running: boolean }>('/api/ops/status'),
  opsRun: () => post<ApiResult>('/api/ops/run'),
  opsStop: () => post<ApiResult>('/api/ops/stop'),
  opsRestart: () => post<ApiResult>('/api/ops/restart'),

  // ---------- 日志与聊天 ----------
  runLog: () => get<ApiResult & { title: string; note: string; lines: string[] }>('/api/logs/run'),
  chatLog: (after: number) => get<ApiResult & { messages: ChatMessage[] }>(`/api/chat-log?after=${after}`),
  chatSend: (mode: string, username: string, content: string) =>
    post<ApiResult>('/api/chat-log/send', { mode, username, content }),

  // ---------- 动作按钮与文件 ----------
  action: (id: string, payload?: Record<string, unknown>) =>
    post<ApiResult & { items?: string[]; models?: string[] }>(`/api/actions/${id}`, payload ?? {}),
  fileGet: (path: string) => get<ApiResult & { content: string }>(`/api/file?path=${encodeURIComponent(path)}`),
  filePut: (path: string, content: string) =>
    request<ApiResult>('/api/file', { method: 'PUT', body: JSON.stringify({ path, content }) }),
}

export interface ChatMessage {
  seq: number
  content: string
  name: string
  stamp: string
  mine: boolean
}
