/** 区块卡片：标题 + 说明 + 字段行 + 嵌套子卡；custom 区块分发到专用组件。 */
import { useConfigStore } from '../state/configStore'
import { sectionVisible } from '../schema'
import { fieldIdOf, type Section } from '../schema/types'
import { FieldControl } from './FieldControl'
import { DocsCard, SectionToggleWall } from './SystemExtras'
import { DataAnalysisCard } from './DataAnalysisCard'
import { TtsTester } from './VoiceExtras'

export function SectionCard({
  section,
  workspaceId,
  nested = false,
}: {
  section: Section
  workspaceId: string
  nested?: boolean
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

  return (
    <section
      data-section-id={`${workspaceId}__${section.id}`}
      className={
        nested
          ? 'rounded-xl border border-slate-200 bg-slate-50/70 p-4'
          : 'card-surface p-5'
      }
    >
      <h3 className={`font-semibold text-[var(--ink)] ${nested ? 'text-[14px]' : 'text-[15px]'}`}>{section.title}</h3>
      {section.desc && <p className="mt-1 text-xs leading-relaxed text-[var(--ink-mut)]">{section.desc}</p>}

      {(section.rows ?? []).map((row, i) => (
        <div key={i} className="mt-3 flex flex-wrap gap-x-5 gap-y-4">
          {row.map((field, j) => (
            <FieldControl
              key={`${i}-${j}`}
              field={field}
              fieldId={fieldIdOf(workspaceId, section.id, field)}
            />
          ))}
        </div>
      ))}

      {(section.cards ?? []).length > 0 && (
        <div className={`flex flex-col gap-4 ${nested ? 'mt-3' : 'mt-4'}`}>
          {(section.cards ?? []).map((card) => (
            <SectionCard key={card.id} section={card} workspaceId={workspaceId} nested />
          ))}
        </div>
      )}
    </section>
  )
}
