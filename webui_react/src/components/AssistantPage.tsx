/** 配置助手（v5 P2）：把需求翻译成配置变更，按三档安全等级应用。

 * 人工审核（默认）：每条变更待确认；自动审核：安全变更自动落盘、敏感变更仍待确认；
 * 完全访问：全部自动落盘。落盘即写 config.json，重启程序后在直播间生效。
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { api, type ConfigChange } from '../api/client'
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

export function AssistantPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [busy, setBusy] = useState(false)
  const [level, setLevel] = useState<string>('manual')
  const [sessionVersion, setSessionVersion] = useState(0)
  const sessionId = useRef(`assistant-${sessionVersion}`)
  const bottomRef = useRef<HTMLDivElement>(null)

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
    setMessages((prev) => [...prev, { role: 'user', text }])
    setBusy(true)
    try {
      const resp = await api.configChat(sessionId.current, text)
      if (resp.code === 200) {
        setMessages((prev) => [
          ...prev,
          { role: 'assistant', text: resp.reply, questions: resp.questions, changes: resp.changes },
        ])
        if (resp.changes.some((c) => c.status === 'applied')) notify.ok('有变更已生效 · 重启程序后作用于直播间')
      } else {
        setMessages((prev) => [...prev, { role: 'assistant', text: resp.message || '出错了，请重试' }])
      }
    } catch (e) {
      setMessages((prev) => [...prev, { role: 'assistant', text: `请求失败：${e}` }])
    } finally {
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
    }, '将清空当前对话上下文（已生效的配置不受影响）。')
  }

  return (
    <div className="mx-auto flex h-[calc(100vh-140px)] w-full max-w-[900px] flex-col">
      {/* 顶栏：安全等级 */}
      <div className="card-surface mb-3 flex flex-wrap items-center gap-2 p-3">
        <span className="text-[14px] font-semibold">配置助手</span>
        <span className="text-xs text-[var(--ink-mut)]">说出需求，AI 翻译成配置变更</span>
        <span className="ml-auto flex items-center gap-2">
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
            <p>试试这样说：</p>
            <p>「我想要观众能点歌，歌放在 song 目录」</p>
            <p>「弹幕里有人骂人，帮我屏蔽脏话」</p>
            <p>「闲的时候别一直说话，十分钟说一次就行」</p>
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
        {busy && <p className="text-xs text-[var(--ink-mut)]">助手思考中……</p>}
        <div ref={bottomRef} />
      </div>

      {/* 输入区 */}
      <div className="card-surface mt-3 flex items-center gap-2 p-3">
        <input
          className="inp flex-1"
          placeholder="说出你的需求，例如：我想要观众能点歌……"
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
