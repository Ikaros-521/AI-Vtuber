/** 全局浮层：toast 与确认框。 */
import { useConfirmStore, useToastStore } from '../state/ui'

const TOAST_STYLE: Record<string, string> = {
  info: 'bg-slate-800 text-white',
  positive: 'bg-emerald-600 text-white',
  warning: 'bg-amber-600 text-white',
  negative: 'bg-red-600 text-white',
}

export function ToastHost() {
  const toasts = useToastStore((s) => s.toasts)
  const dismiss = useToastStore((s) => s.dismiss)
  return (
    <div className="pointer-events-none fixed left-1/2 top-3 z-[70] flex w-full max-w-[560px] -translate-x-1/2 flex-col items-center gap-2 px-4">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`pointer-events-auto w-full cursor-pointer rounded-lg px-4 py-2.5 text-[13px] leading-relaxed shadow-lg ${TOAST_STYLE[t.kind]}`}
          onClick={() => dismiss(t.id)}
        >
          {t.message}
        </div>
      ))}
    </div>
  )
}

export function ConfirmHost() {
  const current = useConfirmStore((s) => s.current)
  const close = useConfirmStore((s) => s.close)
  if (!current) return null
  return (
    <div className="dialog-backdrop !items-center !pt-0" onMouseDown={close}>
      <div className="card-surface w-full max-w-[420px] p-5" onMouseDown={(e) => e.stopPropagation()}>
        <h3 className="text-[15px] font-semibold">{current.title}</h3>
        {current.body && <p className="mt-2 text-[13px] leading-relaxed text-[var(--ink-mut)]">{current.body}</p>}
        <div className="mt-4 flex justify-end gap-2">
          <button className="rounded-lg border border-slate-300 px-4 py-1.5 text-[13px] hover:bg-slate-50" onClick={close}>
            取消
          </button>
          <button
            className="rounded-lg px-4 py-1.5 text-[13px] font-medium text-white"
            style={{ background: 'var(--accent)' }}
            onClick={() => {
              close()
              current.onOk()
            }}
          >
            确认
          </button>
        </div>
      </div>
    </div>
  )
}
