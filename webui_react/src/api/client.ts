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
    post<ApiResult & { items?: string[]; models?: string[]; audio_path?: string; tts_type?: string }>(`/api/actions/${id}`, payload ?? {}),
  fileGet: (path: string) => get<ApiResult & { content: string }>(`/api/file?path=${encodeURIComponent(path)}`),
  filePut: (path: string, content: string) =>
    request<ApiResult>('/api/file', { method: 'PUT', body: JSON.stringify({ path, content }) }),

  // ---------- 登录 ----------
  authStatus: () => get<ApiResult & { enabled: boolean; authed: boolean; username?: string }>('/api/auth/status'),
  authLogin: (username: string, password: string) => post<ApiResult>('/api/auth/login', { username, password }),
  authLogout: () => post<ApiResult>('/api/auth/logout'),

  // ---------- 数据分析 ----------
  dataAnalysis: (top: number) =>
    get<ApiResult & Record<string, unknown>>(`/api/data-analysis?top=${top}`),

  // ---------- Agent 工作台（v5） ----------
  agentOverview: () => get<AgentOverviewResult>('/api/agent/overview'),
  agentTrace: () => get<ApiResult & { records: AgentTraceRecord[] }>('/api/agent/trace'),
  agentStats: () => get<ApiResult & AgentStats>('/api/agent/stats'),
  agentKill: (on: boolean) => post<ApiResult>('/api/agent/kill', { on }),
  agentViewers: (keyword: string) =>
    get<ApiResult & { viewers: AgentViewer[] }>(`/api/agent/memory/viewers?keyword=${encodeURIComponent(keyword)}`),
  agentSetNote: (platform: string, username: string, note: string) =>
    post<ApiResult>('/api/agent/memory/viewer/note', { platform, username, note }),
  agentDeleteViewer: (platform: string, username: string) =>
    post<ApiResult>('/api/agent/memory/viewer/delete', { platform, username }),
  agentHighlights: () => get<ApiResult & { highlights: AgentHighlight[] }>('/api/agent/memory/highlights'),
  agentDeleteHighlight: (rowId: number) =>
    post<ApiResult>('/api/agent/memory/highlight/delete', { row_id: rowId }),

  // ---------- 配置助手（v5 P2） ----------
  configChat: (sessionId: string, message: string) =>
    post<ApiResult & { reply: string; changes: ConfigChange[]; questions: string[]; level: string }>(
      '/api/agent/config-chat',
      { session_id: sessionId, message },
    ),
  configApply: (changes: { path: string[]; value: unknown }[]) =>
    post<ApiResult & { results: { path: string[]; ok: boolean }[] }>('/api/agent/config-apply', { changes }),
  assistantSettings: () => get<ApiResult & { safety_level: string }>('/api/agent/assistant-settings'),
  setAssistantSettings: (safetyLevel: string) =>
    post<ApiResult>('/api/agent/assistant-settings', { safety_level: safetyLevel }),
}

// ---------- 配置助手类型 ----------

export interface ConfigChange {
  path: string[]
  value: unknown
  reason: string
  danger: boolean
  status?: 'pending' | 'applied' | 'failed'
}

// ---------- Agent 工作台类型（与 webui_server/schemas.py 的模型一一对应） ----------

export interface AgentOverviewResult extends ApiResult {
  agent: Record<string, unknown>
  tool_catalog: AgentToolInfo[]
  running: boolean
  runtime?: AgentRuntimeInfo | null
}

export interface AgentToolInfo {
  name: string
  description: string
  dangerous: boolean
}

export interface AgentRuntimeInfo {
  killed: boolean
  tools_enabled: string[]
  hour_used: number
  hour_limit: number
  recent_trace_count: number
}

export interface AgentTraceRecord {
  ts: string
  event_type: string
  username: string
  source: string
  duration_ms: number
  tool_calls: { name: string; args_digest: string; ms: number; ok: boolean }[]
  degraded: boolean
  reason: string
  output_chars: number
  prompt_chars: number
}

export interface AgentStats {
  total: number
  degraded: number
  degrade_rate: number
  fallback_used: number
  small_routed: number
  avg_ms: number
  tool_total: number
  tool_ok: number
}

export interface AgentViewer {
  platform: string
  username: string
  first_seen: string
  last_seen: string
  interactions: number
  note: string
}

export interface AgentHighlight {
  row_id: number
  ts: string
  username: string
  content: string
}

/** 试听音频的播放地址（后端流式读文件）。 */
export function audioUrl(path: string): string {
  return `/api/audio?path=${encodeURIComponent(path)}`
}

export interface BarDataset {
  users: string[]
  series: { name?: string; data: unknown[] }[]
}

export interface ChatMessage {
  seq: number
  content: string
  name: string
  stamp: string
  mine: boolean
}
