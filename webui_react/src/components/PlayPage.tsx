/** 玩法库：开关卡片网格。masterKey 指到的布尔键就是玩法总开关，
 * 开了才在卡片下方展开配置（SectionCard 无头渲染）；没配 masterKey 的
 * 区块（定时任务/联动程序/串口这类「列表型」）始终展开配置。
 */
import { getByPath } from '../lib/path'
import { sectionVisible } from '../schema'
import { useConfigStore } from '../state/configStore'
import { notify } from '../state/ui'
import type { Section, Workspace } from '../schema/types'
import { SectionCard } from './SectionCard'
import { JumpFlash } from './WorkspacePage'

/** 玩法卡片图标（Section.icon 名称 → SVG path），17px 线性描边。 */
const ICON_PATHS: Record<string, string> = {
  music: 'M9 18a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0zM20 16a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0zM9 18V6l11-2v12',
  card: 'M3 6h18v12H3zM3 10h18M7 14h4',
  wand: 'M5 19L17 7M15 5l1-3 1 3 3 1-3 1-1 3-1-3-3-1zM4 8l.6-1.8L6.4 5.6 4.6 5 4 3.2 3.4 5 1.6 5.6l1.8.6z',
  clockw: 'M12 4a8 8 0 108 8M12 8v4l3 2M12 2v2',
  book: 'M5 4h6a3 3 0 013 3v13a2.5 2.5 0 00-2.5-2H5zM19 4h-5v13h5z',
  person: 'M12 4a3.5 3.5 0 100 7 3.5 3.5 0 000-7zM5 20c1-4 3.5-6 7-6s6 2 7 6',
  plug: 'M9 3v5M15 3v5M7 8h10v3a5 5 0 01-10 0zM12 16v5',
  globe: 'M12 3a9 9 0 100 18 9 9 0 000-18zM3.6 9h16.8M3.6 15h16.8M12 3a14 14 0 000 18M12 3a14 14 0 010 18',
  cam: 'M3 8h4l2-3h6l2 3h4v12H3zM12 17a3.5 3.5 0 100-7 3.5 3.5 0 000 7z',
  chip: 'M8 8h8v8H8zM4 10V8h4M4 14v2h4M20 10V8h-4M20 14v2h-4M10 4V6M14 4V6M10 20v-2M14 20v-2',
  puzzle: 'M10 4h4v2a2 2 0 104 0h2v4h-2a2 2 0 100 4h2v4h-4v-2a2 2 0 10-4 0v2H6v-4h2a2 2 0 100-4H6V6h4z',
  radio: 'M12 8a4 4 0 100 8 4 4 0 000-8zM4.9 4.9l2 2M17.1 4.9l-2 2M12 2v2M12 20v2M4.9 19.1l2-2M17.1 19.1l-2-2',
  gear: 'M12 9a3 3 0 100 6 3 3 0 000-6zM12 2v3M12 19v3M4.2 4.2l2.1 2.1M17.7 17.7l2.1 2.1M2 12h3M19 12h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1',
}

function SecIcon({ name, size = 17 }: { name: string; size?: number }) {
  const d = ICON_PATHS[name]
  if (!d) return null
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" style={{ flex: 'none' }}>
      <path d={d} />
    </svg>
  )
}

export function PlayPage({ workspace }: { workspace: Workspace }) {
  const draft = useConfigStore((s) => s.draft)
  const setValue = useConfigStore((s) => s.setValue)
  if (!draft) return null

  const groups = workspace.groups
    .map((g) => ({ ...g, sections: g.sections.filter((s) => sectionVisible(s, draft)) }))
    .filter((g) => g.sections.length > 0)
  const onCount = groups.flatMap((g) => g.sections).filter((s) => s.masterKey && Boolean(getByPath(draft, s.masterKey))).length

  return (
    <div className="flex flex-col gap-5">
      <JumpFlash workspaceId={workspace.id} />
      <div className="flex items-baseline gap-3">
        <h2 className="text-[14.5px] font-bold">已启用 {onCount} 个玩法</h2>
        <span className="text-xs text-[var(--ink-mut)]">开了开关才会生效；关掉只是不参与运行，配置都还留着</span>
      </div>

      {groups.map((g) => (
        <div key={g.title}>
          <div className="mb-2.5 flex items-baseline gap-3">
            <h3 className="text-[14px] font-bold">{g.title}</h3>
            <span className="h-px flex-1 bg-slate-200" />
          </div>
          <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
            {g.sections.map((s) => (
              <PlayCard key={s.id} section={s} workspaceId={workspace.id} draft={draft} setValue={setValue} />
            ))}
          </div>
        </div>
      ))}
    </div>
  )
}

function PlayCard({
  section,
  workspaceId,
  draft,
  setValue,
}: {
  section: Section
  workspaceId: string
  draft: ReturnType<typeof useConfigStore.getState>['draft']
  setValue: ReturnType<typeof useConfigStore.getState>['setValue']
}) {
  const on = section.masterKey ? Boolean(getByPath(draft, section.masterKey)) : false

  const toggle = (next: boolean) => {
    if (!section.masterKey) return
    setValue(section.masterKey, next)
    notify.info(`「${section.title}」已${next ? '开启' : '关闭'} · 记得保存`)
  }

  return (
    <div
      className="card-surface p-4 transition"
      style={on ? { borderColor: 'color-mix(in srgb, var(--accent) 45%, #e4e7ec)' } : undefined}
    >
      <div className="flex items-center gap-2.5">
        {section.icon && (
          <span style={{ color: on ? 'var(--accent)' : 'var(--ink-mut)' }}>
            <SecIcon name={section.icon} />
          </span>
        )}
        <span className="text-[14px] font-semibold">{section.title}</span>
        {section.masterKey ? (
          <label className="switch ml-auto">
            <input type="checkbox" checked={on} onChange={(e) => toggle(e.target.checked)} />
            <span className="track" />
          </label>
        ) : (
          <span className="ml-auto rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-[var(--ink-mut)]">列表配置</span>
        )}
      </div>
      {section.desc && <p className="mt-1 text-xs leading-relaxed text-[var(--ink-mut)]">{section.desc}</p>}

      <div className="mt-3 border-t border-dashed border-slate-200 pt-3">
        {on || !section.masterKey ? (
          <SectionCard section={section} workspaceId={workspaceId} bare />
        ) : (
          <p className="py-1 text-xs text-[var(--ink-mut)]">开启开关后展开配置。</p>
        )}
      </div>
    </div>
  )
}
