/** 全局配置项搜索（Ctrl+K）：忽略分隔符匹配，名字命中排前。 */
import { useEffect, useMemo, useRef, useState } from 'react'
import { searchFields } from '../schema'
import { useJumpStore } from '../state/ui'

export function SearchDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const [query, setQuery] = useState('')
  const jump = useJumpStore((s) => s.jump)
  const inputRef = useRef<HTMLInputElement>(null)

  const results = useMemo(() => searchFields(query), [query])

  useEffect(() => {
    if (open) {
      setQuery('')
      setTimeout(() => inputRef.current?.focus(), 30)
    }
  }, [open])

  if (!open) return null

  const go = (workspaceId: string, fieldId: string) => {
    onClose()
    jump(workspaceId, { fieldId })
  }

  return (
    <div className="dialog-backdrop" onMouseDown={onClose}>
      <div className="card-surface w-full max-w-[640px] overflow-hidden p-0" onMouseDown={(e) => e.stopPropagation()}>
        <div className="flex items-center gap-2 border-b border-slate-100 px-4 py-3">
          <span className="text-[var(--ink-mut)]">🔍</span>
          <input
            ref={inputRef}
            className="w-full bg-transparent text-[14px] outline-none"
            placeholder="搜索配置项：名字、config 键、区块名…（忽略分隔符）"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && results.length > 0) {
                go(results[0].workspaceId, results[0].fieldId)
              }
              if (e.key === 'Escape') onClose()
            }}
          />
          <kbd className="rounded border border-slate-300 px-1.5 py-0.5 text-[11px] text-[var(--ink-mut)]">Esc</kbd>
        </div>
        <div className="max-h-[52vh] overflow-y-auto py-1">
          {query && results.length === 0 && (
            <p className="px-4 py-6 text-center text-[13px] text-[var(--ink-mut)]">
              没搜到。搜不到的就是还没迁移到 v3 的工作区，请先用 v2 WebUI 配置。
            </p>
          )}
          {results.map((r) => (
            <button
              key={r.fieldId}
              className="flex w-full items-center gap-3 px-4 py-2 text-left hover:bg-slate-50"
              onClick={() => go(r.workspaceId, r.fieldId)}
            >
              <div className="min-w-0 flex-1">
                <div className="text-[13px] font-medium">{r.field.label}</div>
                <div className="mt-0.5 text-xs text-[var(--ink-mut)]">
                  {r.workspaceTitle} · {r.sectionTitle} · {r.field.key.join('.')}
                </div>
              </div>
              <span className="flex-none rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-[var(--ink-mut)]">{r.workspaceTitle}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
