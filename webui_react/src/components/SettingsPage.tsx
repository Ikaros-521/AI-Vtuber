/** 基础设置页：四步信号链（直播间→AI大脑→声音→形象）+ 选卡墙「选中即所见」。

 * 有 pickKey 的步骤：provider 区块收敛为选卡墙上的一张卡，只有当前选中值的区块
 * 渲染完整表单；无 pickValue 的普通区块照常平铺。brain/voice 的多组用页签切换。
 */
import { useEffect, useState } from 'react'
import { getByPath, type JsonObject } from '../lib/path'
import { pickMatches, sectionVisible, SETTINGS_STEPS } from '../schema'
import { useConfigStore } from '../state/configStore'
import { notify, useJumpStore } from '../state/ui'
import type { Section, Workspace } from '../schema/types'
import { SectionCard } from './SectionCard'
import { JumpFlash } from './WorkspacePage'

const STEP_HINTS: Record<string, string> = {
  platform: '弹幕从哪个平台来',
  brain: '谁来理解弹幕、组织语言',
  voice: '用什么嗓门说话、怎么听见你',
  body: '画面上是谁',
}

export function SettingsPage({ step, onStep }: { step: string; onStep: (s: string) => void }) {
  const draft = useConfigStore((s) => s.draft)
  const setValue = useConfigStore((s) => s.setValue)
  const jumpTarget = useJumpStore((s) => s.target)

  const ws = SETTINGS_STEPS.find((w) => w.id === step) ?? SETTINGS_STEPS[0]

  // 跳转目标到达时切一次步骤（目标是一次性消费的，AppShell 路由完即清空，
  // 不会常驻渲染期顶掉用户对步骤条的手动点击）
  useEffect(() => {
    if (!jumpTarget) return
    if (SETTINGS_STEPS.some((w) => w.id === jumpTarget.workspace) && jumpTarget.workspace !== step) {
      onStep(jumpTarget.workspace)
    }
    // 只依赖跳转目标：onStep 是内联箭头函数，进依赖会每帧触发
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jumpTarget])

  // 各步骤的页签状态（大脑：模型接入/记忆与模板/快捷问答；声音：说话/听话/变声）
  const [tabOf, setTabOf] = useState<Record<string, number>>({})
  const tab = Math.min(tabOf[ws.id] ?? 0, Math.max(ws.groups.length - 1, 0))
  const group = ws.groups[tab] ?? ws.groups[0]

  if (!draft) return null
  const currentValue = ws.pick ? getByPath(draft, ws.pick.key) : undefined

  const pickSections = ws.groups[0]?.sections.filter((s) => s.pickValue !== undefined) ?? []
  const groupNormal = group.sections.filter((s) => s.pickValue === undefined)
  const isPickGroup = group === ws.groups[0] && pickSections.length > 0
  const selected = pickSections.find((s) => pickMatches(s, currentValue))

  const pickCard = (value: string) => {
    if (String(currentValue ?? '') === value) return
    if (!ws.pick) return
    setValue(ws.pick.key, value)
    notify.info(`已切换为「${ws.pick.options[value] ?? value}」· 记得保存`)
  }

  return (
    <div>
      <JumpFlash workspaceId={ws.id} />

      {/* 步骤条 */}
      <div className="mb-4 flex flex-wrap items-center gap-1.5">
        {SETTINGS_STEPS.map((w, i) => {
          const on = w.id === ws.id
          return (
            <div key={w.id} className="flex items-center gap-1.5">
              {i > 0 && <span className="mx-1 h-px w-5 bg-slate-300" aria-hidden />}
              <button
                className={`flex items-center gap-2 rounded-lg px-2.5 py-1.5 text-[13px] transition ${on ? 'font-semibold' : 'text-[var(--ink-mut)] hover:bg-slate-100'}`}
                style={on ? { background: 'var(--accent)' } : undefined}
                onClick={() => onStep(w.id)}
              >
                <span
                  className="flex h-5 w-5 items-center justify-center rounded-full border text-[11px] font-bold"
                  style={on ? { borderColor: '#fff' } : { borderColor: '#cbd5e1', color: 'var(--ink-mut)' }}
                >
                  {i + 1}
                </span>
                <span style={on ? { color: '#fff' } : undefined}>{w.title}</span>
              </button>
            </div>
          )
        })}
        <span className="ml-2 text-xs text-[var(--ink-mut)]">{STEP_HINTS[ws.id] ?? ws.title}</span>
      </div>

      {/* 组页签（多组步骤才有） */}
      {ws.groups.length > 1 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {ws.groups.map((g, i) => (
            <button
              key={g.title}
              className={`rounded-full px-3.5 py-1 text-[12.5px] transition ${i === tab ? 'font-semibold text-white' : 'text-[var(--ink-mut)] ring-1 ring-slate-300 hover:text-[var(--accent)]'}`}
              style={i === tab ? { background: 'var(--ink)' } : undefined}
              onClick={() => setTabOf({ ...tabOf, [ws.id]: i })}
            >
              {g.title}
            </button>
          ))}
        </div>
      )}

      <div className="flex flex-col gap-4">
        {/* 组内普通区块先渲染（直播间号 / TTS调试 / Live2D / 音频播放…） */}
        {groupNormal.filter((s) => sectionVisible(s, draft)).map((s) => (
          <SectionCard key={s.id} section={s} workspaceId={ws.id} />
        ))}

        {/* 选卡墙 + 选中者的表单 */}
        {isPickGroup && ws.pick && (
          <>
            <PickWall
              title={ws.title}
              pick={ws.pick}
              pickSections={pickSections}
              currentValue={currentValue}
              draft={draft}
              onPick={pickCard}
            />
            {selected ? (
              <SectionCard section={selected} workspaceId={ws.id} />
            ) : (
              <NoFormNote ws={ws} value={String(currentValue ?? '')} />
            )}
          </>
        )}
      </div>
    </div>
  )
}

/** 选卡墙：N 选 1 的服务只显示卡片，不渲染表单。 */
function PickWall({
  title,
  pick,
  pickSections,
  currentValue,
  draft,
  onPick,
}: {
  title: string
  pick: NonNullable<Workspace['pick']>
  pickSections: Section[]
  currentValue: unknown
  draft: JsonObject
  onPick: (v: string) => void
}) {
  const entries: { value: string; label: string; section?: Section }[] = []
  for (const [value, label] of Object.entries(pick.options)) {
    entries.push({ value, label, section: pickSections.find((s) => pickMatches(s, value)) })
  }
  // 配置里的未知值兜底成一张卡（老平台名这类），不让当前选择「消失」
  const cur = String(currentValue ?? '')
  if (cur && !entries.some((e) => e.value === cur)) {
    const section = pickSections.find((s) => pickMatches(s, cur))
    entries.push({ value: cur, label: section?.title ?? `${cur}（配置里的当前值）`, section })
  }

  // 卡片名：一个区块只被一个选项引用时用区块标题（更友好，如 my_wenxinworkshop → 千帆大模型）；
  // 多个选项共享同一区块时退回选项标签（哔哩哔哩 / 哔哩哔哩2 不能重名）
  const sectionUse = new Map<string, number>()
  for (const e of entries) if (e.section) sectionUse.set(e.section.id, (sectionUse.get(e.section.id) ?? 0) + 1)
  const nameOf = (e: { label: string; section?: Section }) =>
    e.section && sectionUse.get(e.section.id) === 1 ? e.section.title : e.label

  const visible = entries.filter((e) => !e.section || sectionVisible(e.section, draft))

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-baseline gap-2">
        <h2 className="text-[14.5px] font-bold">选一个{title}服务</h2>
        <span className="text-xs text-[var(--ink-mut)]">同一时刻只有一个生效，选中谁就只配谁</span>
      </div>
      <div className="grid grid-cols-2 gap-2.5 md:grid-cols-3 xl:grid-cols-4">
        {visible.map((e) => {
          const on = String(currentValue ?? '') === e.value
          return (
            <button
              key={e.value}
              className={`relative rounded-xl border p-3 text-left transition ${on ? '' : 'bg-white hover:border-slate-400'}`}
              style={on
                ? { borderColor: 'var(--accent)', boxShadow: '0 0 0 3px color-mix(in srgb, var(--accent) 15%, transparent)' }
                : { borderColor: '#e4e7ec' }}
              onClick={() => onPick(e.value)}
            >
              <div className="pr-6 text-[13.5px] font-semibold">{nameOf(e)}</div>
              {e.section?.desc && <div className="mt-1 line-clamp-2 text-xs leading-relaxed text-[var(--ink-mut)]">{e.section.desc}</div>}
              {e.section?.tags && e.section.tags.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {e.section.tags.map((t) => (
                    <span key={t} className="rounded border border-slate-200 bg-slate-50 px-1.5 py-px text-[11px] text-[var(--ink-mut)]">{t}</span>
                  ))}
                </div>
              )}
              <span
                className="absolute right-2.5 top-2.5 flex items-center justify-center rounded-full border-2"
                style={{
                  width: 18, height: 18,
                  borderColor: on ? 'var(--accent)' : '#cbd5e1',
                  background: on ? 'var(--accent)' : '#fff',
                }}
                aria-hidden
              >
                {on && (
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round">
                    <path d="M4.5 12.5l5 5L19.5 7" />
                  </svg>
                )}
              </span>
            </button>
          )
        })}
      </div>
    </div>
  )
}

/** 选中值没有对应表单（none/复读机/聊天模式/其他外置/空值）时的说明卡。 */
function NoFormNote({ ws, value }: { ws: Workspace; value: string }) {
  const label = ws.pick?.options[value] ?? value
  const notes: Record<string, string> = {
    none: '当前不启用这项能力，没有需要填的配置。想用的时候从上面挑一家就行。',
    reread: '复读机模式：不接大模型，直接复读弹幕。想让她「会聊天」，从上面挑一家大脑。',
    talk: '聊天模式：不接直播平台，直接在开播台的「聊天测试」里对话调试。',
    其他: '画面由外部窗口负责，本程序只负责声音。想给她一张脸，用上面的 Live2D（推荐）或其他驱动。',
  }
  // 空态引导：还没选时给一句推荐，不让表单区干巴巴
  const emptyGuide: Record<string, string> = {
    platform: '还没选平台——不知道选什么就「哔哩哔哩 2」，扫码即接；只想先试就「聊天模式」。',
    brain: '还没选大脑——OpenAI 兼容接口最通用（DeepSeek / 中转站都算），通义千问有免费额度。',
    voice: '还没选声音——Edge-TTS 免费且无需任何 Key，先用它跑起来，以后随时换。',
    body: '还没选形象——Live2D（推荐）模型放本地就能用；只要声音就选「其他（外置）」。',
  }
  return (
    <div className="card-surface px-5 py-4">
      <div className="text-[14px] font-semibold">{value ? `当前：${label}` : '还没选择'}</div>
      <p className="mt-1 text-[13px] leading-relaxed text-[var(--ink-mut)]">
        {value ? (notes[value] ?? '当前选择没有额外的表单要填。') : (emptyGuide[ws.id] ?? '从上面挑一个就能开始配置。')}
      </p>
    </div>
  )
}
