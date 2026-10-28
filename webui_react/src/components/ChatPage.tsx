/** 聊天页：聊天记录视窗 + 交互坞（发送 / 直接复读 / 调教）。 */
import { useEffect, useRef, useState } from 'react'
import { api, type ChatMessage } from '../api/client'
import { getByPath } from '../lib/path'
import { useConfigStore } from '../state/configStore'
import { useOpsStore } from '../state/opsStore'
import { notify, useJumpStore } from '../state/ui'
import { CHAT_SETTINGS_SECTION } from '../schema'
import { fieldIdOf } from '../schema/types'
import { FieldControl } from './FieldControl'
import { JumpFlash } from './WorkspacePage'

export function ChatPage() {
  const draft = useConfigStore((s) => s.draft)
  const running = useOpsStore((s) => s.running)
  const jump = useJumpStore((s) => s.jump)

  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)
  const lastSeqRef = useRef(0)

  useEffect(() => {
    let alive = true
    const poll = async () => {
      try {
        const resp = await api.chatLog(lastSeqRef.current)
        if (!alive || resp.code !== 200 || resp.messages.length === 0) return
        lastSeqRef.current = resp.messages[resp.messages.length - 1].seq
        setMessages((prev) => [...prev, ...resp.messages].slice(-100))
      } catch {
        /* 后端瞬断，下一轮再拉 */
      }
    }
    poll()
    const timer = setInterval(poll, 2000)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [])

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight })
  }, [messages.length])

  const username = (getByPath(draft ?? {}, ['talk', 'username']) as string | undefined)?.trim() || '主播'
  const triggerKey = getByPath(draft ?? {}, ['talk', 'trigger_key']) as string | undefined

  const send = async (mode: 'comment' | 'reread' | 'tuning') => {
    const content = text.trim()
    if (!content) return
    if (!running) {
      notify.info('请先点击右下角「操作」→「一键运行」启动核心服务')
      return
    }
    setSending(true)
    try {
      const resp = await api.chatSend(mode, username, content)
      if (resp.code === 200) {
        setText('')
        if (mode === 'comment') {
          // 自己的发言立刻显示（main.py 不回显 comment）
          lastSeqRef.current += 1
          setMessages((prev) => [
            ...prev,
            { seq: lastSeqRef.current, content, name: username, stamp: new Date().toLocaleTimeString(), mine: true },
          ])
        }
      } else {
        notify.warn(resp.message ?? '发送失败')
      }
    } catch {
      notify.err('发送失败：连不上后端')
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-[960px] flex-col gap-3 px-4 pb-28 pt-4" style={{ minHeight: 'calc(100vh - 170px)' }}>
      <JumpFlash workspaceId="chat" />

      {/* 聊天记录视窗 */}
      <div className="card-surface flex min-h-[420px] flex-1 flex-col overflow-hidden p-0">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 bg-slate-50 px-4 py-2.5">
          <div className="flex items-center gap-2">
            <span className="text-lg leading-none" style={{ color: 'var(--accent)' }}>💬</span>
            <span className="text-[14px] font-semibold">AI 对话与即时交互</span>
          </div>
          <div className="flex items-center gap-2 text-xs" style={{ color: running ? 'var(--ok)' : '#6b7280' }}>
            <span>{running ? '● 服务运行中' : '○ 核心未运行'}</span>
            {triggerKey && (
              <span className="rounded-full border border-slate-300 px-2 py-0.5 text-[11px] text-[var(--ink-mut)]">
                录音热键: {triggerKey}
              </span>
            )}
          </div>
        </div>

        <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto px-4 py-4">
          {messages.length === 0 && (
            <p className="px-2 py-8 text-center text-[13px] text-[var(--ink-mut)]">
              还没有聊天记录：弹幕被回复后会显示在这里，最多保留最近 100 条
            </p>
          )}
          {messages.map((m) => (
            <div key={m.seq} className={`flex ${m.mine ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[78%] rounded-2xl px-3.5 py-2 ${m.mine ? 'text-white' : 'bg-slate-100 text-[var(--ink)]'}`} style={m.mine ? { background: 'var(--accent)' } : undefined}>
                <div className={`mb-0.5 flex items-center gap-2 text-[11px] ${m.mine ? 'text-white/80' : 'text-[var(--ink-mut)]'}`}>
                  <span className="font-medium">{m.name}</span>
                  <span>{m.stamp}</span>
                </div>
                <div className="whitespace-pre-wrap break-words text-[13px] leading-relaxed">{m.content}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 交互坞 */}
      <div className="card-surface flex flex-col gap-3 p-4">
        <div data-section-id="chat__chat-settings" className="flex flex-wrap items-center gap-x-6 gap-y-3">
          {(CHAT_SETTINGS_SECTION.rows ?? []).flat().map((field, i) => (
            <FieldControl key={i} field={field} fieldId={fieldIdOf('chat', CHAT_SETTINGS_SECTION.id, field)} />
          ))}
        </div>
        <div className="flex items-center gap-2">
          <input
            className="inp flex-1"
            placeholder="输入消息与 AI 对话... (按 Enter 发送)"
            value={text}
            disabled={sending}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.nativeEvent.isComposing) void send('comment')
            }}
          />
          <button
            className="rounded-lg px-5 py-2 text-[13px] font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
            style={{ background: 'var(--accent)' }}
            disabled={sending}
            onClick={() => void send('comment')}
          >
            发送
          </button>
          <button
            className="rounded-lg border border-slate-300 px-3 py-2 text-xs text-[var(--ink-mut)] transition hover:border-[var(--accent)] hover:text-[var(--accent)]"
            disabled={sending}
            onClick={() => void send('reread')}
            title="跳过大模型思考，让当前 TTS 语音引擎直接朗读输入框文字（声音调试）"
          >
            直接复读
          </button>
          <button
            className="rounded-lg border border-slate-300 px-3 py-2 text-xs text-[var(--ink-mut)] transition hover:border-[var(--accent)] hover:text-[var(--accent)]"
            disabled={sending}
            onClick={() => void send('tuning')}
            title="向 LLM 注入提示词或指导信息，不触发语音播放"
          >
            调教
          </button>
        </div>
        <p className="text-[11px] text-[var(--ink-mut)]">
          「同步弹幕 / 语音对话」等设置保存后生效；「去聊天设置」可以
          <button className="mx-1 underline" style={{ color: 'var(--accent)' }} onClick={() => jump('chat', { sectionId: 'chat__chat-settings' })}>
            定位到上面的设置项
          </button>
          。语音对话（直接拾音）由核心程序在运行时执行。
        </p>
      </div>
    </div>
  )
}
