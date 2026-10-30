/** 声音与表现的专用组件：TTS 试听坞。 */
import { useRef, useState } from 'react'
import { api, audioUrl } from '../api/client'
import { getByPath } from '../lib/path'
import { useConfigStore } from '../state/configStore'
import { useTestStore } from '../state/testStore'
import { notify } from '../state/ui'
import { AUDIO_SYNTHESIS_TYPE_OPTIONS } from '../schema/options'

/** TTS 语音合成调试：按已保存的引擎配置合成一段文本并播放。 */
export function TtsTester() {
  const draft = useConfigStore((s) => s.draft)
  const setValue = useConfigStore((s) => s.setValue)
  const [text, setText] = useState('你好，这里是语音合成试听')
  const [busy, setBusy] = useState(false)
  const [audioPath, setAudioPath] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement>(null)

  const engine = String(getByPath(draft ?? {}, ['audio_synthesis_type']) ?? 'none')
  const engineLabel = AUDIO_SYNTHESIS_TYPE_OPTIONS[engine] ?? engine

  const synth = async () => {
    if (engine === 'none') {
      notify.warn('当前「语音合成」选的是 不启用，先选一个引擎')
      return
    }
    setBusy(true)
    try {
      const username = String(getByPath(draft ?? {}, ['talk', 'username']) || '主播')
      const resp = await api.action('tts-test', { content: text, username })
      // 试听结果记账：选卡墙/信号链据此显示「已测通」（网络异常不算引擎的账）
      if (engine !== 'none') {
        useTestStore.getState().record('tts', engine, resp.code === 200 && Boolean(resp.audio_path), resp.message ?? '')
      }
      if (resp.code === 200 && resp.audio_path) {
        setAudioPath(resp.audio_path)
        notify.ok(`合成成功（${engineLabel}），即将播放`)
        setTimeout(() => void audioRef.current?.play().catch(() => undefined), 200)
      } else {
        notify.err(resp.message ?? '合成失败')
      }
    } catch {
      notify.err('合成失败：连不上后端')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-end gap-4">
        <div className="w-64 max-w-full">
          <label className="mb-1 block text-[13px] font-medium">当前TTS引擎</label>
          <select
            className="inp"
            value={engine}
            onChange={(e) => setValue(['audio_synthesis_type'], e.target.value)}
          >
            {Object.entries(AUDIO_SYNTHESIS_TYPE_OPTIONS).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
          <p className="mt-1 text-xs text-[var(--ink-mut)]">在线试听与快速测试当前配置的语音合成效果与音色表现。</p>
        </div>
        <div className="min-w-[16rem] flex-1">
          <label className="mb-1 block text-[13px] font-medium">试听文本</label>
          <input
            className="inp"
            value={text}
            placeholder="输入要合成试听的文本"
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.nativeEvent.isComposing && void synth()}
          />
        </div>
        <button
          className="h-[34px] rounded-lg px-4 text-[13px] font-medium text-white transition hover:opacity-90 disabled:opacity-50"
          style={{ background: 'var(--accent)' }}
          disabled={busy}
          onClick={() => void synth()}
        >
          {busy ? '合成中…' : '合成并播放'}
        </button>
      </div>

      {audioPath && (
        <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50/70 px-3 py-2">
          <audio ref={audioRef} controls src={audioUrl(audioPath)} className="h-8 w-full max-w-[520px]" />
          <span className="truncate text-xs text-[var(--ink-mut)]" title={audioPath}>
            {audioPath}
          </span>
        </div>
      )}

      <p className="text-xs leading-relaxed text-[var(--ink-mut)]">
        试听用的是<b>已保存</b>的引擎配置（含各引擎细项）——界面上改了参数要先「保存配置」再听。说话人取自聊天页的「说话人昵称」。
      </p>
    </div>
  )
}
