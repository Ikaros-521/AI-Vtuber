/** 应用外壳（重设计版）：左侧 5 项主导航 + 顶栏（保存/运行状态/搜索）+ 页面路由。

 * ?tab= 深链认新页面 id，也兼容老 v3 的九个工作区标题（resolveTab）。
 * 保存模型从右下角操作坞收编到顶栏常驻；运行控制在开播台。
 */
import { useEffect, useState } from 'react'
import { api } from '../api/client'
import { PAGES, resolveTab, WORKSPACES, SETTINGS_STEPS, precheckSettings, type PageId } from '../schema'
import { entryForPath } from '../schema'
import { useChanges, useConfigStore } from '../state/configStore'
import { useOpsStore } from '../state/opsStore'
import { notify, useConfirmStore, useJumpStore } from '../state/ui'
import { getByPath, type JsonObject } from '../lib/path'
import {
  AUDIO_SYNTHESIS_TYPE_OPTIONS,
  CHAT_TYPE_OPTIONS,
  PLATFORM_OPTIONS,
  VISUAL_BODY_OPTIONS,
} from '../schema/options'
import { ChatPage } from './ChatPage'
import { DashboardPage } from './DashboardPage'
import { DirtyListDialog } from './Dialogs'
import { PlayPage } from './PlayPage'
import { SearchDialog } from './SearchDialog'
import { ConfirmHost, ToastHost } from './Overlays'
import { SettingsPage } from './SettingsPage'
import { Wizard } from './Wizard'
import { WorkspacePage } from './WorkspacePage'

function initialRoute(): { page: PageId; step: string } {
  return resolveTab(new URLSearchParams(window.location.search).get('tab'))
}

/** 保存前给用户一条配置摘要（v2 save_config 的提示行为）。 */
function summarize(config: JsonObject): string {
  const platform = getByPath(config, ['platform']) as string | undefined
  const chatType = getByPath(config, ['chat_type']) as string | undefined
  const tts = getByPath(config, ['audio_synthesis_type']) as string | undefined
  const body = getByPath(config, ['visual_body']) as string | undefined
  return [
    `平台：${PLATFORM_OPTIONS[platform ?? ''] ?? platform}`,
    `大语言模型：${CHAT_TYPE_OPTIONS[chatType ?? ''] ?? chatType}`,
    `语音合成：${AUDIO_SYNTHESIS_TYPE_OPTIONS[tts ?? ''] ?? tts}`,
    `虚拟身体：${VISUAL_BODY_OPTIONS[body ?? ''] ?? body}`,
  ].join(' | ')
}

export function AppShell() {
  const refreshOps = useOpsStore((s) => s.refresh)
  const jumpTarget = useJumpStore((s) => s.target)
  const changes = useChanges()
  const save = useConfigStore((s) => s.save)
  const running = useOpsStore((s) => s.running)

  const [route, setRoute] = useState(initialRoute)
  const [searchOpen, setSearchOpen] = useState(false)
  const [dirtyOpen, setDirtyOpen] = useState(false)
  const [wizardOpen, setWizardOpen] = useState(false)
  const [navOpen, setNavOpen] = useState(false)
  const config = useConfigStore((s) => s.config)
  const ask = useConfirmStore((s) => s.ask)
  const [loginUser, setLoginUser] = useState<string | null>(null)

  // 首次使用向导：没配平台或大脑时自动弹一次；关掉后本会话不再打扰
  useEffect(() => {
    if (!config) return
    if (sessionStorage.getItem('aiv-wizard-seen')) return
    const platform = getByPath(config, ['platform'])
    const chatType = getByPath(config, ['chat_type'])
    if (!platform || !chatType || chatType === 'none') setWizardOpen(true)
  }, [config])

  // 登录功能启用时，侧栏底部给一个退出入口
  useEffect(() => {
    api.authStatus().then(
      (resp) => setLoginUser(resp.enabled && resp.authed ? (resp.username ?? '') : null),
      () => undefined,
    )
  }, [])

  const logout = async () => {
    await api.authLogout().catch(() => undefined)
    window.location.reload()
  }

  const page = PAGES.find((p) => p.id === route.page) ?? PAGES[0]

  // 运行态轮询：状态也会被 /sys_cmd 从别处改掉，只能轮询
  useEffect(() => {
    void refreshOps()
    const timer = setInterval(() => void refreshOps(), 2000)
    return () => clearInterval(timer)
  }, [refreshOps])

  // 跳转可能要求切页（搜索 / 未保存清单 / 开播台信号链共用）；
  // 路由完成后清掉目标——跳转是一次性指令，不能常驻渲染期和用户的手动切换打架
  useEffect(() => {
    if (!jumpTarget) return
    const wsId = jumpTarget.workspace
    if (SETTINGS_STEPS.some((w) => w.id === wsId)) {
      setRoute((cur) => (cur.page === 'settings' && cur.step === wsId ? cur : { page: 'settings', step: wsId }))
    } else if (WORKSPACES.some((w) => w.id === wsId)) {
      setRoute((cur) => (cur.page === wsId ? cur : { page: wsId as PageId, step: cur.step }))
    } else if (wsId === 'chat') {
      setRoute((cur) => (cur.page === 'chat' ? cur : { page: 'chat', step: cur.step }))
    } else if (wsId === 'overview' || wsId === 'dash') {
      setRoute((cur) => (cur.page === 'dash' ? cur : { page: 'dash', step: cur.step }))
    }
    useJumpStore.getState().clear()
  }, [jumpTarget])

  // ?tab= 深链同步
  useEffect(() => {
    const url = `?tab=${encodeURIComponent(route.page === 'settings' ? route.step : route.page)}`
    window.history.replaceState(null, '', url)
    document.title = `${route.page === 'settings' ? '基础设置 · ' + (SETTINGS_STEPS.find((w) => w.id === route.step)?.title ?? '') : page.title} · AI Vtuber`
  }, [route, page.title])

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

  const handleSave = async () => {
    if (changes.length === 0) {
      notify.info('没有未保存的改动')
      return
    }
    // 保存前预检：当前选中服务的必填型字段空着就提醒（可仍要保存，是提醒不是拦截）
    const issues = precheckSettings(useConfigStore.getState().draft ?? {})
    if (issues.length > 0) {
      const lines = issues.slice(0, 6).map((i) => `· ${i.stepTitle}：${i.sectionTitle} 的「${i.label}」`).join('\n')
      const more = issues.length > 6 ? `\n…等共 ${issues.length} 项` : ''
      const proceed = await new Promise<boolean>((res) => {
        ask(
          `保存前提醒：${issues.length} 项看起来还没填`,
          () => res(true),
          `${lines}${more}\n\n这些可能是开播要用的参数，空着容易运行报错。`,
          { onCancel: () => res(false), confirmLabel: '仍要保存', cancelLabel: '先去补' },
        )
      })
      if (!proceed) {
        const first = issues[0]
        useJumpStore.getState().jump(first.stepId, { fieldId: first.fieldId })
        return
      }
    }
    notify.info(summarize(useConfigStore.getState().draft ?? {}))
    const outcome = await save()
    if (outcome.ok) notify.ok(outcome.message)
    else {
      notify.err(outcome.message)
      // 校验失败：把用户带到那个框上
      if (outcome.path) {
        const entry = entryForPath(outcome.path)
        if (entry) useJumpStore.getState().jump(entry.workspaceId, { fieldId: entry.fieldId })
      }
    }
  }

  const modWorkspace = WORKSPACES.find((w) => w.id === 'mod')!
  const sysWorkspace = WORKSPACES.find((w) => w.id === 'sys')!
  const playWorkspace = WORKSPACES.find((w) => w.id === 'play')!

  const navGo = (p: PageId) => {
    setRoute((cur) => (cur.page === p ? cur : { page: p, step: cur.step }))
    setNavOpen(false)
  }

  return (
    <div className="flex min-h-screen">
      {/* 窄屏抽屉遮罩 */}
      {navOpen && (
        <div className="fixed inset-0 z-[45] bg-slate-900/40 md:hidden" onClick={() => setNavOpen(false)} aria-hidden />
      )}
      {/* 左侧主导航：桌面粘性全高贯通，窄屏抽屉化（修复窄于 768px 时完全没有导航的问题） */}
      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-[224px] flex-none flex-col border-r border-slate-200 bg-white transition-transform duration-200 md:sticky md:top-0 md:z-auto md:h-screen md:w-[204px] md:translate-x-0 ${
          navOpen ? 'translate-x-0 shadow-xl' : '-translate-x-full'
        }`}
      >
        <div className="flex items-center gap-2.5 px-[18px] pb-3.5 pt-[18px]">
          <span
            className="flex h-[30px] w-[30px] flex-none items-center justify-center rounded-[9px] text-sm font-bold text-white"
            style={{ background: 'var(--accent)' }}
          >
            ▶
          </span>
          <div className="min-w-0">
            <div className="text-[15px] font-bold">AI&nbsp;Vtuber</div>
          </div>
        </div>
        <nav className="flex flex-col gap-0.5 px-2.5">
          {PAGES.map((p) => {
            const active = route.page === p.id
            return (
              <button
                key={p.id}
                onClick={() => navGo(p.id)}
                className={`rounded-lg px-2.5 py-2 text-left text-[13.5px] transition ${active ? 'font-semibold' : 'text-[var(--ink-mut)] hover:bg-slate-100'}`}
                style={active ? { background: 'color-mix(in srgb, var(--accent) 12%, white)', color: 'var(--accent)' } : undefined}
              >
                {p.title}
              </button>
            )
          })}
        </nav>
        <div className="mt-auto flex flex-col gap-2 px-3.5 py-3.5">
          {loginUser !== null && (
            <button
              className="w-full rounded-lg border border-slate-300 px-2 py-1.5 text-xs text-[var(--ink-mut)] transition hover:border-red-400 hover:text-red-500"
              onClick={() => void logout()}
              title={`当前登录：${loginUser || '（未知）'}`}
            >
              退出登录
            </button>
          )}
          <p className="text-center text-[11px] leading-relaxed text-[var(--ink-mut)]">
            改版说明见<br />docs/redesign/
          </p>
        </div>
      </aside>

      {/* 主区 */}
      <div className="flex min-w-0 flex-1 flex-col">
        {/* 顶栏：页面标题 + 保存 + 运行状态 + 搜索 */}
        <header className="sticky top-0 z-40 flex h-[58px] items-center gap-3 border-b border-slate-200 bg-white/95 px-4 backdrop-blur md:px-6">
          {/* 窄屏汉堡：打开抽屉导航 */}
          <button
            className="flex h-8 w-8 flex-none items-center justify-center rounded-lg border border-slate-300 text-[15px] text-[var(--ink-mut)] transition hover:border-[var(--accent)] hover:text-[var(--accent)] md:hidden"
            onClick={() => setNavOpen(true)}
            aria-label="打开导航"
          >
            ☰
          </button>
          <div className="min-w-0">
            <div className="truncate text-[15px] font-bold">
              {route.page === 'settings'
                ? `基础设置 · ${SETTINGS_STEPS.find((w) => w.id === route.step)?.title ?? ''}`
                : page.title}
            </div>
            <div className="hidden truncate text-xs text-[var(--ink-mut)] sm:block">{page.sub}</div>
          </div>

          <div className="ml-auto flex flex-none items-center gap-2.5">
            <button
              className="flex items-center gap-2 rounded-lg border border-slate-300 px-2.5 py-1 text-[13px] text-[var(--ink-mut)] transition hover:border-[var(--accent)] hover:text-[var(--accent)]"
              onClick={() => setSearchOpen(true)}
              title="Ctrl+K"
            >
              🔍 搜索配置项
            </button>
            <button
              className="flex items-center gap-1.5 rounded-full border border-slate-200 px-2.5 py-1 text-xs transition hover:border-[var(--accent)]"
              style={{ color: running ? 'var(--ok)' : 'var(--ink-mut)' }}
              onClick={() => navGo('dash')}
              title="到开播台看运行状态"
            >
              <span className="inline-block h-[7px] w-[7px] rounded-full" style={{ background: running ? 'var(--ok)' : '#cbd5e1' }} />
              {running ? '运行中' : '未运行'}
            </button>
            {changes.length > 0 && (
              <button
                className="rounded-full px-2.5 py-1 text-xs font-semibold"
                style={{ background: 'color-mix(in srgb, var(--warn) 14%, white)', color: 'var(--warn)' }}
                onClick={() => setDirtyOpen(true)}
                title="点开看哪些项还没保存"
              >
                ● {changes.length} 项未保存
              </button>
            )}
            <button
              className="rounded-lg px-3.5 py-1.5 text-[13px] font-medium text-white transition hover:opacity-90"
              style={{ background: 'var(--accent)' }}
              onClick={() => void handleSave()}
            >
              保存
            </button>
          </div>
        </header>

        {/* 页面内容 */}
        <main className="mx-auto w-full max-w-[1240px] flex-1 px-6 pb-16 pt-5">
          {route.page === 'dash' && <DashboardPage onOpenChat={() => navGo('chat')} onOpenWizard={() => setWizardOpen(true)} />}
          {route.page === 'settings' && (
            <SettingsPage step={route.step} onStep={(s) => setRoute({ page: 'settings', step: s })} />
          )}
          {route.page === 'play' && <PlayPage workspace={playWorkspace} />}
          {route.page === 'mod' && <WorkspacePage workspace={modWorkspace} />}
          {route.page === 'sys' && <WorkspacePage workspace={sysWorkspace} />}
          {route.page === 'chat' && <ChatPage />}
        </main>
      </div>

      {wizardOpen && (
        <Wizard
          open={wizardOpen}
          onClose={() => {
            sessionStorage.setItem('aiv-wizard-seen', '1')
            setWizardOpen(false)
          }}
          onApply={(goSettings) => {
            sessionStorage.setItem('aiv-wizard-seen', '1')
            setWizardOpen(false)
            if (goSettings) setRoute({ page: 'settings', step: 'platform' })
          }}
        />
      )}
      <SearchDialog open={searchOpen} onClose={() => setSearchOpen(false)} />
      {dirtyOpen && <DirtyListDialog onClose={() => setDirtyOpen(false)} />}
      <ToastHost />
      <ConfirmHost />
    </div>
  )
}
