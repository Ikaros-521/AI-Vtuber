/** schema 驱动的工作区页面：吸顶区块索引 + 分组区块卡片 + 跳转闪烁。 */
import { useEffect } from 'react'
import { useConfigStore } from '../state/configStore'
import { useJumpStore } from '../state/ui'
import { sectionVisible } from '../schema'
import type { Workspace } from '../schema/types'
import { SectionCard } from './SectionCard'

/** 跳转落点：切页后等一帧 DOM，再滚动 + 描边闪烁。 */
export function JumpFlash({ workspaceId }: { workspaceId: string }) {
  const target = useJumpStore((s) => s.target)

  useEffect(() => {
    if (!target || target.workspace !== workspaceId) return
    const timer = setTimeout(() => {
      const el = target.fieldId
        ? document.querySelector(`[data-field-id="${CSS.escape(target.fieldId)}"]`)
        : target.sectionId
          ? document.querySelector(`[data-section-id="${CSS.escape(target.sectionId)}"]`)
          : null
      if (!el) return
      el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      const cls = target.fieldId ? 'field-flash' : 'section-flash'
      el.classList.remove(cls)
      // 强制 reflow，同名跳转连续两次也能重新触发动画
      void (el as HTMLElement).offsetWidth
      el.classList.add(cls)
      setTimeout(() => el.classList.remove(cls), 2300)
      const input = el.querySelector('input:not([type=checkbox]), textarea') as HTMLInputElement | HTMLTextAreaElement | null
      if (input) input.focus({ preventScroll: true })
    }, 80)
    return () => clearTimeout(timer)
  }, [target, workspaceId])

  return null
}

function StubCard({ workspace }: { workspace: Workspace }) {
  return (
    <div className="mx-auto max-w-[760px] px-4 py-10">
      <div className="card-surface p-8 text-center">
        <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-2xl">🚧</div>
        <h2 className="text-lg font-semibold">{workspace.title}</h2>
        <p className="mt-2 text-[13px] leading-relaxed text-[var(--ink-mut)]">
          这个工作区还在从 v2 迁移到 React 的路上，涉及的配置：
          <br />
          {workspace.stub}
        </p>
        <p className="mt-4 text-[13px] text-[var(--ink-mut)]">
          迁移完成前请继续用 v2 WebUI（<code className="rounded bg-slate-100 px-1.5 py-0.5">webui.py</code>）配置这部分内容，
          两边读写的是同一份 config.json。
        </p>
        <p className="mt-1 text-[13px] text-[var(--ink-mut)]">
          也可以先用本页顶部的「搜索配置项」搜一下——搜不到的就是还没迁。
        </p>
      </div>
    </div>
  )
}

export function WorkspacePage({ workspace }: { workspace: Workspace }) {
  const draft = useConfigStore((s) => s.draft)

  if (workspace.stub) return <StubCard workspace={workspace} />

  const groups = workspace.groups
    .map((g) => ({ ...g, sections: g.sections.filter((s) => sectionVisible(s, draft)) }))
    .filter((g) => g.sections.length > 0)

  return (
    <div className="mx-auto w-full max-w-[1180px] px-4 pb-28 pt-4">
      <JumpFlash workspaceId={workspace.id} />

      {/* 吸顶区块索引：让人先看得见这页有什么 */}
      {groups.some((g) => g.sections.length >= 2) && (
        <div className="sticky top-[57px] z-30 mb-4 flex flex-wrap items-center gap-x-1.5 gap-y-1.5 rounded-xl border border-slate-200/90 bg-white/95 px-3 py-2 shadow-sm backdrop-blur">
          <span className="mr-1 text-xs font-semibold text-[var(--ink-mut)]">本页区块</span>
          {groups.map((g) => (
            <span key={g.title} className="flex flex-wrap items-center gap-1.5">
              <span className="ml-1.5 rounded-full border border-slate-300 px-2 py-0.5 text-[11px] font-semibold text-[var(--ink)]">
                {g.title}
              </span>
              {g.sections.map((s) => (
                <button
                  key={s.id}
                  className="rounded-full bg-white px-2 py-0.5 text-xs text-[var(--ink-mut)] shadow-sm ring-1 ring-slate-200 transition hover:text-[var(--accent)] hover:ring-[var(--accent)]"
                  onClick={() => {
                    const el = document.querySelector(`[data-section-id="${CSS.escape(`${workspace.id}__${s.id}`)}"]`)
                    el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                    el?.classList.add('section-flash')
                    setTimeout(() => el?.classList.remove('section-flash'), 1900)
                  }}
                >
                  {s.title}
                </button>
              ))}
            </span>
          ))}
        </div>
      )}

      <div className="flex flex-col gap-5">
        {groups.map((g, gi) => (
          <div key={g.title} className="flex flex-col gap-4">
            {groups.length > 1 && (
              <div className="flex items-center gap-3 pt-1">
                <span className="rounded-md bg-slate-200/70 px-2.5 py-1 text-xs font-semibold tracking-wide text-[var(--ink)]">
                  {g.title}
                </span>
                <span className="h-px flex-1 bg-slate-200" />
                {gi === 0 && <span className="text-xs text-[var(--ink-mut)]">{workspace.title}</span>}
              </div>
            )}
            {g.sections.map((s) => (
              <SectionCard key={s.id} section={s} workspaceId={workspace.id} />
            ))}
          </div>
        ))}
      </div>
    </div>
  )
}
