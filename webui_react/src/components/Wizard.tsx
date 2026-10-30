/** 首次使用向导：5 步选齐信号链（平台 → 大脑 → 声音 → 形象 → 完成）。

 * 只写草稿里的四个选择键（platform/chat_type/audio_synthesis_type/visual_body[+live2d]），
 * 必填参数（密钥/房间号）引导到基础设置补；写入后由顶栏「保存」落盘——和其他改动同一条链路。
 * 自动唤起：没配平台或大脑时进 AppShell 弹一次（关闭后本浏览器会话不再打扰）。
 */
import { useState } from 'react'
import { getByPath, type JsonObject } from '../lib/path'
import { useConfigStore } from '../state/configStore'
import { notify } from '../state/ui'
import { PLATFORM_OPTIONS, VISUAL_BODY_OPTIONS } from '../schema/options'
import { brainWorkspace } from '../schema/workspaces/brain'
import { voiceWorkspace } from '../schema/workspaces/voice'

const STEP_TITLES = ['直播平台', 'AI 大脑', '声音', '形象', '完成']

const PLATFORM_ORDER = ['bilibili2', 'bilibili', 'dy', 'live_monitor_assistant', 'wxlive', 'youtube', 'twitch', 'tiktok', 'talk']

const PLATFORM_NOTES: Record<string, string> = {
  bilibili2: '扫码即接，最省事',
  bilibili: 'cookie 方式，稳定性一般',
  dy: '配合抖音弹幕监听程序使用',
  live_monitor_assistant: '覆盖快手2 / 拼多多 / 斗鱼 / 淘宝 / 1688',
  talk: '先不接平台，配完直接聊天测试',
}

const GUIDES = [
  '弹幕从哪个平台来？拿不准就先选「聊天模式」，把主播调教好再上播。',
  '谁来理解弹幕、组织语言？选一家就行，以后随时换。',
  '她用什么嗓门说话？Edge-TTS 免费无需 Key，先用它跑起来。',
  '画面上是谁？Live2D 模型放本地就能用，不想用形象选「其他（外置）」。',
]

interface Selection {
  platform: string
  brain: string
  tts: string
  /** 'live2d' 是特殊项（visual_body=其他 + live2d.enable=true），其余为 visual_body 取值 */
  body: string
}

export function Wizard({ open, onClose, onApply }: { open: boolean; onClose: () => void; onApply: (goSettings: boolean) => void }) {
  const draft = useConfigStore((s) => s.draft)
  const setValue = useConfigStore((s) => s.setValue)
  const [step, setStep] = useState(0)

  // 挂载时（= 向导被打开时）从当前草稿取默认选择；此后只由用户交互改变
  const [sel, setSel] = useState<Selection>(() => {
    const d = useConfigStore.getState().draft as JsonObject | null
    const val = (key: string) => String((d && getByPath(d, [key])) ?? '')
    return {
      platform: val('platform') || 'bilibili2',
      brain: val('chat_type') || 'chatgpt',
      tts: val('audio_synthesis_type') || 'edge-tts',
      body: d && getByPath(d, ['live2d', 'enable']) ? 'live2d' : val('visual_body') || '其他',
    }
  })

  if (!open || !draft) return null

  const brainSections = brainWorkspace.groups[0].sections.filter((s) => s.pickValue !== undefined)
  const ttsSections = voiceWorkspace.groups[0].sections.filter((s) => s.pickValue !== undefined)

  const apply = (goSettings: boolean) => {
    setValue(['platform'], sel.platform)
    setValue(['chat_type'], sel.brain)
    setValue(['audio_synthesis_type'], sel.tts)
    if (sel.body === 'live2d') {
      setValue(['visual_body'], '其他')
      setValue(['live2d', 'enable'], true)
    } else {
      setValue(['visual_body'], sel.body)
    }
    notify.info('向导选择已写入（待保存）——点顶栏「保存」落盘')
    onApply(goSettings)
  }

  return (
    <div className="dialog-backdrop" style={{ zIndex: 70 }} onMouseDown={onClose}>
      <div
        className="card-surface flex max-h-[86vh] w-full max-w-[760px] flex-col overflow-hidden p-0"
        onMouseDown={(e) => e.stopPropagation()}
      >
        {/* 头部 + 进度 */}
        <div className="px-6 pb-3 pt-5">
          <div className="flex items-center gap-3">
            <h3 className="text-[16px] font-bold">开播设置向导</h3>
            <span className="text-xs text-[var(--ink-mut)]">只做选择，必填参数到「基础设置」补，全程可跳过</span>
            <button className="ml-auto rounded-md border border-slate-300 px-2.5 py-1 text-xs hover:bg-slate-50" onClick={onClose}>
              跳过向导
            </button>
          </div>
          <div className="mt-3.5 flex items-center gap-2">
            {STEP_TITLES.map((t, i) => (
              <div key={t} className="flex flex-1 items-center gap-2">
                <span className={`text-xs ${i === step ? 'font-semibold' : ''}`} style={{ color: i === step ? 'var(--accent)' : i < step ? 'var(--ok)' : 'var(--ink-mut)' }}>
                  {i + 1}. {t}
                </span>
                {i < STEP_TITLES.length - 1 && (
                  <span className="h-[3px] flex-1 rounded-full" style={{ background: i < step ? 'var(--ok)' : i === step ? 'var(--accent)' : '#e4e7ec' }} />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* 步骤内容 */}
        <div className="flex-1 overflow-y-auto px-6 pb-5">
          {step < 4 && <p className="mb-3 text-[13px] leading-relaxed text-[var(--ink-mut)]">{GUIDES[step]}</p>}

          {step === 0 && (
            <>
              <div className="grid grid-cols-2 gap-2.5 md:grid-cols-3">
                {PLATFORM_ORDER.map((v) => (
                  <WizCard key={v} name={PLATFORM_OPTIONS[v] ?? v} note={PLATFORM_NOTES[v]} on={sel.platform === v} onClick={() => setSel({ ...sel, platform: v })} />
                ))}
              </div>
              {!['talk', 'live_monitor_assistant'].includes(sel.platform) && (
                <label className="mt-4 flex max-w-[420px] items-center gap-3">
                  <span className="flex-none text-[13px] font-medium">直播间号</span>
                  <input
                    className="inp"
                    value={String(getByPath(draft as JsonObject, ['room_display_id']) ?? '')}
                    placeholder="直播间网址最后一段"
                    onChange={(e) => setValue(['room_display_id'], e.target.value)}
                  />
                </label>
              )}
            </>
          )}

          {step === 1 && (
            <div className="grid grid-cols-2 gap-2.5 md:grid-cols-3">
              {brainSections.map((s) => (
                <WizCard key={s.id} name={s.title} note={s.tags?.join(' · ')} desc={s.desc} on={sel.brain === s.pickValue} onClick={() => setSel({ ...sel, brain: String(s.pickValue) })} />
              ))}
            </div>
          )}

          {step === 2 && (
            <div className="grid grid-cols-2 gap-2.5 md:grid-cols-3">
              {ttsSections.map((s) => (
                <WizCard key={s.id} name={s.title} note={s.tags?.join(' · ')} desc={s.desc} on={sel.tts === s.pickValue} onClick={() => setSel({ ...sel, tts: String(s.pickValue) })} />
              ))}
            </div>
          )}

          {step === 3 && (
            <div className="grid grid-cols-2 gap-2.5 md:grid-cols-3">
              <WizCard name="Live2D（推荐）" note="本机运行 · 免费" desc="模型放本地即用，口型同步+表情动作" on={sel.body === 'live2d'} onClick={() => setSel({ ...sel, body: 'live2d' })} />
              {Object.entries(VISUAL_BODY_OPTIONS).map(([v, label]) => (
                <WizCard key={v} name={label} on={sel.body === v} onClick={() => setSel({ ...sel, body: v })} />
              ))}
            </div>
          )}

          {step === 4 && (
            <>
              <div className="rounded-lg border px-4 py-3 text-[13px] leading-relaxed" style={{ borderColor: 'color-mix(in srgb, var(--accent) 40%, #e4e7ec)', background: 'color-mix(in srgb, var(--accent) 6%, white)' }}>
                选择已就绪。点「去补参数」到基础设置填<b>密钥等必填项</b>（选完服务才有表单可填）；
                改完记得点顶栏<b>「保存」</b>，然后回开播台一键运行。
              </div>
              <div className="card-surface mt-3 max-w-[440px] px-4 py-2">
                {[
                  ['直播平台', PLATFORM_OPTIONS[sel.platform] ?? sel.platform],
                  ['AI 大脑', brainSections.find((s) => String(s.pickValue) === sel.brain)?.title ?? sel.brain],
                  ['声音', ttsSections.find((s) => String(s.pickValue) === sel.tts)?.title ?? sel.tts],
                  ['形象', sel.body === 'live2d' ? 'Live2D' : (VISUAL_BODY_OPTIONS[sel.body] ?? sel.body)],
                ].map(([k, v]) => (
                  <div key={k} className="flex items-center justify-between border-b border-slate-100 py-2 last:border-b-0">
                    <span className="text-[var(--ink-mut)]">{k}</span>
                    <b className="text-[13px]">{v}</b>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* 底部按钮 */}
        <div className="flex items-center justify-end gap-2.5 border-t border-slate-100 px-6 py-3.5">
          {step > 0 && (
            <button className="rounded-lg border border-slate-300 px-3.5 py-1.5 text-[13px] hover:bg-slate-50" onClick={() => setStep(step - 1)}>
              上一步
            </button>
          )}
          <div className="flex-1" />
          {step < 4 ? (
            <button
              className="rounded-lg px-4 py-1.5 text-[13px] font-medium text-white transition hover:opacity-90"
              style={{ background: 'var(--accent)' }}
              onClick={() => setStep(step + 1)}
            >
              {step === 3 ? '完成' : '下一步'}
            </button>
          ) : (
            <>
              <button className="rounded-lg border border-slate-300 px-3.5 py-1.5 text-[13px] hover:bg-slate-50" onClick={() => apply(false)}>
                完成，回开播台
              </button>
              <button
                className="rounded-lg px-4 py-1.5 text-[13px] font-medium text-white transition hover:opacity-90"
                style={{ background: 'var(--accent)' }}
                onClick={() => apply(true)}
              >
                去补参数 →
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

function WizCard({ name, note, desc, on, onClick }: { name: string; note?: string; desc?: string; on: boolean; onClick: () => void }) {
  return (
    <button
      className={`relative rounded-xl border p-3 text-left transition ${on ? '' : 'bg-white hover:border-slate-400'}`}
      style={on
        ? { borderColor: 'var(--accent)', boxShadow: '0 0 0 3px color-mix(in srgb, var(--accent) 15%, transparent)' }
        : { borderColor: '#e4e7ec' }}
      onClick={onClick}
    >
      <div className="pr-6 text-[13.5px] font-semibold">{name}</div>
      {note && <div className="mt-1 text-[11.5px] text-[var(--ink-mut)]">{note}</div>}
      {!note && desc && <div className="mt-1 line-clamp-2 text-[11.5px] leading-relaxed text-[var(--ink-mut)]">{desc}</div>}
      <span
        className="absolute right-2.5 top-2.5 flex items-center justify-center rounded-full border-2"
        style={{ width: 18, height: 18, borderColor: on ? 'var(--accent)' : '#cbd5e1', background: on ? 'var(--accent)' : '#fff' }}
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
}
