/** schema 字段 → 表单控件。

 * 所有控件直接读写配置草稿（数字/列表例外，本地暂存原始输入）。
 * basePath 是「基座路径」：顶层字段为 []，动态配置组内的字段为 [组路径, 序号]，
 * 字段的 key 一律是相对基座的路径。
 */
import { useMemo, useState } from 'react'
import { api } from '../api/client'
import { getByPath, type Path } from '../lib/path'
import { useConfigStore } from '../state/configStore'
import { useActionStore } from '../state/actionStore'
import { useTestStore } from '../state/testStore'
import { notify, useConfirmStore } from '../state/ui'
import { resolveOptions, type Field } from '../schema/types'

const WIDTH_CLASS: Record<string, string> = {
  xs: 'w-36',
  sm: 'w-48',
  md: 'w-64',
  lg: 'w-96',
  xl: 'w-[540px]',
}

/** 与可见标签同款样式的隐形占位行：开关/按钮这类「无顶标签」字段也保留标签行高度，
 * 行内所有控件的顶基线（标签行下沿）对齐——混排不再高低错落。 */
function LabelSpacer() {
  return <span aria-hidden className="mb-1 block text-[13px] font-medium">&nbsp;</span>
}

function shell(field: Field, fieldId: string, control: React.ReactNode, extra?: React.ReactNode) {
  return (
    <div data-field-id={fieldId} className={`${WIDTH_CLASS[field.w ?? 'md']} max-w-full min-w-[9rem]`}>
      {field.kind === 'switch' || field.kind === 'action' ? (
        <LabelSpacer />
      ) : (
        <label className="mb-1 block text-[13px] font-medium text-[var(--ink)]">{field.label}</label>
      )}
      {control}
      {field.hint && <p className="mt-1 text-xs leading-relaxed text-[var(--ink-mut)]">{field.hint}</p>}
      {extra}
    </div>
  )
}

export function FieldControl({ field, fieldId, basePath = [] }: { field: Field; fieldId: string; basePath?: Path }) {
  const draft = useConfigStore((s) => s.draft)
  const value = draft ? getByPath(draft, [...basePath, ...field.key]) : undefined

  switch (field.kind) {
    case 'input':
      return shell(
        field,
        fieldId,
        <input
          className="inp"
          type={field.password ? 'password' : 'text'}
          value={value === null || value === undefined ? '' : String(value)}
          placeholder={field.placeholder}
          onChange={(e) => useConfigStore.getState().setValue([...basePath, ...field.key], e.target.value)}
        />,
      )

    case 'number':
      return <NumberField key={fieldId} field={field} fieldId={fieldId} basePath={basePath} />

    case 'select':
      return <SelectField field={field} fieldId={fieldId} basePath={basePath} />

    case 'switch':
      return shell(
        field,
        fieldId,
        <label className="switch">
          <input
            type="checkbox"
            checked={Boolean(value)}
            onChange={(e) => useConfigStore.getState().setValue([...basePath, ...field.key], e.target.checked)}
          />
          <span className="track" />
          <span className="text-[13px] font-medium">{field.label}</span>
        </label>,
      )

    case 'textarea':
      return shell(
        field,
        fieldId,
        <textarea
          className="inp"
          rows={4}
          value={value === null || value === undefined ? '' : String(value)}
          placeholder={field.placeholder}
          onChange={(e) => useConfigStore.getState().setValue([...basePath, ...field.key], e.target.value)}
        />,
      )

    case 'string-list':
      return <StringListField field={field} fieldId={fieldId} basePath={basePath} />

    case 'checkboxes':
      return <CheckboxesField field={field} fieldId={fieldId} basePath={basePath} />

    case 'frequency':
      return <FrequencyField field={field} fieldId={fieldId} basePath={basePath} />

    case 'action':
      return <ActionField field={field} fieldId={fieldId} basePath={basePath} />

    case 'file-json':
      return <FileJsonField field={field} fieldId={fieldId} basePath={basePath} />

    case 'group-list':
      return <GroupListField field={field} fieldId={fieldId} basePath={basePath} />

    case 'transient-input':
      return <TransientInput field={field} fieldId={fieldId} />
  }
}

/** 数字字段：本地暂存原始输入（允许打 "1." 这种中间态），失焦时归位。 */
function NumberField({ field, fieldId, basePath }: { field: Extract<Field, { kind: 'number' }>; fieldId: string; basePath: Path }) {
  const value = useConfigStore((s) => (s.draft ? getByPath(s.draft, [...basePath, ...field.key]) : undefined))
  const setValue = useConfigStore((s) => s.setValue)
  const [raw, setRaw] = useState<string | null>(null)

  const shown = raw ?? (value === null || value === undefined ? '' : String(value))

  const commit = (text: string) => {
    const t = text.trim()
    if (t === '') {
      setValue([...basePath, ...field.key], 0) // v2 语义：空值落 0
      return
    }
    const n = field.int ? parseInt(t, 10) : parseFloat(t)
    if (!Number.isNaN(n)) setValue([...basePath, ...field.key], field.int ? n : Math.round(n * 100) / 100)
  }

  return shell(
    field,
    fieldId,
    <input
      className="inp"
      inputMode="decimal"
      value={shown}
      placeholder={field.placeholder}
      onChange={(e) => {
        setRaw(e.target.value)
        commit(e.target.value)
      }}
      onBlur={() => setRaw(null)}
    />,
  )
}

function SelectField({ field, fieldId, basePath }: { field: Extract<Field, { kind: 'select' }>; fieldId: string; basePath: Path }) {
  const value = useConfigStore((s) => (s.draft ? getByPath(s.draft, [...basePath, ...field.key]) : undefined))
  const setValue = useConfigStore((s) => s.setValue)
  const dynamic = useActionStore((s) => (field.dynamicOptions ? s.options[field.dynamicOptions] : undefined))
  const current = value === null || value === undefined ? '' : String(value)

  const options = useMemo(() => {
    const base = { ...resolveOptions(field, value) }
    for (const item of dynamic ?? []) base[item] = base[item] ?? item
    // 配置里存的值已不在选项里（如老平台名）：保留为选项，不让老配置看起来是空的
    if (field.keepUnknown !== false && current !== '' && !(current in base)) {
      base[current] = `${current}（配置里的当前值）`
    }
    return base
  }, [field, value, dynamic, current])

  if (field.free) {
    // 可输入下拉（datalist）：模型名这类可手输项，对应 v2 的 with_input + add-unique
    return shell(
      field,
      fieldId,
      <>
        <input
          className="inp"
          value={current}
          list={fieldId}
          placeholder={field.placeholder}
          onChange={(e) => setValue([...basePath, ...field.key], e.target.value)}
        />
        <datalist id={fieldId}>
          {Object.entries(options).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </datalist>
      </>,
    )
  }

  return shell(
    field,
    fieldId,
    <select className="inp" value={current} onChange={(e) => setValue([...basePath, ...field.key], e.target.value)}>
      <option value="">（未选择）</option>
      {Object.entries(options).map(([k, v]) => (
        <option key={k} value={k}>
          {v}
        </option>
      ))}
    </select>,
  )
}

/** string[] 与多行文本互转：草稿里始终存规范化后的列表（去空白行），原始输入本地暂存。 */
function StringListField({ field, fieldId, basePath }: { field: Extract<Field, { kind: 'string-list' }>; fieldId: string; basePath: Path }) {
  const value = useConfigStore((s) => (s.draft ? getByPath(s.draft, [...basePath, ...field.key]) : undefined))
  const setValue = useConfigStore((s) => s.setValue)
  const [raw, setRaw] = useState<string | null>(null)

  const list = Array.isArray(value) ? (value as unknown[]) : []
  const shown = raw ?? list.map((v) => String(v)).join('\n')

  const handleChange = (text: string) => {
    setRaw(text)
    const normalized = text
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)
    setValue([...basePath, ...field.key], normalized)
  }

  return shell(
    field,
    fieldId,
    <textarea
      className="inp"
      rows={4}
      value={shown}
      placeholder={field.placeholder}
      onChange={(e) => handleChange(e.target.value)}
      onBlur={() => setRaw(null)}
    />,
  )
}

function CheckboxesField({ field, fieldId, basePath }: { field: Extract<Field, { kind: 'checkboxes' }>; fieldId: string; basePath: Path }) {
  const value = useConfigStore((s) => (s.draft ? getByPath(s.draft, [...basePath, ...field.key]) : undefined))
  const setValue = useConfigStore((s) => s.setValue)
  const selected = new Set(Array.isArray(value) ? (value as unknown[]).map(String) : [])

  const toggle = (key: string, on: boolean) => {
    const next = new Set(selected)
    if (on) next.add(key)
    else next.delete(key)
    setValue([...basePath, ...field.key], [...next])
  }

  return shell(
    field,
    fieldId,
    <div className="flex flex-wrap gap-x-5 gap-y-2 rounded-lg border border-slate-200 bg-slate-50/60 px-3 py-2.5">
      {Object.entries(field.options).map(([k, label]) => (
        <label key={k} className="flex items-center gap-1.5 text-[13px]">
          <input
            type="checkbox"
            className="h-3.5 w-3.5 accent-[var(--accent)]"
            checked={selected.has(k)}
            onChange={(e) => toggle(k, e.target.checked)}
          />
          {label}
        </label>
      ))}
    </div>,
  )
}

/** 周期触发复合控件：把「周期 min/max + 次数 min/max」四件套收成一行。
 * key 指向 periodic_trigger 对象基座，四个子键 periodic_time_min/max（秒）、trigger_num_min/max。 */
function FrequencyField({ field, fieldId, basePath }: { field: Extract<Field, { kind: 'frequency' }>; fieldId: string; basePath: Path }) {
  return shell(
    field,
    fieldId,
    <div className="flex flex-wrap items-center gap-x-2 gap-y-2 rounded-lg border border-slate-200 bg-slate-50/60 px-3.5 py-2.5 text-[13px]">
      <span className="text-[var(--ink-mut)]">每隔</span>
      <FreqNum field={field} basePath={basePath} sub="periodic_time_min" />
      <span className="text-[var(--ink-mut)]">~</span>
      <FreqNum field={field} basePath={basePath} sub="periodic_time_max" />
      <span>秒触发</span>
      <span className="mx-1.5 h-4 w-px bg-slate-300" aria-hidden />
      <span className="text-[var(--ink-mut)]">每次播</span>
      <FreqNum field={field} basePath={basePath} sub="trigger_num_min" />
      <span className="text-[var(--ink-mut)]">~</span>
      <FreqNum field={field} basePath={basePath} sub="trigger_num_max" />
      <span>条</span>
    </div>,
  )
}

function FreqNum({ field, basePath, sub }: { field: Extract<Field, { kind: 'frequency' }>; basePath: Path; sub: string }) {
  const value = useConfigStore((s) => (s.draft ? getByPath(s.draft, [...basePath, ...field.key, sub]) : undefined))
  const setValue = useConfigStore((s) => s.setValue)
  const [raw, setRaw] = useState<string | null>(null)
  const shown = raw ?? (value === null || value === undefined ? '' : String(value))

  return (
    <input
      className="inp w-[72px] px-2 py-1 text-center font-mono text-xs"
      inputMode="numeric"
      value={shown}
      onChange={(e) => {
        setRaw(e.target.value)
        const n = parseInt(e.target.value, 10)
        if (!Number.isNaN(n)) setValue([...basePath, ...field.key, sub], n)
      }}
      onBlur={() => setRaw(null)}
    />
  )
}

/** $transient 引用：精确匹配 fieldId，匹配不到时按后缀匹配（动态组内的临时输入框带序号前缀）。 */
function transientValue(transient: Record<string, string>, ref: string): string {
  if (ref in transient) return transient[ref]
  const suffix = '__' + ref
  const hit = Object.keys(transient).find((k) => k.endsWith(suffix))
  return hit ? transient[hit] : ''
}

/** 动作按钮：从草稿取参数调后端，回填动态选项 / 弹结果。 */
const ACTION_OPTIONS_KEY: Partial<Record<string, string>> = {
  'llm-models': 'llm-models',
  'window-titles': 'window-titles',
  cameras: 'cameras',
  'config-templates': 'config-templates',
  'anythingllm-workspaces': 'anythingllm-slugs',
  'serial-ports': 'serial-ports',
}

function ActionField({ field, fieldId, basePath }: { field: Extract<Field, { kind: 'action' }>; fieldId: string; basePath: Path }) {
  const [busy, setBusy] = useState(false)
  const ask = useConfirmStore((s) => s.ask)

  const run = async () => {
    const { draft } = useConfigStore.getState()
    const { transient } = useActionStore.getState()
    const params: Record<string, unknown> = {}
    for (const [name, spec] of Object.entries(field.params ?? {})) {
      if (typeof spec === 'string' && spec.startsWith('$transient:')) {
        params[name] = transientValue(transient, spec.slice('$transient:'.length))
      } else {
        params[name] = draft ? getByPath(draft, [...basePath, ...(spec as Path)]) : undefined
      }
    }

    setBusy(true)
    try {
      const resp = await api.action(field.action, params)
      // LLM 测试结果记账：选卡墙/信号链据此显示「已测通」
      if (field.action === 'llm-test') {
        const engine = String(getByPath(useConfigStore.getState().draft ?? {}, ['chat_type']) ?? '')
        if (engine) {
          useTestStore.getState().record('llm', engine, resp.code === 200, resp.message ?? '')
        }
      }
      const optionsKey = ACTION_OPTIONS_KEY[field.action]
      if (optionsKey && resp.code === 200) {
        const items = (resp.items ?? resp.models ?? []) as string[]
        useActionStore.getState().setOptions(optionsKey, items)
        const note =
          field.action === 'llm-models'
            ? `取到 ${items.length} 个模型，已填进左边的下拉框（也始终可以手输）`
            : field.action === 'config-templates'
              ? `找到 ${items.length} 个模板文件`
              : (resp.message ?? '已完成')
        notify.ok(note)
      } else if (resp.code === 200) {
        notify.ok(resp.message ?? '操作成功')
      } else {
        notify.warn(resp.message ?? '操作失败')
      }
    } catch {
      notify.err('操作失败：连不上后端')
    } finally {
      setBusy(false)
    }
  }

  return shell(
    field,
    fieldId,
    <button
      className="h-fit rounded-lg border border-slate-300 bg-white px-3.5 py-2 text-[13px] font-medium text-[var(--ink)] shadow-sm transition hover:border-[var(--accent)] hover:text-[var(--accent)] disabled:opacity-50"
      disabled={busy}
      onClick={() => {
        if (field.confirm) {
          ask(field.label, () => void run(), field.confirm)
        } else {
          void run()
        }
      }}
    >
      {busy ? '执行中…' : field.label}
    </button>,
  )
}

/** 本地问答 JSON 这类外部文件编辑器：显式加载/保存，不走配置保存链路。 */
function FileJsonField({ field, fieldId, basePath }: { field: Extract<Field, { kind: 'file-json' }>; fieldId: string; basePath: Path }) {
  const path = useConfigStore((s) => (s.draft ? String(getByPath(s.draft, [...basePath, ...field.key]) ?? '') : ''))
  const [content, setContent] = useState<string>('')
  const [busy, setBusy] = useState(false)

  const load = async () => {
    if (!path.trim()) {
      notify.warn('先在上面填 JSON 文件路径')
      return
    }
    setBusy(true)
    try {
      const resp = await api.fileGet(path)
      if (resp.code !== 200) {
        notify.err(resp.message ?? '读取失败')
        return
      }
      try {
        setContent(JSON.stringify(JSON.parse(resp.content), null, 2))
      } catch {
        setContent(resp.content) // 不是合法 JSON 就原样给，让用户自己修
      }
      notify.ok('文件已加载')
    } finally {
      setBusy(false)
    }
  }

  const save = async () => {
    try {
      JSON.parse(content)
    } catch (e) {
      notify.err(`JSON 语法不对，没写入文件：${e}`)
      return
    }
    setBusy(true)
    try {
      const resp = await api.filePut(path, content)
      resp.code === 200 ? notify.ok(resp.message ?? '已保存') : notify.err(resp.message ?? '写入失败')
    } finally {
      setBusy(false)
    }
  }

  return shell(
    field,
    fieldId,
    <div className="w-[560px] max-w-full">
      <textarea
        className="inp font-mono text-xs"
        rows={12}
        value={content}
        placeholder="点「加载文件」把 JSON 文件内容读进来；改完点「保存到文件」写回去。这份内容不进 config.json，也不走右下角的「保存配置」。"
        onChange={(e) => setContent(e.target.value)}
      />
      <div className="mt-2 flex items-center gap-2">
        <button
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium hover:border-[var(--accent)] hover:text-[var(--accent)] disabled:opacity-50"
          disabled={busy}
          onClick={() => void load()}
        >
          加载文件
        </button>
        <button
          className="rounded-lg px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
          style={{ background: 'var(--accent)' }}
          disabled={busy}
          onClick={() => void save()}
        >
          保存到文件
        </button>
        <span className="truncate text-xs text-[var(--ink-mut)]">{path || '（先填上面的文件路径）'}</span>
      </div>
    </div>,
  )
}

/** 动态配置组：config 里的对象数组，增删改条目。 */
function GroupListField({ field, fieldId, basePath }: { field: Extract<Field, { kind: 'group-list' }>; fieldId: string; basePath: Path }) {
  const value = useConfigStore((s) => (s.draft ? getByPath(s.draft, [...basePath, ...field.key]) : undefined))
  const setValue = useConfigStore((s) => s.setValue)
  const ask = useConfirmStore((s) => s.ask)
  const items: unknown[] = Array.isArray(value) ? (value as unknown[]) : []

  const fullPath = [...basePath, ...field.key]
  const add = () => setValue(fullPath, [...items, structuredClone(field.itemDefaults)])
  const remove = (index: number) => {
    ask(
      `确认删除 ${field.itemTitle ?? '配置组'}#${index + 1}？`,
      () => setValue(fullPath, items.filter((_, j) => j !== index)),
      '删的是界面上的这一组配置，保存后才会写进配置文件。',
    )
  }

  return (
    <div data-field-id={fieldId} className="w-full max-w-full">
      {field.hint && <p className="mb-2 text-xs leading-relaxed text-[var(--ink-mut)]">{field.hint}</p>}
      {field.itemDesc && <p className="mb-2 text-xs text-[var(--ink-mut)]">{field.itemDesc}</p>}
      <div className="flex flex-col gap-3">
        {items.map((_, i) => (
          <div key={i} className="rounded-xl border border-slate-200 bg-slate-50/70 p-3.5">
            <div className="mb-2 flex items-center justify-between">
              <span className="text-[13px] font-semibold text-[var(--ink)]">
                {field.itemTitle ?? '配置组'} #{i + 1}
              </span>
              <button
                className="rounded-md border border-red-200 px-2 py-0.5 text-xs text-red-600 transition hover:bg-red-50"
                onClick={() => remove(i)}
              >
                删除
              </button>
            </div>
            {(field.rows ?? []).map((row, r) => (
              <div key={r} className="mb-2 flex flex-wrap items-start gap-x-5 gap-y-3 last:mb-0">
                {row.map((sub, c) => (
                  <FieldControl
                    key={c}
                    field={sub}
                    fieldId={`${fieldId}__${i}__${sub.key.join('.')}`}
                    basePath={[...fullPath, i]}
                  />
                ))}
              </div>
            ))}
          </div>
        ))}
        <button
          className="self-start rounded-lg border border-dashed border-slate-400 px-4 py-1.5 text-[13px] font-medium text-[var(--ink-mut)] transition hover:border-[var(--accent)] hover:text-[var(--accent)]"
          onClick={add}
        >
          ＋ {field.addLabel ?? '增加配置组'}
        </button>
      </div>
    </div>
  )
}

/** 临时输入框：值只存在内存里（串口调试的发送数据这类）。 */
function TransientInput({ field, fieldId }: { field: Extract<Field, { kind: 'transient-input' }>; fieldId: string }) {
  const value = useActionStore((s) => s.transient[fieldId] ?? '')
  const setTransient = useActionStore((s) => s.setTransient)
  return shell(
    field,
    fieldId,
    <input className="inp" value={value} placeholder={field.placeholder} onChange={(e) => setTransient(fieldId, e.target.value)} />,
  )
}
