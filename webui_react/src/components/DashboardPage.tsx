/** 开播台：信号链可视化 + 下一步建议 + 运行控制 + 聊天测试入口。

 * 取代旧「总览」页：readiness 从四行清单升级为信号链节点，
 * 运行/停止/日志/重启从右下角操作坞收编到这一页。
 */
import { useState } from 'react'
import { api } from '../api/client'
import { getByPath, type JsonObject } from '../lib/path'
import { useConfigStore } from '../state/configStore'
import { useOpsStore } from '../state/opsStore'
import { notify, useConfirmStore, useJumpStore } from '../state/ui'
import {
  AUDIO_SYNTHESIS_TYPE_OPTIONS,
  CHAT_TYPE_OPTIONS,
  LIVE_MONITOR_PLATFORM_KEYS,
  platformOptions,
  VISUAL_BODY_OPTIONS,
} from '../schema/options'
import { RunLogDialog } from './Dialogs'

interface ChainNode {
  step: string
  title: string
  ok: boolean
  value: string
  hint: string
}

function readiness(config: JsonObject): ChainNode[] {
  const platform = getByPath(config, ['platform']) as string | undefined
  const room = getByPath(config, ['room_display_id']) as string | undefined
  const chatType = getByPath(config, ['chat_type']) as string | undefined
  const ttsType = getByPath(config, ['audio_synthesis_type']) as string | undefined
  const body = getByPath(config, ['visual_body']) as string | undefined
  const live2dOn = Boolean(getByPath(config, ['live2d', 'enable']))

  const platLabel = platformOptions(platform)[platform ?? ''] ?? platform ?? '未选择'
  return [
    {
      step: 'platform',
      title: '直播间',
      ok: Boolean(platform) && platform !== 'talk' && Boolean(room),
      value: platLabel + (room ? ` · 房间号 ${room}` : ' · 未填房间号'),
      hint: '不接平台就只能按文案念，收不到任何弹幕',
    },
    {
      step: 'brain',
      title: 'AI 大脑',
      ok: Boolean(chatType) && chatType !== 'none',
      value: CHAT_TYPE_OPTIONS[chatType ?? ''] ?? chatType ?? '未选择',
      hint: '不选则数字人不会回答，只会复读或只念文案',
    },
    {
      step: 'voice',
      title: '声音',
      ok: Boolean(ttsType) && ttsType !== 'none',
      value: AUDIO_SYNTHESIS_TYPE_OPTIONS[ttsType ?? ''] ?? ttsType ?? '未选择',
      hint: '不选就没有声音，弹幕回复只会出现在字幕页',
    },
    {
      step: 'body',
      title: '形象',
      ok: Boolean(body) || live2dOn,
      value: live2dOn ? 'Live2D' : (VISUAL_BODY_OPTIONS[body ?? ''] ?? body ?? '未选择'),
      hint: '只要画面的话，留「其他（外置）」由外部窗口显示',
    },
  ]
}

export function DashboardPage({ onOpenChat, onOpenWizard }: { onOpenChat: () => void; onOpenWizard: () => void }) {
  const draft = useConfigStore((s) => s.draft)
  const running = useOpsStore((s) => s.running)
  const refresh = useOpsStore((s) => s.refresh)
  const jump = useJumpStore((s) => s.jump)
  const ask = useConfirmStore((s) => s.ask)

  const [busy, setBusy] = useState(false)
  const [logOpen, setLogOpen] = useState(false)

  if (!draft) return null
  const nodes = readiness(draft)
  const missing = nodes.find((n) => !n.ok)
  const platform = getByPath(draft, ['platform']) as string | undefined

  const run = async () => {
    setBusy(true)
    try {
      const resp = await api.opsRun()
      resp.code === 200 ? notify.ok(resp.message ?? '已运行') : notify.warn(resp.message ?? '运行失败')
      await refresh()
    } finally {
      setBusy(false)
    }
  }

  const stop = () =>
    ask(
      '确认停止正在运行的直播程序？',
      async () => {
        setBusy(true)
        try {
          const resp = await api.opsStop()
          resp.code === 200 ? notify.ok(resp.message ?? '已停止') : notify.warn(resp.message ?? '停止失败')
          await refresh()
        } finally {
          setBusy(false)
        }
      },
      '弹幕监听、文案播报和虚拟身体会一起停下；正在直播的话，这一下就是断播。',
    )

  const restart = () =>
    ask(
      '确认重启 webui？',
      async () => {
        notify.info('重启中...')
        await api.opsRestart().catch(() => undefined)
        // 服务端 os.execl 自替换，这个响应多半送不回来；过几秒还不通就提示手动刷新
        setTimeout(() => {
          void api.opsStatus().then(
            () => notify.ok('webui 已重启'),
            () => notify.warn('还没连上重启后的服务，稍等几秒刷新页面'),
          )
        }, 4000)
      },
      '会先停掉正在运行的直播程序，再用当前配置重新拉起 webui；没点「保存」的改动会全部丢失。',
    )

  return (
    <div className="flex flex-col gap-5">
      {/* 下一步建议：只给一条最重要的动作 */}
      <div className="card-surface px-5 py-4">
        {missing ? (
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="flex h-6 w-6 flex-none items-center justify-center rounded-full text-[13px] font-bold text-white" style={{ background: 'var(--warn)' }}>
              {nodes.indexOf(missing) + 1}
            </span>
            <span className="text-[14px]">
              还差 <b>{nodes.filter((n) => !n.ok).length} 步</b>就能开播 ——「{missing.title}」{missing.ok ? '' : `：${missing.hint}`}
            </span>
            <button
              className="rounded-lg px-3.5 py-1.5 text-[13px] font-medium text-white transition hover:opacity-90"
              style={{ background: 'var(--accent)' }}
              onClick={() => jump(missing.step, {})}
            >
              去配置 →
            </button>
          </div>
        ) : (
          <div className="text-[14px]">
            <b style={{ color: 'var(--ok)' }}>一切就绪</b>，随时可以开播。改过配置记得先保存再重新运行。
          </div>
        )}
        {platform === 'dy' && (
          <p className="mt-2 text-xs" style={{ color: 'var(--warn)' }}>
            对接抖音平台时，请先开启抖音弹幕监听程序！直播间号不需要填写
          </p>
        )}
        {platform && LIVE_MONITOR_PLATFORM_KEYS.includes(platform) && (
          <p className="mt-2 text-xs" style={{ color: 'var(--warn)' }}>
            走「直播弹幕监听助手」接入：请先让助手把弹幕推到「基础设置 → 直播间 → 直播弹幕监听助手」里配置的地址，监听哪个直播间由助手那边决定，直播间号不需要填写
          </p>
        )}
        {platform === 'bilibili' && (
          <p className="mt-2 text-xs text-[var(--ink-mut)]">哔哩哔哩1 监听不是很稳定，推荐使用 哔哩哔哩2</p>
        )}
        <div className="mt-2.5 text-xs text-[var(--ink-mut)]">
          想从头过一遍？
          <button className="ml-1 font-medium hover:underline" style={{ color: 'var(--accent)' }} onClick={onOpenWizard}>
            运行设置向导（5 步）
          </button>
        </div>
      </div>

      {/* 信号链：弹幕从哪来 → 谁想 → 谁说 → 长什么样 */}
      <div>
        <div className="mb-2.5 flex items-baseline gap-3">
          <h2 className="text-[15px] font-bold">信号链</h2>
          <span className="text-xs text-[var(--ink-mut)]">弹幕从哪来 → 谁想 → 谁说 → 长什么样；点节点直达配置</span>
        </div>
        <div className="flex flex-col gap-2.5 lg:flex-row">
          {nodes.map((n, i) => (
            <div key={n.step} className="flex flex-1 items-center gap-2.5">
              <button
                className="card-surface w-full px-4 py-3 text-left transition hover:border-[var(--accent)]"
                onClick={() => jump(n.step, {})}
              >
                <div className="flex items-center gap-2">
                  <span className="text-[13.5px] font-semibold">{n.title}</span>
                  <span
                    className="ml-auto inline-block h-2 w-2 flex-none rounded-full"
                    style={{ background: n.ok ? 'var(--ok)' : '#cbd5e1' }}
                    title={n.ok ? '已配置' : '未配置'}
                  />
                </div>
                <div className={`mt-1 truncate text-[13px] ${n.ok ? '' : 'text-[var(--ink-mut)]'}`} title={n.value}>
                  {n.value}
                </div>
                {!n.ok && <div className="mt-0.5 text-xs" style={{ color: 'var(--warn)' }}>{n.hint}</div>}
              </button>
              {i < nodes.length - 1 && (
                <span className="hidden flex-none text-slate-300 lg:block" aria-hidden>→</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 运行控制 + 聊天测试 */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="card-surface p-5">
          <div className="flex items-center gap-3">
            <span className="inline-block h-2.5 w-2.5 flex-none rounded-full" style={{ background: running ? 'var(--ok)' : '#cbd5e1' }} />
            <div className="min-w-0">
              <div className="text-[14.5px] font-semibold">{running ? '直播程序运行中' : '直播程序未运行'}</div>
              <div className="text-xs text-[var(--ink-mut)]">{running ? '弹幕监听与语音合成工作中' : '用当前已保存的配置启动 main.py'}</div>
            </div>
            <div className="ml-auto flex-none">
              {running ? (
                <button className="rounded-lg border border-red-200 px-4 py-1.5 text-[13px] font-medium text-red-600 transition hover:bg-red-50 disabled:opacity-50" disabled={busy} onClick={stop}>
                  ■ 停止
                </button>
              ) : (
                <button
                  className="rounded-lg px-4 py-1.5 text-[13px] font-medium text-white transition hover:opacity-90 disabled:opacity-50"
                  style={{ background: 'var(--accent)' }}
                  disabled={busy}
                  onClick={() => void run()}
                >
                  ▶ 开始直播
                </button>
              )}
            </div>
          </div>
          <div className="mt-3.5 flex items-center gap-2 border-t border-slate-100 pt-3">
            <button className="rounded-md border border-slate-300 px-3 py-1 text-xs transition hover:border-[var(--accent)] hover:text-[var(--accent)]" onClick={() => setLogOpen(true)}>
              运行日志
            </button>
            <button className="rounded-md border border-slate-300 px-3 py-1 text-xs transition hover:border-[var(--accent)] hover:text-[var(--accent)]" onClick={restart}>
              重启 webui
            </button>
            <span className="ml-auto text-[11px] text-[var(--ink-mut)]">配置变更后需重启生效</span>
          </div>
        </div>

        <div className="card-surface flex flex-col p-5">
          <div className="flex items-center gap-2.5">
            <span className="text-[14.5px] font-semibold">聊天测试</span>
            <span className="text-xs text-[var(--ink-mut)]">验证「大脑 → 声音」整条通路</span>
          </div>
          <p className="mt-2.5 text-[13px] leading-relaxed text-[var(--ink-mut)]">
            {running
              ? '直播程序已在运行——进去发一句话，看她怎么接。'
              : '先把大脑和声音配好，进聊天页就能不带直播间直接对话调试；也可以等一键运行后在这里看弹幕与回复的同步记录。'}
          </p>
          <button
            className="mt-auto self-start rounded-lg px-3.5 py-1.5 text-[13px] font-medium transition"
            style={{ color: 'var(--accent)', border: '1px solid var(--accent)' }}
            onClick={onOpenChat}
          >
            打开聊天页 →
          </button>
        </div>
      </div>

      {logOpen && <RunLogDialog onClose={() => setLogOpen(false)} />}
    </div>
  )
}
