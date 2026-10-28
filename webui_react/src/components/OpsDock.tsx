/** 右下角可折叠操作条：状态徽标 + 保存/运行/停止/日志/重启。

 * 徽标刻意只报状态、不禁用按钮：main.py 自己崩掉时 running_flag 会留在 True，
 * 禁用「一键运行」等于把人锁在重启不了的状态（v2 同款结论）。
 */
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { formatValue } from '../lib/path'
import { useChanges, useConfigStore } from '../state/configStore'
import { useOpsStore } from '../state/opsStore'
import { notify, useConfirmStore, useJumpStore } from '../state/ui'
import { entryForPath } from '../schema'

const PILL = 'rounded-full bg-white px-2.5 py-1 text-xs shadow-md ring-1 ring-slate-200'

export function OpsDock() {
  const changes = useChanges()
  const save = useConfigStore((s) => s.save)
  const running = useOpsStore((s) => s.running)
  const refresh = useOpsStore((s) => s.refresh)
  const jump = useJumpStore((s) => s.jump)
  const ask = useConfirmStore((s) => s.ask)

  const [open, setOpen] = useState(false)
  const [showDirty, setShowDirty] = useState(false)
  const [runLog, setRunLog] = useState<{ title: string; note: string; lines: string[] } | null>(null)
  const [busy, setBusy] = useState(false)

  const dirty = changes.length > 0

  const handleSave = async () => {
    if (!dirty) {
      notify.info('没有未保存的改动')
      return
    }
    const outcome = await save()
    if (outcome.ok) {
      notify.ok(outcome.message)
      return
    }
    notify.err(outcome.message)
    // 校验失败：把用户带到那个框上
    if (outcome.path) {
      const entry = entryForPath(outcome.path)
      if (entry) jump(entry.workspaceId, { fieldId: entry.fieldId })
    }
  }

  const run = async () => {
    setBusy(true)
    try {
      const resp = await api.opsRun()
      resp.code === 200 ? notify.ok(resp.message ?? '已运行') : notify.warn(resp.message ?? '运行失败')
      await refresh()
    } finally {
      setBusy(false)
    }
  }

  const stop = () =>
    ask(
      '确认停止正在运行的直播程序？',
      async () => {
        setBusy(true)
        try {
          const resp = await api.opsStop()
          resp.code === 200 ? notify.ok(resp.message ?? '已停止') : notify.warn(resp.message ?? '停止失败')
          await refresh()
        } finally {
          setBusy(false)
        }
      },
      '弹幕监听、文案播报和虚拟身体会一起停下；正在直播的话，这一下就是断播。',
    )

  const restart = () =>
    ask(
      '确认重启 webui？',
      async () => {
        notify.info('重启中...')
        await api.opsRestart().catch(() => undefined)
        // 服务端 os.execl 自替换，这个响应多半送不回来；过几秒还不通就提示手动刷新
        setTimeout(() => {
          void api.opsStatus().then(
            () => notify.ok('webui 已重启'),
            () => notify.warn('还没连上重启后的服务，稍等几秒刷新页面'),
          )
        }, 4000)
      },
      '会先停掉正在运行的直播程序，再用当前配置重新拉起 webui；没点「保存配置」的改动会全部丢失。',
    )

  const openRunLog = async () => {
    try {
      const resp = await api.runLog()
      if (resp.code === 200) setRunLog({ title: resp.title, note: resp.note, lines: resp.lines })
    } catch {
      notify.err('运行日志拉取失败')
    }
  }

  return (
    <>
      <div className="fixed bottom-3 right-3 z-50 flex flex-col items-end gap-2">
        <div className="flex items-center gap-2.5">
          <button className={PILL} style={{ color: dirty ? 'var(--warn)' : 'var(--ok)' }} onClick={() => setShowDirty(true)} title="点开看哪些项还没保存">
            {dirty ? `● ${changes.length} 项未保存` : '● 配置已保存'}
          </button>
          <button
            className={PILL}
            style={{ color: running ? 'var(--ok)' : 'var(--ink-mut)' }}
            onClick={() => jump('overview', {})}
            title="到总览页看开播就绪度"
          >
            {running ? '● 直播程序运行中' : '○ 直播程序未运行'}
          </button>
        </div>

        {open && (
          <div className="flex max-w-[92vw] flex-wrap justify-end gap-1.5">
            <DockButton label="保存配置" primary disabled={busy} title="保存 webui 的配置到本地文件，有些配置保存后需要重启生效" onClick={() => void handleSave()} />
            <DockButton label="一键运行" disabled={busy} title="运行 main.py" onClick={() => void run()} />
            <DockButton label="停止运行" disabled={busy} title="停止运行 main.py" onClick={stop} />
            <DockButton label="运行日志" title="看今天的日志末尾 400 行；日志文件在 log/ 下，按大小滚动" onClick={() => void openRunLog()} />
            <DockButton label="重启" title="停止运行 main.py 并重启 webui" onClick={restart} />
          </div>
        )}

        <div className="flex gap-2">
          <button className={PILL} onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} title="平滑滚动到页面顶部">
            ↑
          </button>
          <button
            className={`${PILL} font-medium`}
            style={{ color: 'var(--accent)' }}
            onClick={() => setOpen((v) => !v)}
          >
            {open ? '收起' : '操作'}
          </button>
        </div>
      </div>

      {showDirty && <DirtyListDialog changes={changes} onClose={() => setShowDirty(false)} />}
      {runLog && <RunLogDialog data={runLog} onClose={() => setRunLog(null)} onRefresh={openRunLog} />}
    </>
  )
}

function DockButton({ label, onClick, title, primary, disabled }: { label: string; onClick: () => void; title: string; primary?: boolean; disabled?: boolean }) {
  return (
    <button
      className={`rounded-lg px-3 py-1.5 text-[13px] font-medium shadow-sm ring-1 transition hover:opacity-90 disabled:opacity-50 ${
        primary ? 'text-white ring-transparent' : 'bg-white text-[var(--ink)] ring-slate-300'
      }`}
      style={primary ? { background: 'var(--accent)' } : undefined}
      title={title}
      disabled={disabled}
      onClick={onClick}
    >
      {label}
    </button>
  )
}

function DirtyListDialog({ changes, onClose }: { changes: ReturnType<typeof useChanges>; onClose: () => void }) {
  const jump = useJumpStore((s) => s.jump)
  return (
    <div className="dialog-backdrop" onMouseDown={onClose}>
      <div className="card-surface flex max-h-[72vh] w-full max-w-[720px] flex-col overflow-hidden p-0" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-3">
          <h3 className="text-[15px] font-semibold">未保存的改动</h3>
          <span className="text-xs text-[var(--ink-mut)]">{changes.length} 项 · 没保存就刷新或关闭会全部丢失</span>
        </div>
        <div className="overflow-y-auto px-5 py-3">
          {changes.length === 0 && <p className="py-6 text-center text-[13px] text-[var(--ink-mut)]">都保存好了，没有未保存的改动</p>}
          {changes.map((c, i) => {
            const entry = entryForPath(c.path)
            return (
              <div key={i} className="flex items-center gap-3 border-b border-slate-100 py-2 last:border-b-0">
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] font-medium">
                    {entry ? entry.field.label : c.path.join('.')}
                    <span className="ml-2 text-xs font-normal text-[var(--ink-mut)]">
                      {entry ? `${entry.workspaceTitle} · ${entry.sectionTitle}` : '（不在已迁移的表单里）'}
                    </span>
                  </div>
                  <div className="mt-0.5 truncate text-xs text-[var(--ink-mut)]">
                    {formatValue(c.before)} → {formatValue(c.value)}
                  </div>
                </div>
                {entry && (
                  <button className="text-[13px] font-medium hover:underline" style={{ color: 'var(--accent)' }} onClick={() => { onClose(); jump(entry.workspaceId, { fieldId: entry.fieldId }) }}>
                    去改
                  </button>
                )}
              </div>
            )
          })}
        </div>
        <div className="flex justify-end border-t border-slate-100 px-5 py-3">
          <button className="rounded-lg border border-slate-300 px-4 py-1.5 text-[13px] hover:bg-slate-50" onClick={onClose}>
            关闭
          </button>
        </div>
      </div>
    </div>
  )
}

function RunLogDialog({ data, onClose, onRefresh }: { data: { title: string; note: string; lines: string[] }; onClose: () => void; onRefresh: () => Promise<void> }) {
  const [refreshing, setRefreshing] = useState(false)
  useEffect(() => {
    // 打开期间每 5 秒自动刷一次，出问题能直接看着日志定位
    const timer = setInterval(() => void onRefresh(), 5000)
    return () => clearInterval(timer)
  }, [onRefresh])
  return (
    <div className="dialog-backdrop" onMouseDown={onClose}>
      <div className="card-surface flex max-h-[76vh] w-full max-w-[1000px] flex-col overflow-hidden p-0" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-3">
          <h3 className="text-[15px] font-semibold">{data.title}</h3>
          <span className="text-xs text-[var(--ink-mut)]">{data.note}</span>
          <div className="flex-1" />
          <button
            className="rounded-md border border-slate-300 px-3 py-1 text-xs hover:bg-slate-50 disabled:opacity-50"
            disabled={refreshing}
            onClick={async () => {
              setRefreshing(true)
              await onRefresh()
              setRefreshing(false)
            }}
          >
            刷新
          </button>
          <button className="rounded-md border border-slate-300 px-3 py-1 text-xs hover:bg-slate-50" onClick={onClose}>
            关闭
          </button>
        </div>
        <pre className="overflow-auto whitespace-pre-wrap break-all px-5 py-3 text-xs leading-relaxed">
          {data.lines.join('\n') || '（这个日志文件目前是空的）'}
        </pre>
      </div>
    </div>
  )
}
