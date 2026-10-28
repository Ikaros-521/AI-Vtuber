/** 应用外壳：顶部导航（9 大工作区芯片）+ 页面内容 + 操作坞 + 全局浮层。

 * ?tab= 深链与 v2 行为一致：切页写地址栏，刷新/分享能回到原来那一页。
 */
import { useEffect, useState } from 'react'
import { WORKSPACES } from '../schema'
import { useChanges } from '../state/configStore'
import { useOpsStore } from '../state/opsStore'
import { useJumpStore } from '../state/ui'
import { ChatPage } from './ChatPage'
import { OpsDock } from './OpsDock'
import { OverviewPage } from './OverviewPage'
import { SearchDialog } from './SearchDialog'
import { ConfirmHost, ToastHost } from './Overlays'
import { WorkspacePage } from './WorkspacePage'

function initialWorkspaceId(): string {
  const tab = new URLSearchParams(window.location.search).get('tab')
  const hit = WORKSPACES.find((w) => w.title === tab)
  return hit ? hit.id : 'overview'
}

export function AppShell() {
  const refreshOps = useOpsStore((s) => s.refresh)
  const jumpTarget = useJumpStore((s) => s.target)
  const changes = useChanges()

  const [workspaceId, setWorkspaceId] = useState(initialWorkspaceId)
  const [searchOpen, setSearchOpen] = useState(false)

  const workspace = WORKSPACES.find((w) => w.id === workspaceId) ?? WORKSPACES[0]

  // 运行态轮询：状态也会被 /sys_cmd 从别处改掉，只能轮询
  useEffect(() => {
    void refreshOps()
    const timer = setInterval(() => void refreshOps(), 2000)
    return () => clearInterval(timer)
  }, [refreshOps])

  // 跳转可能要求切页
  useEffect(() => {
    if (jumpTarget) setWorkspaceId((cur) => (cur === jumpTarget.workspace ? cur : jumpTarget.workspace))
  }, [jumpTarget])

  // ?tab= 深链同步
  useEffect(() => {
    const url = `?tab=${encodeURIComponent(workspace.title)}`
    window.history.replaceState(null, '', url)
    document.title = `${workspace.title} · AI Vtuber`
  }, [workspace.title])

  // Ctrl+K 搜索
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setSearchOpen(true)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  // 有未保存改动时拦一下关闭/刷新
  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (changes.length === 0) return
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => window.removeEventListener('beforeunload', onBeforeUnload)
  }, [changes.length])

  return (
    <div className="min-h-screen">
      {/* 顶部导航 */}
      <header className="sticky top-0 z-40 border-b border-slate-200/80 bg-white/95 backdrop-blur">
        <div className="mx-auto flex w-full max-w-[1180px] items-center gap-2 px-4 py-2.5">
          <span className="flex-none text-[15px] font-bold tracking-wide">AI&nbsp;Vtuber</span>
          {/* 窄屏单行横向滚动，不折行：换行会把导航挤成两层 */}
          <nav className="flex min-w-0 flex-1 items-center gap-1 overflow-x-auto py-0.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
            {WORKSPACES.map((w) => {
              const active = w.id === workspaceId
              return (
                <button
                  key={w.id}
                  onClick={() => setWorkspaceId(w.id)}
                  className={`flex-none rounded-md px-2.5 py-1 text-[13px] font-medium transition ${active ? 'text-white' : 'text-[var(--ink)] hover:bg-slate-100'}`}
                  style={active ? { background: 'var(--accent)' } : undefined}
                >
                  {w.title}
                </button>
              )
            })}
          </nav>
          <button
            className="flex flex-none items-center gap-1.5 rounded-md border border-slate-300 px-2.5 py-1 text-[13px] text-[var(--ink-mut)] hover:border-[var(--accent)] hover:text-[var(--accent)]"
            onClick={() => setSearchOpen(true)}
            title="Ctrl+K"
          >
            🔍 搜索配置项
          </button>
        </div>
      </header>

      {/* 页面内容 */}
      <main>
        {workspace.custom === 'overview' ? (
          <OverviewPage />
        ) : workspace.custom === 'chat' ? (
          <ChatPage />
        ) : (
          <WorkspacePage workspace={workspace} />
        )}
      </main>

      <OpsDock />
      <SearchDialog open={searchOpen} onClose={() => setSearchOpen(false)} />
      <ToastHost />
      <ConfirmHost />
    </div>
  )
}
