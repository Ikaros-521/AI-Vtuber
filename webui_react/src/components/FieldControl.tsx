/** schema 字段 → 表单控件。所有控件直接读写配置草稿，无本地副本（数字/列表例外）。 */
import { useState } from 'react'
import { useConfigStore } from '../state/configStore'
import { getByPath } from '../lib/path'
import { resolveOptions, type Field } from '../schema/types'

const WIDTH_CLASS: Record<string, string> = {
  xs: 'w-36',
  sm: 'w-48',
  md: 'w-64',
  lg: 'w-96',
  xl: 'w-[540px]',
}

function shell(field: Field, fieldId: string, control: React.ReactNode) {
  return (
    <div data-field-id={fieldId} className={`${WIDTH_CLASS[field.w ?? 'md']} max-w-full min-w-[11rem]`}>
      {field.kind !== 'switch' && (
        <label className="mb-1 block text-[13px] font-medium text-[var(--ink)]">{field.label}</label>
      )}
      {control}
      {field.hint && <p className="mt-1 text-xs leading-relaxed text-[var(--ink-mut)]">{field.hint}</p>}
    </div>
  )
}

export function FieldControl({ field, fieldId }: { field: Field; fieldId?: string }) {
  const id = fieldId ?? field.key.join('.')
  const draft = useConfigStore((s) => s.draft)
  const setValue = useConfigStore((s) => s.setValue)
  const value = draft ? getByPath(draft, field.key) : undefined

  switch (field.kind) {
    case 'input':
      return shell(
        field,
        id,
        <input
          className="inp"
          type={field.password ? 'password' : 'text'}
          value={value === null || value === undefined ? '' : String(value)}
          placeholder={field.placeholder}
          onChange={(e) => setValue(field.key, e.target.value)}
        />,
      )

    case 'number':
      return <NumberField field={field} fieldId={id} />

    case 'select':
      return <SelectField field={field} fieldId={id} />

    case 'switch':
      return shell(
        field,
        id,
        <label className="switch mt-0.5">
          <input type="checkbox" checked={Boolean(value)} onChange={(e) => setValue(field.key, e.target.checked)} />
          <span className="track" />
          <span className="text-[13px] font-medium">{field.label}</span>
        </label>,
      )

    case 'textarea':
      return shell(
        field,
        id,
        <textarea
          className="inp"
          rows={4}
          value={value === null || value === undefined ? '' : String(value)}
          placeholder={field.placeholder}
          onChange={(e) => setValue(field.key, e.target.value)}
        />,
      )

    case 'string-list':
      return <StringListField field={field} fieldId={id} />
  }
}

/** 数字字段：本地暂存原始输入（允许打 "1." 这种中间态），失焦时归位。 */
function NumberField({ field, fieldId }: { field: Extract<Field, { kind: 'number' }>; fieldId: string }) {
  const value = useConfigStore((s) => (s.draft ? getByPath(s.draft, field.key) : undefined))
  const setValue = useConfigStore((s) => s.setValue)
  const [raw, setRaw] = useState<string | null>(null)

  const shown = raw ?? (value === null || value === undefined ? '' : String(value))

  const commit = (text: string) => {
    const t = text.trim()
    if (t === '') {
      setValue(field.key, 0) // v2 语义：空值落 0
      return
    }
    const n = field.int ? parseInt(t, 10) : parseFloat(t)
    if (!Number.isNaN(n)) setValue(field.key, field.int ? n : Math.round(n * 100) / 100)
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

function SelectField({ field, fieldId }: { field: Extract<Field, { kind: 'select' }>; fieldId: string }) {
  const value = useConfigStore((s) => (s.draft ? getByPath(s.draft, field.key) : undefined))
  const setValue = useConfigStore((s) => s.setValue)
  const options = resolveOptions(field, value)

  // 配置里存的值已不在选项里（如老平台名）：保留为选项，不让老配置看起来是空的
  const current = value === null || value === undefined ? '' : String(value)
  if (current !== '' && !(current in options)) {
    Object.assign(options, { [current]: `${current}（配置里的当前值）` })
  }

  return shell(
    field,
    fieldId,
    <select className="inp" value={current} onChange={(e) => setValue(field.key, e.target.value)}>
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
function StringListField({ field, fieldId }: { field: Extract<Field, { kind: 'string-list' }>; fieldId: string }) {
  const value = useConfigStore((s) => (s.draft ? getByPath(s.draft, field.key) : undefined))
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
    setValue(field.key, normalized)
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
