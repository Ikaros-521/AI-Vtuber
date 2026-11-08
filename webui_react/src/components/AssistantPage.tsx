/** 配置助手（v5 P2）：把需求翻译成配置变更，按三档安全等级应用。

 * 人工审核（默认）：每条变更待确认；自动审核：安全变更自动落盘、敏感变更仍待确认；
 * 完全访问：全部自动落盘。落盘即写 config.json，重启程序后在直播间生效。
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { api, configChatStream, type ConfigChange } from '../api/client'
import { deepDiff } from '../lib/path'
import { useConfigStore } from '../state/configStore'
import { notify, useConfirmStore } from '../state/ui'

const BTN =
  'rounded-lg border border-slate-200 px-3 py-1.5 text-[12.5px] transition hover:border-[color-mix(in_srgb,var(--accent)_45%,#e4e7ec)] disabled:opacity-50'

const LEVEL_OPTIONS = [
  { value: 'manual', label: '人工审核', desc: '每条变更都等你确认' },
  { value: 'auto', label: '自动审核', desc: '安全变更直接生效，敏感变更仍需确认' },
  { value: 'full', label: '完全访问', desc: '全部自动生效（谨慎）' },
]

interface ChatMessage {
  role: 'user' | 'assistant'
  text: string
  questions?: string[]
  changes?: ConfigChange[]
}

interface StoredSession {
  id: string
  title: string
  messages: ChatMessage[]
  updatedAt: number
}

const SESSIONS_KEY = 'luna-assistant-sessions'
const MAX_STORED_SESSIONS = 10

function loadStoredSessions(): StoredSession[] {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY)
    return raw ? (JSON.parse(raw) as StoredSession[]) : []
  } catch {
    return []
  }
}

function persistSessions(list: StoredSession[]) {
  try {
    localStorage.setItem(SESSIONS_KEY, JSON.stringify(list.slice(0, MAX_STORED_SESSIONS)))
  } catch {
    // localStorage 满/被禁：会话持久化是体验增强，失败不影响对话
  }
}

export function AssistantPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [elapsed, setElapsed] = useState(0)
  const [level, setLevel] = useState<string>('manual')
  const [sessionVersion, setSessionVersion] = useState(0)
  const [sessions, setSessions] = useState<StoredSession[]>([])
  const [serverSessionIds, setServerSessionIds] = useState<string[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string>('')
  const sessionId = useRef(`assistant-${sessionVersion}`)
  const bottomRef = useRef<HTMLDivElement>(null)

  // 恢复最近会话（切页/刷新后不丢对话）；服务端会话列表用于标注记忆有效性
  useEffect(() => {
    const stored = loadStoredSessions()
    setSessions(stored)
    if (stored.length > 0) {
      const last = stored[0]
      sessionId.current = last.id
      setActiveSessionId(last.id)
      setMessages(last.messages)
    }
    void api.assistantSessions().then((resp) => {
      if (resp.code === 200) setServerSessionIds(resp.sessions.map((item) => item.id))
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 会话自动持久化：消息一变就落 localStorage（最近 10 个会话，切页/刷新可恢复）
  useEffect(() => {
    if (messages.length === 0) return
    const id = sessionId.current
    const title = (messages.find((m) => m.role === 'user')?.text ?? '新会话').slice(0, 30)
    setSessions((prev) => {
      const rest = prev.filter((item) => item.id !== id)
      const list = [{ id, title, messages, updatedAt: Date.now() }, ...rest].slice(0, MAX_STORED_SESSIONS)
      persistSessions(list)
      return list
    })
  }, [messages])

  useEffect(() => {
    sessionId.current = `assistant-${sessionVersion}`
  }, [sessionVersion])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    void api.assistantSettings().then((resp) => {
      if (resp.code === 200 && resp.safety_level) setLevel(resp.safety_level)
    })
  }, [])

  // 等待计时：配置助手单轮要 10-30s，无反馈会被当成没响应
  useEffect(() => {
    if (!busy) return
    setElapsed(0)
    const timer = setInterval(() => setElapsed((sec) => sec + 1), 1000)
    return () => clearInterval(timer)
  }, [busy])

  const changeLevel = async (next: string) => {
    const target = LEVEL_OPTIONS.find((l) => l.value === next)
    const apply = async () => {
      const resp = await api.setAssistantSettings(next)
      if (resp.code === 200) {
        setLevel(next)
        notify.ok(resp.message || '已切换')
      } else {
        notify.err(resp.message || '切换失败')
      }
    }
    if (next === 'full') {
      useConfirmStore.getState().ask('切换到完全访问', () => void apply(), '此后助手提出的所有配置变更都会立即生效，不再逐条确认。确定吗？')
    } else {
      await apply()
    }
    void target
  }

  const send = async () => {
    const text = input.trim()
    if (!text || busy) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', text }, { role: 'assistant', text: '' }])
    setBusy(true)
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 120000)
    try {
      await configChatStream(
        sessionId.current,
        text,
        // 流式 delta：更新最后一条（占位中的助手消息）
        (delta) =>
          setMessages((prev) =>
            prev.map((msg, i) => (i === prev.length - 1 ? { ...msg, text: msg.text + delta } : msg)),
          ),
        (ev) => {
          if (ev.type === 'done') {
            const cost = ev.elapsed_ms ? `（耗时 ${(ev.elapsed_ms / 1000).toFixed(1)}s）` : ''
            const applied = (ev.changes ?? []).some((c) => c.status === 'applied')
            if (applied) {
              // 助手是服务端直写 config.json，前端各页读的是 configStore 基线——
              // 不同步的话信号链/设置页一直显示旧值（用户得手动刷新）
              const st = useConfigStore.getState()
              const dirty = st.config && st.draft ? deepDiff(st.config, st.draft).length > 0 : false
              const sync = () => {
                void st.refreshConfig()
                notify.ok('配置已同步到前端 · 重启程序后作用于直播间')
              }
              if (dirty) {
                useConfirmStore
                  .getState()
                  .ask('同步助手改过的配置', () => void sync(), '你有未保存的草稿改动；同步将以助手落盘的配置为准，草稿会被丢弃。')
              } else {
                sync()
              }
            }
            setMessages((prev) =>
              prev.map((msg, i) =>
                i === prev.length - 1
                  ? { ...msg, text: msg.text.trim() + cost, questions: ev.questions, changes: ev.changes }
                  : msg,
              ),
            )
          } else {
            setMessages((prev) => prev.map((msg, i) => (i === prev.length - 1 ? { ...msg, text: `⚠️ ${ev.message}` } : msg)))
          }
        },
        controller.signal,
      )
    } catch (e) {
      const aborted = e instanceof DOMException && e.name === 'AbortError'
      const reason = aborted
        ? '等待超时（120s）——检查模型服务/网关是否在运行，或换更快的模型（agent.config_assistant.chat_type）后重试'
        : `请求失败：${e}`
      setMessages((prev) => prev.map((msg, i) => (i === prev.length - 1 && msg.text === '' ? { ...msg, text: `⚠️ ${reason}` } : msg)))
    } finally {
      clearTimeout(timeout)
      setBusy(false)
    }
  }

  const applyChange = useCallback(
    async (messageIndex: number, changeIndex: number) => {
      const change = messages[messageIndex]?.changes?.[changeIndex]
      if (!change) return
      const resp = await api.configApply([{ path: change.path, value: change.value }])
      if (resp.code === 200) {
        notify.ok('已应用 · 重启程序后生效')
        setMessages((prev) =>
          prev.map((msg, mi) =>
            mi === messageIndex
              ? {
                  ...msg,
                  changes: msg.changes?.map((c, ci) => (ci === changeIndex ? { ...c, status: 'applied' as const } : c)),
                }
              : msg,
          ),
        )
      } else {
        notify.err(resp.message || '应用失败')
      }
    },
    [messages],
  )

  const resetSession = () => {
    useConfirmStore.getState().ask('开始新会话', () => {
      setMessages([])
      setSessionVersion((v) => v + 1)
    }, '将清空当前对话上下文（旧会话保留在会话列表里可随时切回；已生效的配置不受影响）。')
  }

  const switchSession = (id: string) => {
    const target = sessions.find((item) => item.id === id)
    if (!target || id === sessionId.current) return
    sessionId.current = id
    setActiveSessionId(id)
    setMessages(target.messages)
    if (!serverSessionIds.includes(id)) {
      notify.info('该会话早于最近一次服务重启，助手不记得上文了——继续聊会重新开始理解你')
    }
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-140px)] w-full max-w-[900px] flex-col">
      {/* 顶栏：安全等级 */}
      <div className="card-surface mb-3 flex flex-wrap items-center gap-2 p-3">
        <span className="text-[14px] font-semibold">配置助手</span>
        <span className="text-xs text-[var(--ink-mut)]">管理员说目标，AI 翻译成配置变更并按安全等级应用</span>
        <span className="ml-auto flex items-center gap-2">
          <span className="flex items-center gap-1 text-[12.5px] text-[var(--ink-mut)]">
            会话：
          </span>
          <select
            className="inp w-auto max-w-[220px] py-1.5 text-[12.5px]"
            value={activeSessionId || '__none__'}
            onChange={(e) => {
              if (e.target.value !== '__none__') switchSession(e.target.value)
            }}
            title="历史会话列表：点击切回（对话记录保存在本机浏览器）"
          >
            {sessions.length === 0 && (
              <option value="__none__">暂无历史会话（发第一条消息后自动保存）</option>
            )}
            {sessions.map((item) => (
              <option key={item.id} value={item.id}>
                {item.title} · {new Date(item.updatedAt).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                {serverSessionIds.includes(item.id) ? '' : '（记忆已失效）'}
              </option>
            ))}
          </select>
          <select
            className="inp w-auto py-1.5 text-[12.5px]"
            value={level}
            onChange={(e) => void changeLevel(e.target.value)}
            title="安全等级：助手改配置的自动化程度"
          >
            {LEVEL_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label} · {option.desc}
              </option>
            ))}
          </select>
          <button className={`${BTN} whitespace-nowrap`} onClick={resetSession}>
            新会话
          </button>
        </span>
      </div>

      {/* 对话流 */}
      <div className="card-surface flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 && (
          <div className="space-y-2 py-6 text-center text-[13px] text-[var(--ink-mut)]">
            <p>直接说配置目标，例如：</p>
            <p>「配置抖音无人直播：dy 平台 + 数字人视频源 + 闲时任务」</p>
            <p>「加强弹幕辱骂过滤，命中直接拉黑」</p>
            <p>「闲时主动说话降频：一小时最多 3 次」</p>
          </div>
        )}
        {messages.map((msg, mi) => (
          <div key={mi} className={msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
            <div
              className="max-w-[85%] rounded-2xl px-3.5 py-2.5 text-[13.5px] leading-relaxed"
              style={
                msg.role === 'user'
                  ? { background: 'var(--accent)', color: 'white' }
                  : { background: 'color-mix(in srgb, var(--ink-mut) 8%, white)' }
              }
            >
              <p className="whitespace-pre-wrap">{msg.text}</p>
              {msg.questions && msg.questions.length > 0 && (
                <ul className="mt-1.5 list-disc pl-4 text-[12.5px] text-[var(--ink-mut)]">
                  {msg.questions.map((q, qi) => (
                    <li key={qi}>{q}</li>
                  ))}
                </ul>
              )}
              {msg.changes && msg.changes.length > 0 && (
                <div className="mt-2.5 space-y-2">
                  {msg.changes.map((change, ci) => (
                    <div
                      key={ci}
                      className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-[12.5px]"
                      style={change.status === 'failed' ? { borderColor: 'var(--warn)' } : undefined}
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <code className="font-mono text-[12px]">{change.path.join(' . ')}</code>
                        <span>→</span>
                        <code className="font-mono text-[12px] font-semibold">{JSON.stringify(change.value)}</code>
                        {change.danger && (
                          <span
                            className="rounded-full px-2 py-0.5 text-[11px]"
                            style={{ background: 'color-mix(in srgb, var(--warn) 14%, white)', color: 'var(--warn)' }}
                          >
                            敏感
                          </span>
                        )}
                        <span
                          className="ml-auto rounded-full px-2 py-0.5 text-[11px]"
                          style={
                            change.status === 'applied'
                              ? { background: 'color-mix(in srgb, var(--ok) 14%, white)', color: 'var(--ok)' }
                              : change.status === 'failed'
                                ? { background: 'color-mix(in srgb, var(--warn) 14%, white)', color: 'var(--warn)' }
                                : undefined
                          }
                        >
                          {change.status === 'applied' ? '已生效' : change.status === 'failed' ? '失败' : '待确认'}
                        </span>
                        {change.status === 'pending' && (
                          <button className={BTN} onClick={() => void applyChange(mi, ci)}>
                            应用
                          </button>
                        )}
                      </div>
                      {change.reason && <p className="mt-1 text-[12px] text-[var(--ink-mut)]">{change.reason}</p>}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {busy && (
          <p className="text-xs text-[var(--ink-mut)]">
            助手思考中…… {elapsed}s{elapsed >= 30 ? '（模型响应较慢，仍在等待，请勿重复发送）' : ''}
          </p>
        )}
        <div ref={bottomRef} />
      </div>

      {/* 输入区 */}
      <div className="card-surface mt-3 flex items-center gap-2 p-3">
        <input
          className="inp flex-1"
          placeholder="描述配置目标，例如：配置抖音无人直播……"
          value={input}
          disabled={busy}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void send()
            }
          }}
        />
        <button
          className="rounded-lg px-4 py-2 text-[13px] font-medium text-white disabled:opacity-50"
          style={{ background: 'var(--accent)' }}
          disabled={busy || !input.trim()}
          onClick={() => void send()}
        >
          发送
        </button>
      </div>
    </div>
  )
}
