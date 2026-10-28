/** 总览页：运行态 + 未保存计数 + 开播就绪度。数据全部读自真实 config，不放假数。 */
import { useConfigStore, useChanges } from '../state/configStore'
import { useOpsStore } from '../state/opsStore'
import { useJumpStore, notify } from '../state/ui'
import { getByPath, type JsonObject } from '../lib/path'
import {
  AUDIO_SYNTHESIS_TYPE_OPTIONS,
  CHAT_TYPE_OPTIONS,
  LIVE_MONITOR_PLATFORM_KEYS,
  PLATFORM_OPTIONS,
  VISUAL_BODY_OPTIONS,
  platformOptions,
} from '../schema/options'

interface ReadinessRow {
  title: string
  value: string
  ok: boolean
  fieldId: string
  hint: string
}

function readiness(config: JsonObject): ReadinessRow[] {
  const platform = getByPath(config, ['platform']) as string | undefined
  const room = getByPath(config, ['room_display_id']) as string | undefined
  const chatType = getByPath(config, ['chat_type']) as string | undefined
  const ttsType = getByPath(config, ['audio_synthesis_type']) as string | undefined
  const body = getByPath(config, ['visual_body']) as string | undefined

  const platLabel = platformOptions(platform)[platform ?? ''] ?? platform ?? '未选择'
  return [
    {
      title: '弹幕来源',
      value: platLabel + (room ? ` · 房间号 ${room}` : ' · 未填房间号'),
      ok: Boolean(platform) && platform !== 'talk' && Boolean(room),
      fieldId: 'live__base-model__platform',
      hint: '不接平台就只能按文案念，收不到任何弹幕',
    },
    {
      title: '大语言模型',
      value: CHAT_TYPE_OPTIONS[chatType ?? ''] ?? chatType ?? '未选择',
      ok: Boolean(chatType) && chatType !== 'none',
      fieldId: 'live__base-model__chat_type',
      hint: '不选则数字人不会回答，只会复读或只念文案',
    },
    {
      title: '文本转语音',
      value: AUDIO_SYNTHESIS_TYPE_OPTIONS[ttsType ?? ''] ?? ttsType ?? '未选择',
      ok: Boolean(ttsType) && ttsType !== 'none',
      fieldId: 'live__base-model__audio_synthesis_type',
      hint: '不选就没有声音，弹幕回复只会出现在字幕页',
    },
    {
      title: '虚拟身体',
      value: VISUAL_BODY_OPTIONS[body ?? ''] ?? body ?? '未选择',
      ok: Boolean(body),
      fieldId: 'live__base-model__visual_body',
      hint: '只要画面的话，留「其他（外置）」由外部窗口显示',
    },
  ]
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

export function OverviewPage() {
  const config = useConfigStore((s) => s.config)
  const draft = useConfigStore((s) => s.draft)
  const save = useConfigStore((s) => s.save)
  const changes = useChanges()
  const running = useOpsStore((s) => s.running)
  const jump = useJumpStore((s) => s.jump)

  if (!config || !draft) return null
  const rows = readiness(draft)

  const handleSave = async () => {
    if (changes.length === 0) {
      notify.info('没有未保存的改动')
      return
    }
    notify.info(summarize(draft))
    const outcome = await save()
    if (outcome.ok) notify.ok(outcome.message)
    else notify.err(outcome.message)
  }

  const platform = getByPath(draft, ['platform']) as string | undefined

  return (
    <div className="mx-auto w-full max-w-[760px] px-4 pb-28 pt-4">
      <div className="card-surface p-5">
        <h2 className="text-[17px] font-semibold">开播就绪度</h2>
        <p className="mt-1.5 text-[13px]" style={{ color: running ? 'var(--ok)' : 'var(--ink-mut)' }}>
          {running ? '直播程序运行中' : '直播程序未运行 · 右下角「操作」→ 一键运行'}
        </p>
        <p className="text-[13px]" style={{ color: changes.length > 0 ? 'var(--warn)' : 'var(--ok)' }}>
          {changes.length > 0 ? `有 ${changes.length} 项改动未保存` : '配置已保存'}
        </p>

        <div className="mt-3 rounded-lg bg-indigo-50/70 px-3 py-2 text-xs leading-relaxed text-[#3730a3]">
          第一次搭：按 1→4 填完就能开播。填好的会打勾，点某一行右边的「去配置」直接跳到那个框。
        </div>

        {rows.map((row, i) => (
          <div key={row.title} className="mt-1 flex items-center gap-3 border-t border-slate-900/10 py-2.5 first:border-t-0">
            {row.ok ? (
              <span className="text-xl leading-none" style={{ color: 'var(--ok)' }}>✓</span>
            ) : (
              <span
                className="flex h-5 w-5 flex-none items-center justify-center rounded-full text-xs font-semibold text-white"
                style={{ background: 'var(--warn)' }}
              >
                {i + 1}
              </span>
            )}
            <div className="min-w-0 flex-1">
              <div className="text-[14px] font-semibold">{row.title}</div>
              <div className="text-[13px] text-[var(--ink-mut)]">
                {row.ok ? row.value : `${row.value} —— ${row.hint}`}
              </div>
            </div>
            <button
              className="flex-none rounded-md px-2 py-1 text-[13px] font-medium hover:underline"
              style={{ color: 'var(--accent)' }}
              onClick={() => jump('live', { fieldId: row.fieldId })}
            >
              去配置
            </button>
          </div>
        ))}

        {/* 平台相关的开播提示（v2 check_config 的提醒部分） */}
        {platform === 'dy' && (
          <p className="mt-2 text-xs" style={{ color: 'var(--warn)' }}>
            对接抖音平台时，请先开启抖音弹幕监听程序！直播间号不需要填写
          </p>
        )}
        {platform && LIVE_MONITOR_PLATFORM_KEYS.includes(platform) && (
          <p className="mt-2 text-xs" style={{ color: 'var(--warn)' }}>
            走「直播弹幕监听助手」接入：请先让助手把弹幕推到 webui「直播接入 → 直播弹幕监听助手」里配置的地址，监听哪个直播间由助手那边决定，直播间号不需要填写
          </p>
        )}
        {platform === 'bilibili' && (
          <p className="mt-2 text-xs text-[var(--ink-mut)]">哔哩哔哩1 监听不是很稳定，推荐使用 哔哩哔哩2</p>
        )}

        <button
          className="mt-4 rounded-lg px-4 py-1.5 text-[13px] font-medium text-white transition hover:opacity-90"
          style={{ background: 'var(--accent)' }}
          onClick={handleSave}
        >
          保存配置
        </button>
      </div>
    </div>
  )
}
