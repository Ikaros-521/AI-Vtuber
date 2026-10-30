/** 区块卡片：标题 + 说明 + 字段行 + 高级参数折叠 + 嵌套子卡；custom 区块分发到专用组件。 */
import { useState } from 'react'
import { useConfigStore } from '../state/configStore'
import { sectionVisible } from '../schema'
import { fieldIdOf, type Section } from '../schema/types'
import { FieldControl } from './FieldControl'
import { DocsCard, SectionToggleWall } from './SystemExtras'
import { DataAnalysisCard } from './DataAnalysisCard'
import { TtsTester } from './VoiceExtras'
import { PriorityList } from './PriorityList'

export function SectionCard({
  section,
  workspaceId,
  nested = false,
  bare = false,
}: {
  section: Section
  workspaceId: string
  nested?: boolean
  /** 玩法库卡片：标题/说明由外层开关卡承载，这里只渲染表单体（不带卡片外壳） */
  bare?: boolean
}) {
  const draft = useConfigStore((s) => s.draft)
  if (!sectionVisible(section, draft)) return null

  if (section.custom === 'section-toggles') {
    return (
      <section data-section-id={`${workspaceId}__${section.id}`} className="card-surface p-5">
        <h3 className="text-[15px] font-semibold">{section.title}</h3>
        {section.desc && <p className="mt-1 text-xs leading-relaxed text-[var(--ink-mut)]">{section.desc}</p>}
        <div className="mt-3">
          <SectionToggleWall />
        </div>
      </section>
    )
  }
  if (section.custom === 'docs') {
    return (
      <section data-section-id={`${workspaceId}__${section.id}`}>
        <DocsCard />
      </section>
    )
  }
  if (section.custom === 'tts-tester' || section.custom === 'data-analysis') {
    return (
      <section data-section-id={`${workspaceId}__${section.id}`} className="card-surface p-5">
        <h3 className="text-[15px] font-semibold">{section.title}</h3>
        {section.desc && <p className="mt-1 text-xs leading-relaxed text-[var(--ink-mut)]">{section.desc}</p>}
        <div className="mt-3">
          {section.custom === 'tts-tester' ? <TtsTester /> : <DataAnalysisCard />}
        </div>
      </section>
    )
  }
  if (section.custom === 'priority-list') {
    return (
      <section
        data-section-id={`${workspaceId}__${section.id}`}
        className={nested ? 'rounded-xl border border-slate-200 bg-slate-50/70 p-4' : 'card-surface p-5'}
      >
        <h3 className={`font-semibold text-[var(--ink)] ${nested ? 'text-[14px]' : 'text-[15px]'}`}>{section.title}</h3>
        {section.desc && <p className="mt-1 text-xs leading-relaxed text-[var(--ink-mut)]">{section.desc}</p>}
        <div className="mt-3">
          <PriorityList />
        </div>
      </section>
    )
  }

  return (
    <section
      data-section-id={`${workspaceId}__${section.id}`}
      className={
        bare
          ? ''
          : nested
            ? 'rounded-xl border border-slate-200 bg-slate-50/70 p-4'
            : 'card-surface p-5'
      }
    >
      {!bare && (
        <>
          <h3 className={`font-semibold text-[var(--ink)] ${nested ? 'text-[14px]' : 'text-[15px]'}`}>{section.title}</h3>
          {section.desc && <p className="mt-1 text-xs leading-relaxed text-[var(--ink-mut)]">{section.desc}</p>}
        </>
      )}

      {(section.rows ?? []).map((row, i) => (
        <div key={i} className={`${bare || nested || i === 0 ? '' : 'mt-3'} flex flex-wrap gap-x-5 gap-y-4`}>
          {row.map((field, j) => (
            <FieldControl
              key={`${i}-${j}`}
              field={field}
              fieldId={fieldIdOf(workspaceId, section.id, field)}
            />
          ))}
        </div>
      ))}

      <AdvancedRows section={section} workspaceId={workspaceId} />

      {(section.cards ?? []).length > 0 && (
        <div className={`flex flex-col gap-4 ${(section.rows ?? []).length > 0 ? 'mt-4' : bare ? '' : 'mt-3'}`}>
          {(section.cards ?? []).map((card) => (
            <SectionCard key={card.id} section={card} workspaceId={workspaceId} nested={!bare} />
          ))}
        </div>
      )}
    </section>
  )
}

/** 高级参数：默认折叠（渐进披露），点开才渲染行。 */
function AdvancedRows({ section, workspaceId }: { section: Section; workspaceId: string }) {
  const [open, setOpen] = useState(false)
  if (!section.rowsAdvanced || section.rowsAdvanced.length === 0) return null
  return (
    <div className="mt-3 border-t border-dashed border-slate-200 pt-2">
      <button
        type="button"
        className="flex items-center gap-1.5 text-[13px] font-medium text-[var(--ink-mut)] transition hover:text-[var(--accent)]"
        onClick={() => setOpen(!open)}
      >
        <span className="inline-block transition-transform" style={{ transform: open ? 'rotate(180deg)' : 'none' }}>▾</span>
        高级参数
        <span className="text-xs font-normal">· 新手保持默认即可</span>
      </button>
      {open && (
        <div className="mt-2">
          {section.rowsAdvanced.map((row, i) => (
            <div key={i} className={`${i === 0 ? '' : 'mt-3'} flex flex-wrap gap-x-5 gap-y-4`}>
              {row.map((field, j) => (
                <FieldControl
                  key={`${i}-${j}`}
                  field={field}
                  fieldId={fieldIdOf(workspaceId, section.id, field)}
                />
              ))}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
