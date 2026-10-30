/** 从旧操作坞迁出的两个全局对话框：未保存清单 + 运行日志。 */
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { formatValue } from '../lib/path'
import { useChanges } from '../state/configStore'
import { entryForPath } from '../schema'
import { useJumpStore } from '../state/ui'

export function DirtyListDialog({ onClose }: { onClose: () => void }) {
  const changes = useChanges()
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

export function RunLogDialog({ onClose }: { onClose: () => void }) {
  const [data, setData] = useState<{ title: string; note: string; lines: string[] } | null>(null)

  const refresh = async () => {
    try {
      const resp = await api.runLog()
      if (resp.code === 200) setData({ title: resp.title, note: resp.note, lines: resp.lines })
    } catch {
      /* 拉取失败保留旧内容，下一轮再试 */
    }
  }

  useEffect(() => {
    void refresh()
    // 打开期间每 5 秒自动刷一次，出问题能直接看着日志定位
    const timer = setInterval(() => void refresh(), 5000)
    return () => clearInterval(timer)
  }, [])

  return (
    <div className="dialog-backdrop" onMouseDown={onClose}>
      <div className="card-surface flex max-h-[76vh] w-full max-w-[1000px] flex-col overflow-hidden p-0" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-3 border-b border-slate-100 px-5 py-3">
          <h3 className="text-[15px] font-semibold">{data?.title ?? '运行日志'}</h3>
          {data && <span className="text-xs text-[var(--ink-mut)]">{data.note}</span>}
          <div className="flex-1" />
          <button className="rounded-md border border-slate-300 px-3 py-1 text-xs hover:bg-slate-50" onClick={() => void refresh()}>
            刷新
          </button>
          <button className="rounded-md border border-slate-300 px-3 py-1 text-xs hover:bg-slate-50" onClick={onClose}>
            关闭
          </button>
        </div>
        <pre className="overflow-auto whitespace-pre-wrap break-all px-5 py-3 text-xs leading-relaxed">
          {data?.lines.join('\n') || '（这个日志文件目前是空的）'}
        </pre>
      </div>
    </div>
  )
}
