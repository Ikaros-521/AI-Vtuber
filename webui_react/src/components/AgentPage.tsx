/** Agent 工作台（v5）：总控 / 工具卡片墙 / 记忆管理 / 决策回放。

 * 配置类改动（总开关、工具白名单、预算参数）一律走 useConfigStore 草稿，
 * 顶栏统一保存；运行态（急停、决策回放）与记忆数据走 /api/agent/*，
 * 互不混淆。持久开关保存后需重启程序生效，急停是主进程内即时生效。
 */
import { useCallback, useEffect, useState } from 'react'
import {
  api,
  type AgentHighlight,
  type AgentOverviewResult,
  type AgentStats,
  type AgentTraceRecord,
  type AgentViewer,
} from '../api/client'

interface ReportMeta {
  id: number
  ts: string
  window_date: string
  size: number
}

interface RagInfo {
  enabled: boolean
  dir?: string
  files?: string[]
  chunks?: number
}

interface McpInfo {
  enabled: boolean
  servers: { name: string; state: string; error: string; tools: string[] }[]
}
import { getByPath, type JsonObject } from '../lib/path'
import { useConfigStore } from '../state/configStore'
import { notify, useConfirmStore } from '../state/ui'

function cfgStr(draft: JsonObject | null, path: (string | number)[], fallback = ''): string {
  const value = getByPath(draft ?? {}, path)
  return typeof value === 'string' ? value : value == null ? fallback : String(value)
}

function cfgNum(draft: JsonObject | null, path: (string | number)[], fallback: number): number {
  const value = getByPath(draft ?? {}, path)
  const num = typeof value === 'number' ? value : Number(value)
  return Number.isFinite(num) ? num : fallback
}

/** 区块标题行：标题 + 说明 + 右侧动作。 */
function BlockHead({ title, desc, extra }: { title: string; desc: string; extra?: React.ReactNode }) {
  return (
    <div className="mb-3 flex items-center gap-2">
      <h2 className="text-[15px] font-semibold">{title}</h2>
      <span className="text-xs text-[var(--ink-mut)]">{desc}</span>
      <span className="ml-auto flex items-center gap-2">{extra}</span>
    </div>
  )
}

const BTN =
  'rounded-lg border border-slate-200 px-3 py-1.5 text-[12.5px] transition hover:border-[color-mix(in_srgb,var(--accent)_45%,#e4e7ec)] disabled:opacity-50'

export function AgentPage() {
  const draft = useConfigStore((s) => s.draft)
  const setValue = useConfigStore((s) => s.setValue)

  const [overview, setOverview] = useState<AgentOverviewResult | null>(null)
  const [trace, setTrace] = useState<AgentTraceRecord[] | null>(null)
  const [stats, setStats] = useState<AgentStats | null>(null)
  const [reports, setReports] = useState<ReportMeta[] | null>(null)
  const [reportContent, setReportContent] = useState<string | null>(null)
  const [reviewBusy, setReviewBusy] = useState(false)
  const [useLlm, setUseLlm] = useState(true)
  const [rag, setRag] = useState<RagInfo | null>(null)
  const [ragFile, setRagFile] = useState<string | null>(null)
  const [ragContent, setRagContent] = useState('')
  const [mcp, setMcp] = useState<McpInfo | null>(null)
  const [expandedTrace, setExpandedTrace] = useState<string | null>(null)
  const [viewers, setViewers] = useState<AgentViewer[] | null>(null)
  const [highlights, setHighlights] = useState<AgentHighlight[] | null>(null)
  const [keyword, setKeyword] = useState('')
  const [editingKey, setEditingKey] = useState<string | null>(null)
  const [noteDraftValue, setNoteDraftValue] = useState('')
  const [busy, setBusy] = useState(false)

  const runtime = overview?.runtime ?? null
  const enabledTools = Array.isArray(getByPath(draft ?? {}, ['agent', 'tools', 'enabled']))
    ? ((getByPath(draft ?? {}, ['agent', 'tools', 'enabled']) as string[]) ?? [])
    : []
  const agentEnabled = Boolean(getByPath(draft ?? {}, ['agent', 'enabled']))

  const loadOverview = useCallback(async () => {
    const resp = await api.agentOverview()
    if (resp.code === 200) setOverview(resp)
    else notify.err(resp.message || '读取 Agent 总览失败')
  }, [])

  const loadTrace = useCallback(async () => {
    const [traceResp, statsResp] = await Promise.all([api.agentTrace(), api.agentStats()])
    setTrace(traceResp.code === 200 ? traceResp.records : [])
    if (statsResp.code === 200) setStats(statsResp)
    return traceResp
  }, [])

  const loadMemory = useCallback(async (kw: string) => {
    const [viewerResp, highlightResp] = await Promise.all([api.agentViewers(kw), api.agentHighlights()])
    if (viewerResp.code === 200) setViewers(viewerResp.viewers)
    if (highlightResp.code === 200) setHighlights(highlightResp.highlights)
  }, [])

  const loadRag = useCallback(async () => {
    const resp = await api.ragStatus()
    if (resp.code === 200) setRag(resp)
  }, [])

  const loadMcp = useCallback(async () => {
    const resp = await api.mcpStatus()
    if (resp.code === 200) setMcp(resp)
  }, [])

  const loadReports = useCallback(async () => {
    const resp = await api.reviewList()
    if (resp.code === 200) setReports(resp.reports)
    else setReports([])
  }, [])

  useEffect(() => {
    void loadOverview()
    void loadMemory('')
    void loadTrace()
    void loadReports()
    void loadRag()
    void loadMcp()
  }, [loadOverview, loadMemory, loadTrace, loadReports, loadRag, loadMcp])

  // ---------- 总控 ----------

  const setAgentEnabled = (next: boolean) => {
    setValue(['agent', 'enabled'], next)
    notify.info(`Agent 总开关已${next ? '开启' : '关闭'} · 保存并重启程序后生效`)
  }

  const killToggle = async () => {
    if (!runtime) {
      notify.warn('主进程未在运行，无需急停')
      return
    }
    setBusy(true)
    const resp = await api.agentKill(!runtime.killed)
    setBusy(false)
    if (resp.code === 200) {
      notify.ok(resp.message || '已执行')
      void loadOverview()
    } else {
      notify.err(resp.message || '操作失败')
    }
  }

  const setNum = (path: (string | number)[], value: string, fallback: number) => {
    const num = Number(value)
    setValue(path, Number.isFinite(num) && value !== '' ? num : fallback)
  }

  // ---------- 工具卡片墙 ----------

  const toggleTool = (name: string, next: boolean) => {
    const arr = next ? [...enabledTools, name] : enabledTools.filter((n) => n !== name)
    setValue(['agent', 'tools', 'enabled'], arr)
    notify.info(`工具「${name}」已${next ? '启用' : '停用'} · 记得保存`)
  }

  // ---------- 记忆管理 ----------

  const saveNote = async (viewer: AgentViewer) => {
    setBusy(true)
    const resp = await api.agentSetNote(viewer.platform, viewer.username, noteDraftValue)
    setBusy(false)
    if (resp.code === 200) {
      notify.ok('备注已保存')
      setEditingKey(null)
      void loadMemory(keyword)
    } else {
      notify.err(resp.message || '保存失败')
    }
  }

  const deleteViewer = (viewer: AgentViewer) => {
    useConfirmStore.getState().ask('删除观众画像', async () => {
      const resp = await api.agentDeleteViewer(viewer.platform, viewer.username)
      if (resp.code === 200) {
        notify.ok('已删除')
        void loadMemory(keyword)
      } else {
        notify.err(resp.message || '删除失败')
      }
    }, `将删除「${viewer.username}」的画像与备注，Agent 之后的回应不再记得此人。`)
  }

  const deleteHighlight = (item: AgentHighlight) => {
    useConfirmStore.getState().ask('删除高光', async () => {
      const resp = await api.agentDeleteHighlight(item.row_id)
      if (resp.code === 200) {
        notify.ok('已删除')
        void loadMemory(keyword)
      } else {
        notify.err(resp.message || '删除失败')
      }
    }, '将删除这条高光记录。')
  }

  return (
    <div className="space-y-6">
      {/* ---------- 总控 ---------- */}
      <section className="card-surface p-5">
        <BlockHead
          title="总控"
          desc="Agent 决策域的持久开关与预算参数"
          extra={
            <>
              <span
                className="rounded-full px-2.5 py-0.5 text-[11px]"
                style={{
                  background: overview?.running
                    ? 'color-mix(in srgb, var(--ok) 14%, white)'
                    : 'var(--ink-mut)1a',
                  color: overview?.running ? 'var(--ok)' : 'var(--ink-mut)',
                }}
              >
                {overview?.running ? '主进程运行中' : '主进程未运行'}
              </span>
              {overview?.running && runtime && (
                <button className={BTN} disabled={busy} onClick={() => void killToggle()}
                  style={runtime.killed ? { borderColor: 'var(--ok)', color: 'var(--ok)' } : { borderColor: 'var(--warn)', color: 'var(--warn)' }}>
                  {runtime.killed ? '已急停 · 点击恢复' : '一键急停'}
                </button>
              )}
            </>
          }
        />
        <div className="flex items-center gap-3">
          <label className="switch">
            <input type="checkbox" checked={agentEnabled} onChange={(e) => setAgentEnabled(e.target.checked)} />
            <span className="track" />
          </label>
          <span className="text-[13.5px] font-medium">启用 Agent（模型自主决策 + 工具调用）</span>
          <span className="text-xs text-[var(--ink-mut)]">关闭后走原有规则链路 · 保存并重启后生效</span>
        </div>

        <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
          <label className="block">
            <span className="mb-1 block text-xs text-[var(--ink-mut)]">工具循环轮次上限</span>
            <input
              className="inp w-full"
              type="number"
              min={1}
              max={8}
              value={cfgNum(draft, ['agent', 'max_tool_rounds'], 3)}
              onChange={(e) => setNum(['agent', 'max_tool_rounds'], e.target.value, 3)}
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs text-[var(--ink-mut)]">单次决策超时（秒）</span>
            <input
              className="inp w-full"
              type="number"
              min={2}
              max={60}
              value={cfgNum(draft, ['agent', 'timeout_seconds'], 8)}
              onChange={(e) => setNum(['agent', 'timeout_seconds'], e.target.value, 8)}
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs text-[var(--ink-mut)]">小时预算（token 折算，0=不限）</span>
            <input
              className="inp w-full"
              type="number"
              min={0}
              value={cfgNum(draft, ['agent', 'budget', 'tokens_per_hour'], 0)}
              onChange={(e) => setNum(['agent', 'budget', 'tokens_per_hour'], e.target.value, 0)}
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-xs text-[var(--ink-mut)]">LLM 通道</span>
            <select
              className="inp w-full"
              value={cfgStr(draft, ['agent', 'llm', 'channel'], 'auto')}
              onChange={(e) => setValue(['agent', 'llm', 'channel'], e.target.value)}
            >
              <option value="auto">自动（支持 FC 用原生）</option>
              <option value="native">原生 Function Calling</option>
              <option value="text">文本协议（全模型兼容）</option>
            </select>
          </label>
        </div>
        <label className="mt-3 block">
          <span className="mb-1 block text-xs text-[var(--ink-mut)]">人设补充（留空则沿用基础设置的人设提示词）</span>
          <textarea
            className="inp w-full"
            rows={2}
            value={cfgStr(draft, ['agent', 'persona'])}
            onChange={(e) => setValue(['agent', 'persona'], e.target.value)}
            placeholder="例如：你是直播间的主播小助手，说话简短热情……"
          />
        </label>
        {runtime && (
          <p className="mt-3 text-xs text-[var(--ink-mut)]">
            实时状态：已启用工具 {runtime.tools_enabled.length} 个 · 本小时已用约 {runtime.hour_used} token
            {runtime.hour_limit > 0 ? ` / ${runtime.hour_limit}` : '（不限）'} · 最近决策 {runtime.recent_trace_count} 条
            {runtime.killed ? ' · 已急停' : ''}
          </p>
        )}
      </section>

      {/* ---------- 工具卡片墙 ---------- */}
      <section className="card-surface p-5">
        <BlockHead title="工具管理" desc="模型能调用哪些能力，白名单之外的工具模型看不见也不会执行" />
        <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
          {(overview?.tool_catalog ?? []).map((tool) => {
            const on = enabledTools.includes(tool.name)
            return (
              <div
                key={tool.name}
                className="card-surface p-4 transition"
                style={on ? { borderColor: 'color-mix(in srgb, var(--accent) 45%, #e4e7ec)' } : undefined}
              >
                <div className="flex items-center gap-2.5">
                  <span className="text-[14px] font-semibold">{tool.name}</span>
                  {tool.dangerous && (
                    <span className="rounded-full px-2 py-0.5 text-[11px]" style={{ background: 'color-mix(in srgb, var(--warn) 14%, white)', color: 'var(--warn)' }}>
                      危险动作
                    </span>
                  )}
                  <label className="switch ml-auto">
                    <input type="checkbox" checked={on} onChange={(e) => toggleTool(tool.name, e.target.checked)} />
                    <span className="track" />
                  </label>
                </div>
                <p className="mt-1.5 text-xs leading-relaxed text-[var(--ink-mut)]">{tool.description}</p>
              </div>
            )
          })}
          {!overview && <p className="text-xs text-[var(--ink-mut)]">加载工具目录中……</p>}
        </div>
      </section>

      {/* ---------- 记忆管理 ---------- */}
      <section className="card-surface p-5">
        <BlockHead
          title="记忆管理"
          desc="观众画像与直播高光；记忆可解释、可编辑，是 Agent 的信任底线"
          extra={
            <input
              className="inp w-52"
              placeholder="搜索观众名……"
              value={keyword}
              onChange={(e) => {
                setKeyword(e.target.value)
                void loadMemory(e.target.value)
              }}
            />
          }
        />
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-slate-200 text-left text-xs text-[var(--ink-mut)]">
                <th className="py-2 pr-3 font-medium">观众</th>
                <th className="py-2 pr-3 font-medium">平台</th>
                <th className="py-2 pr-3 font-medium">互动次数</th>
                <th className="py-2 pr-3 font-medium">最近互动</th>
                <th className="py-2 pr-3 font-medium">备注（Agent 会看到）</th>
                <th className="py-2 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {(viewers ?? []).map((viewer) => {
                const key = `${viewer.platform}/${viewer.username}`
                return (
                  <tr key={key} className="border-b border-slate-100">
                    <td className="py-2 pr-3 font-medium">{viewer.username}</td>
                    <td className="py-2 pr-3 text-[var(--ink-mut)]">{viewer.platform}</td>
                    <td className="py-2 pr-3">{viewer.interactions}</td>
                    <td className="py-2 pr-3 text-xs text-[var(--ink-mut)]">{viewer.last_seen.slice(0, 16)}</td>
                    <td className="py-2 pr-3">
                      {editingKey === key ? (
                        <span className="flex items-center gap-2">
                          <input className="inp w-full" value={noteDraftValue} onChange={(e) => setNoteDraftValue(e.target.value)} />
                          <button className={BTN} disabled={busy} onClick={() => void saveNote(viewer)}>保存</button>
                          <button className={BTN} onClick={() => setEditingKey(null)}>取消</button>
                        </span>
                      ) : (
                        viewer.note || <span className="text-[var(--ink-mut)]">—</span>
                      )}
                    </td>
                    <td className="py-2">
                      <span className="flex gap-2">
                        <button
                          className={BTN}
                          onClick={() => {
                            setEditingKey(key)
                            setNoteDraftValue(viewer.note)
                          }}
                        >
                          编辑
                        </button>
                        <button className={BTN} onClick={() => deleteViewer(viewer)} style={{ color: 'var(--warn)' }}>
                          删除
                        </button>
                      </span>
                    </td>
                  </tr>
                )
              })}
              {viewers != null && viewers.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-4 text-center text-xs text-[var(--ink-mut)]">
                    还没有观众画像；开启 Agent 并有互动后会自动建档
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {highlights != null && highlights.length > 0 && (
          <div className="mt-5">
            <p className="mb-2 text-xs font-medium text-[var(--ink-mut)]">直播高光时间线</p>
            <div className="space-y-2">
              {highlights.map((item) => (
                <div key={item.row_id} className="flex items-center gap-3 rounded-xl border border-slate-100 px-3 py-2">
                  <span className="text-xs text-[var(--ink-mut)]">{item.ts.slice(5, 16)}</span>
                  <span className="text-[13px]">{item.content}</span>
                  {item.username && <span className="text-xs text-[var(--ink-mut)]">· {item.username}</span>}
                  <button className={`${BTN} ml-auto`} onClick={() => deleteHighlight(item)}>
                    删除
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </section>

      {/* ---------- 人设知识库 ---------- */}
      <section className="card-surface p-5">
        <BlockHead
          title="人设知识库"
          desc="markdown 知识文件；直播时 Agent 按弹幕话题检索相关知识遵循"
          extra={
            rag?.enabled ? (
              <span className="text-xs text-[var(--ink-mut)]">
                {rag.files?.length ?? 0} 个文件 · {rag.chunks ?? 0} 块
              </span>
            ) : (
              <span className="text-xs text-[var(--ink-mut)]">未启用（config.agent.rag.enabled）</span>
            )
          }
        />
        {rag?.enabled && (
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <select
                className="inp w-auto text-[12.5px]"
                value={ragFile ?? ''}
                onChange={async (e) => {
                  const name = e.target.value
                  setRagFile(name || null)
                  if (name) {
                    const resp = await api.ragGetFile(name)
                    if (resp.code === 200) setRagContent(resp.content)
                  } else {
                    setRagContent('')
                  }
                }}
              >
                <option value="">选择文件 / 新建……</option>
                {(rag.files ?? []).map((f) => (
                  <option key={f} value={f}>
                    {f}
                  </option>
                ))}
              </select>
              {ragFile != null && (
                <button
                  className={BTN}
                  onClick={async () => {
                    const resp = await api.ragSaveFile(ragFile, ragContent)
                    if (resp.code === 200) {
                      notify.ok('知识文件已保存')
                      void loadRag()
                    } else {
                      notify.err(resp.message || '保存失败')
                    }
                  }}
                >
                  保存
                </button>
              )}
              {ragFile != null && (
                <button
                  className={BTN}
                  style={{ color: 'var(--warn)' }}
                  onClick={() => {
                    useConfirmStore.getState().ask('删除知识文件', async () => {
                      const resp = await api.ragDeleteFile(ragFile)
                      if (resp.code === 200) {
                        notify.ok('已删除')
                        setRagFile(null)
                        setRagContent('')
                        void loadRag()
                      } else {
                        notify.err(resp.message || '删除失败')
                      }
                    }, `将删除知识文件「${ragFile}」。`)
                  }}
                >
                  删除
                </button>
              )}
            </div>
            {ragFile != null && (
              <textarea
                className="inp w-full font-mono text-[12.5px]"
                rows={10}
                value={ragContent}
                onChange={(e) => setRagContent(e.target.value)}
                placeholder={'# 主播设定\n直播间规矩：……\n口头禅：……'}
              />
            )}
          </div>
        )}
      </section>

      {/* ---------- MCP 工具生态 ---------- */}
      <section className="card-surface p-5">
        <BlockHead
          title="MCP 工具生态"
          desc="外部 MCP server 的工具并入 Agent 工具清单（server 级信任）；在 config.agent.mcp 配置 servers"
          extra={
            mcp?.enabled ? (
              <span className="text-xs text-[var(--ink-mut)]">{mcp.servers.length} 个 server</span>
            ) : (
              <span className="text-xs text-[var(--ink-mut)]">未启用（config.agent.mcp.enabled）</span>
            )
          }
        />
        {mcp?.enabled && (
          <div className="space-y-2">
            {mcp.servers.length === 0 && <p className="text-xs text-[var(--ink-mut)]">还没有接入的 MCP server。</p>}
            {mcp.servers.map((server) => (
              <div key={server.name} className="flex flex-wrap items-center gap-2 rounded-xl border border-slate-100 px-3 py-2">
                <span className="text-[13px] font-medium">{server.name}</span>
                <span
                  className="rounded-full px-2 py-0.5 text-[11px]"
                  style={
                    server.state === 'ready'
                      ? { background: 'color-mix(in srgb, var(--ok) 14%, white)', color: 'var(--ok)' }
                      : { background: 'color-mix(in srgb, var(--warn) 14%, white)', color: 'var(--warn)' }
                  }
                >
                  {server.state}
                  {server.error ? ` · ${server.error}` : ''}
                </span>
                <span className="text-xs text-[var(--ink-mut)]">{server.tools.length} 个工具</span>
                {server.tools.length > 0 && <code className="text-[11px] text-[var(--ink-mut)]">{server.tools.join('、')}</code>}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ---------- 直播复盘 ---------- */}
      <section className="card-surface p-5">
        <BlockHead
          title="直播复盘"
          desc="按日聚合弹幕/礼物/入场/Agent 决策，可选 AI 总结与建议"
          extra={
            <>
              <label className="flex items-center gap-1.5 text-xs text-[var(--ink-mut)]">
                <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} />
                AI 总结
              </label>
              <button
                className={BTN}
                disabled={reviewBusy || !overview?.running}
                title={overview?.running ? undefined : '需要主程序在运行中'}
                onClick={async () => {
                  setReviewBusy(true)
                  try {
                    const resp = await api.reviewGenerate(useLlm)
                    if (resp.code === 200) {
                      setReportContent(resp.content)
                      notify.ok('复盘已生成并保存')
                      void loadReports()
                    } else {
                      notify.err(resp.message || '生成失败')
                    }
                  } finally {
                    setReviewBusy(false)
                  }
                }}
              >
                {reviewBusy ? '生成中……' : '生成本场复盘'}
              </button>
            </>
          }
        />
        {reports != null && reports.length > 0 && (
          <select
            className="inp mb-3 w-auto text-[12.5px]"
            onChange={async (e) => {
              const id = Number(e.target.value)
              if (!id) {
                setReportContent(null)
                return
              }
              const resp = await api.reviewGet(id)
              if (resp.code === 200) setReportContent(resp.content)
              else notify.err(resp.message || '读取复盘失败')
            }}
          >
            <option value="">历史复盘（{reports.length}）</option>
            {reports.map((r) => (
              <option key={r.id} value={r.id}>
                #{r.id} · {r.window_date} · {r.ts.slice(5, 16)}
              </option>
            ))}
          </select>
        )}
        {reportContent == null && <p className="text-xs text-[var(--ink-mut)]">还没有复盘记录；直播后点「生成本场复盘」，报告会存档在这里。</p>}
        {reportContent != null && (
          <pre className="whitespace-pre-wrap rounded-xl border border-slate-100 bg-slate-50 p-4 font-sans text-[13px] leading-relaxed">
            {reportContent}
          </pre>
        )}
      </section>

      {/* ---------- 决策回放 ---------- */}
      <section className="card-surface p-5">
        <BlockHead
          title="决策回放"
          desc="Agent 每次决策的输入/工具调用/耗时，排查「为什么它这么说」全靠这里"
          extra={
            <>
              {stats && (
                <span className="flex items-center gap-2 text-[11px] text-[var(--ink-mut)]">
                  <span>决策 {stats.total}</span>
                  <span style={{ color: stats.degrade_rate > 20 ? 'var(--warn)' : undefined }}>
                    降级率 {stats.degrade_rate}%
                  </span>
                  {stats.fallback_used > 0 && <span>备用模型 {stats.fallback_used}</span>}
                  {stats.small_routed > 0 && <span>小模型直答 {stats.small_routed}</span>}
                  <span>工具 {stats.tool_ok}/{stats.tool_total}</span>
                  <span>均 {stats.avg_ms}ms</span>
                </span>
              )}
              <span className="text-xs text-[var(--ink-mut)]">保留最近 200 条</span>
              <button className={BTN} onClick={() => void loadTrace()}>刷新</button>
            </>
          }
        />
        {trace == null && <p className="text-xs text-[var(--ink-mut)]">加载中……</p>}
        {trace != null && trace.length === 0 && (
          <p className="text-xs text-[var(--ink-mut)]">还没有决策记录；开启 Agent 并有弹幕互动后，这里会出现每次决策的回放。</p>
        )}
        <div className="space-y-2">
          {(trace ?? []).map((record) => {
            const open = expandedTrace === record.ts + record.username
            return (
              <div key={record.ts + record.username + record.duration_ms} className="rounded-xl border border-slate-100">
                <button className="flex w-full items-center gap-2.5 px-3 py-2 text-left" onClick={() => setExpandedTrace(open ? null : record.ts + record.username)}>
                  <span className="text-xs text-[var(--ink-mut)]">{record.ts.slice(5, 19)}</span>
                  <span className="text-[13px] font-medium">{record.username || '—'}</span>
                  <span
                    className="rounded-full px-2 py-0.5 text-[11px]"
                    style={
                      record.degraded
                        ? { background: 'color-mix(in srgb, var(--warn) 14%, white)', color: 'var(--warn)' }
                        : { background: 'color-mix(in srgb, var(--ok) 14%, white)', color: 'var(--ok)' }
                    }
                  >
                    {record.degraded ? `降级 · ${record.reason || '未知原因'}` : '接管'}
                  </span>
                  {record.tool_calls.length > 0 && (
                    <span className="text-xs text-[var(--ink-mut)]">调用 {record.tool_calls.map((tc) => tc.name).join('、')}</span>
                  )}
                  <span className="ml-auto text-xs text-[var(--ink-mut)]">{record.duration_ms.toFixed(0)}ms</span>
                </button>
                {open && (
                  <div className="border-t border-slate-100 px-3 py-2 text-xs leading-relaxed text-[var(--ink-mut)]">
                    <p>来源：{record.source} · 输入约 {record.prompt_chars} 字 · 输出 {record.output_chars} 字</p>
                    {record.tool_calls.map((tc, idx) => (
                      <p key={idx} style={{ color: tc.ok ? undefined : 'var(--warn)' }}>
                        · {tc.name}（{tc.ms.toFixed(0)}ms{tc.ok ? '' : '，失败'}）{tc.args_digest ? ` 参数：${tc.args_digest}` : ''}
                      </p>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </section>
    </div>
  )
}
