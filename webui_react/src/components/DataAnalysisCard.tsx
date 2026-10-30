/** 数据分析卡：词云 Top 与四类榜单（纯 CSS 条形，不引图表库）。 */
import { useCallback, useEffect, useState } from 'react'
import { api, type BarDataset } from '../api/client'
import { notify } from '../state/ui'

interface AnalysisData {
  words?: { name: string; value: number }[]
  integral?: BarDataset | null
  view_num?: BarDataset | null
  sign_num?: BarDataset | null
  total_price?: BarDataset | null
  gift?: BarDataset | null
}

function Bars({ title, data }: { title: string; data?: BarDataset | null }) {
  if (!data || data.users.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
        <h4 className="text-[13px] font-semibold">{title}</h4>
        <p className="mt-2 text-xs text-[var(--ink-mut)]">暂无数据（数据库还没积累记录）</p>
      </div>
    )
  }
  const series = data.series[0]
  const rows = data.users.map((user, i) => ({ user, value: Number(series?.data?.[i] ?? 0) }))
  const max = Math.max(...rows.map((r) => r.value), 1)

  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
      <h4 className="text-[13px] font-semibold">
        {title}
        {series?.name ? <span className="ml-2 text-xs font-normal text-[var(--ink-mut)]">{series.name}</span> : null}
      </h4>
      <div className="mt-2 flex flex-col gap-1.5">
        {rows.map((r) => (
          <div key={r.user} className="flex items-center gap-2">
            <span className="w-24 flex-none truncate text-xs text-[var(--ink-mut)]" title={r.user}>
              {r.user}
            </span>
            <div className="h-4 flex-1 overflow-hidden rounded bg-white ring-1 ring-slate-200">
              <div className="h-full rounded" style={{ width: `${Math.max((r.value / max) * 100, 2)}%`, background: 'var(--accent)', opacity: 0.75 }} />
            </div>
            <span className="w-16 flex-none text-right text-xs font-medium">{r.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function WordBars({ words }: { words?: { name: string; value: number }[] }) {
  if (!words || words.length === 0) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
        <h4 className="text-[13px] font-semibold">弹幕关键词</h4>
        <p className="mt-2 text-xs text-[var(--ink-mut)]">暂无数据（数据库还没积累弹幕记录）</p>
      </div>
    )
  }
  const max = Math.max(...words.map((w) => w.value), 1)
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
      <h4 className="text-[13px] font-semibold">弹幕关键词</h4>
      <div className="mt-2 flex flex-wrap gap-x-4 gap-y-2">
        {words.map((w) => (
          <span key={w.name} className="inline-flex flex-col items-center">
            <span
              className="font-semibold leading-tight"
              style={{ fontSize: `${Math.min(13 + (w.value / max) * 14, 28)}px`, opacity: 0.55 + (w.value / max) * 0.45 }}
            >
              {w.name}
            </span>
            <span className="text-[10px] text-[var(--ink-mut)]">{w.value}</span>
          </span>
        ))}
      </div>
    </div>
  )
}

const BOARD_DEFS: { key: keyof AnalysisData; title: string }[] = [
  { key: 'integral', title: '积分榜' },
  { key: 'view_num', title: '观看榜' },
  { key: 'sign_num', title: '签到榜' },
  { key: 'total_price', title: '金额榜' },
]

export function DataAnalysisCard() {
  const [data, setData] = useState<AnalysisData>({})
  const [top, setTop] = useState(10)
  const [busy, setBusy] = useState(false)
  const [board, setBoard] = useState<keyof AnalysisData>('integral')

  const refresh = useCallback(async () => {
    setBusy(true)
    try {
      const resp = await api.dataAnalysis(top)
      if (resp.code === 200) {
        setData(resp as AnalysisData)
      } else {
        notify.warn(resp.message ?? '数据分析失败')
      }
    } catch {
      notify.err('数据分析请求失败')
    } finally {
      setBusy(false)
    }
  }, [top])

  useEffect(() => {
    void refresh()
  }, [refresh])

  const boardTitle = BOARD_DEFS.find((b) => b.key === board)?.title ?? ''
  const giftUsers = data.gift?.users ?? []

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-start gap-4">
        <div className="w-36">
          <label className="mb-1 block text-[13px] font-medium">Top N</label>
          <input
            className="inp"
            inputMode="numeric"
            value={top}
            onChange={(e) => setTop(Math.max(1, parseInt(e.target.value, 10) || 10))}
          />
        </div>
        <div>
          {/* 隐形标签行占位：让按钮与旁边输入框的控件基线对齐 */}
          <span aria-hidden className="mb-1 block text-[13px] font-medium">&nbsp;</span>
          <button
            className="h-[35px] rounded-lg px-4 text-[13px] font-medium text-white transition hover:opacity-90 disabled:opacity-50"
            style={{ background: 'var(--accent)' }}
            disabled={busy}
            onClick={() => void refresh()}
          >
            {busy ? '统计中…' : '更新数据'}
          </button>
        </div>
        <div>
          <span aria-hidden className="mb-1 block text-[13px] font-medium">&nbsp;</span>
          <div className="flex flex-wrap gap-1.5">
            {BOARD_DEFS.map((b) => (
              <button
                key={b.key}
                className={`rounded-full px-3 py-1 text-xs font-medium ring-1 transition ${
                  board === b.key ? 'text-white ring-transparent' : 'bg-white text-[var(--ink-mut)] ring-slate-300 hover:text-[var(--accent)]'
                }`}
                style={board === b.key ? { background: 'var(--accent)' } : undefined}
                onClick={() => setBoard(b.key)}
              >
                {b.title}
              </button>
            ))}
          </div>
        </div>
      </div>

      <WordBars words={data.words} />
      <Bars title={boardTitle} data={data[board] as BarDataset | null | undefined} />
      <Bars title="礼物榜" data={data.gift} />
      {giftUsers.length === 0 && data.words && data.words.length > 0 && (
        <p className="text-xs text-[var(--ink-mut)]">榜单数据来自数据库（data/data.db），直播运行中会自动积累。</p>
      )}
    </div>
  )
}
