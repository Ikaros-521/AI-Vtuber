import { useEffect } from 'react'
import { useConfigStore } from './state/configStore'
import { AppShell } from './components/AppShell'

export default function App() {
  const status = useConfigStore((s) => s.status)
  const loadError = useConfigStore((s) => s.loadError)
  const fetchConfig = useConfigStore((s) => s.fetchConfig)

  useEffect(() => {
    void fetchConfig()
  }, [fetchConfig])

  if (status === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-[14px] text-[var(--ink-mut)]">正在加载配置…</p>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="flex min-h-screen items-center justify-center px-6">
        <div className="card-surface max-w-[480px] p-6 text-center">
          <h1 className="text-lg font-semibold">配置加载失败</h1>
          <p className="mt-2 text-[13px] leading-relaxed text-[var(--ink-mut)]">{loadError}</p>
          <p className="mt-3 text-[13px] text-[var(--ink-mut)]">
            请确认 webui_server 已启动：<code className="rounded bg-slate-100 px-1.5 py-0.5">python -m webui_server</code>
          </p>
          <button
            className="mt-4 rounded-lg px-4 py-1.5 text-[13px] font-medium text-white"
            style={{ background: 'var(--accent)' }}
            onClick={() => void fetchConfig()}
          >
            重试
          </button>
        </div>
      </div>
    )
  }

  return <AppShell />
}
