/** 播报优先级：拖拽排序替代 20 个数字输入框。

 * 数据仍是 filter.priority_mapping（数字越大越优先）；拖完把已知模块按名次
 * 归一化写回（第 1 名 = N，最后一名 = 1），未知键原样保留。
 */
import { useRef, useState } from 'react'
import { getByPath, type JsonObject } from '../lib/path'
import { useConfigStore } from '../state/configStore'
import { notify } from '../state/ui'

/** 已知模块（key = filter.priority_mapping 的键）。顺序只是初始展示的兜底排序。 */
export const PRIORITY_MODULES: [key: string, label: string][] = [
  ['talk', '聊天（语音输入）'],
  ['comment', '弹幕回复'],
  ['gift', '礼物答谢'],
  ['entrance', '入场欢迎'],
  ['follow', '关注答谢'],
  ['song', '点歌'],
  ['read_comment', '念弹幕'],
  ['reread', '复读'],
  ['copywriting', '文案'],
  ['schedule', '定时任务'],
  ['idle_time_task', '闲时任务'],
  ['key_mapping', '按键映射'],
  ['integral', '积分'],
  ['abnormal_alarm', '异常报警'],
  ['trends_copywriting', '动态文案'],
  ['image_recognition_schedule', '画面识别'],
  ['local_qa_audio', '本地问答-音频'],
  ['reread_top_priority', '最高优先级复读'],
  ['assistant_anchor_text', '助播-文本'],
  ['assistant_anchor_audio', '助播-音频'],
]

export function PriorityList() {
  const draft = useConfigStore((s) => s.draft)
  const setValue = useConfigStore((s) => s.setValue)
  const dragFrom = useRef<number | null>(null)
  const [dragState, setDragState] = useState<{ from: number; over: number }>({ from: -1, over: -1 })

  const mapping: JsonObject = (getByPath(draft ?? {}, ['filter', 'priority_mapping']) ?? {}) as JsonObject
  const items = PRIORITY_MODULES.map(([key, label]) => ({
    key,
    label,
    value: Number(mapping[key] ?? 0),
  })).sort((a, b) => b.value - a.value)

  const reset = () => {
    dragFrom.current = null
    setDragState({ from: -1, over: -1 })
  }

  const drop = (to: number) => {
    const from = dragFrom.current
    if (from === null || from === to) {
      reset()
      return
    }
    const next = [...items]
    const [moved] = next.splice(from, 1)
    next.splice(to, 0, moved)
    // 名次归一化写回：越靠上数字越大；未知键原样保留
    const patch: Record<string, number> = {}
    next.forEach((m, i) => {
      patch[m.key] = next.length - i
    })
    setValue(['filter', 'priority_mapping'], { ...mapping, ...patch })
    notify.info('播报顺序已更新 · 记得保存')
    reset()
  }

  return (
    <div className="flex flex-col gap-1.5">
      <p className="text-xs leading-relaxed text-[var(--ink-mut)]">
        拖拽调整顺序，<b>越靠上越优先</b>：消息排队时高优先级先合成先播放。松手后按名次重写各模块的优先级数字（第 1 名 = {items.length}）。
      </p>
      <div className="flex flex-col gap-1.5">
        {items.map((m, i) => (
          <div
            key={m.key}
            draggable
            onDragStart={() => {
              dragFrom.current = i
              setDragState({ from: i, over: -1 })
            }}
            onDragOver={(e) => {
              e.preventDefault()
              setDragState((s) => (s.over === i ? s : { ...s, over: i }))
            }}
            onDrop={() => drop(i)}
            onDragEnd={reset}
            className={`flex cursor-grab items-center gap-3 rounded-lg border bg-white px-3.5 py-2 transition ${
              dragState.from === i ? 'opacity-40' : ''
            }`}
            style={dragState.over === i && dragState.from !== i ? { borderColor: 'var(--accent)', boxShadow: '0 0 0 3px color-mix(in srgb, var(--accent) 15%, transparent)' } : { borderColor: '#e4e7ec' }}
          >
            <span className="flex-none select-none text leading-none" style={{ color: '#cbd5e1', letterSpacing: '-1px' }}>⠿</span>
            <span className="flex h-5 w-5 flex-none items-center justify-center rounded bg-slate-100 text-[11px] font-bold text-[var(--ink-mut)]">
              {i + 1}
            </span>
            <span className={`min-w-0 flex-1 truncate text-[13px] ${i === 0 ? 'font-semibold' : ''}`}>{m.label}</span>
            {i === 0 && <span className="flex-none rounded border border-emerald-200 bg-emerald-50 px-1.5 py-px text-[11px]" style={{ color: 'var(--ok)' }}>最高</span>}
            <span className="flex-none rounded bg-slate-100 px-1.5 py-px font-mono text-[11px] text-[var(--ink-mut)]" title="filter.priority_mapping 的当前值">{m.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
