/** 配置路径读写与 diff 工具。 */

export type Path = (string | number)[]
export type JsonObject = Record<string, unknown>

export function isPlainObject(v: unknown): v is JsonObject {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

export function getByPath(obj: unknown, path: Path): unknown {
  let cur: unknown = obj
  for (const key of path) {
    if (cur == null) return undefined
    cur = (cur as Record<string | number, unknown>)[key]
  }
  return cur
}

/** 不可变写入：返回结构共享的新对象，原对象不动。 */
export function setByPath<T>(obj: T, path: Path, value: unknown): T {
  if (path.length === 0) return value as T
  const [head, ...rest] = path
  const source = obj as Record<PropertyKey, unknown> | null
  const next = (Array.isArray(obj) ? [...(obj as unknown[])] : { ...(source ?? {}) }) as Record<PropertyKey, unknown>
  next[head] = setByPath(source?.[head], rest, value)
  return next as T
}

export interface ConfigChange {
  path: Path
  value: unknown
  before: unknown
}

function sameValue(a: unknown, b: unknown): boolean {
  if (a === b) return true
  // 数组（如文案列表）整体比较
  return JSON.stringify(a) === JSON.stringify(b)
}

/** 深度对比，产出叶子级改动清单；双方都是普通对象时下钻。 */
export function deepDiff(base: unknown, draft: unknown, path: Path = [], out: ConfigChange[] = []): ConfigChange[] {
  if (isPlainObject(base) && isPlainObject(draft)) {
    const keys = new Set([...Object.keys(base), ...Object.keys(draft)])
    for (const key of keys) {
      deepDiff(base[key], draft[key], [...path, key], out)
    }
    return out
  }
  if (!sameValue(base, draft)) {
    out.push({ path, value: draft, before: base })
  }
  return out
}

/** 未保存清单里的一行显示，语义与 v2 fields.value_text 一致。 */
export function formatValue(v: unknown): string {
  if (typeof v === 'boolean') return v ? '开' : '关'
  if (v === null || v === undefined || v === '') return '（空）'
  if (Array.isArray(v)) return v.length ? `${v.length} 行` : '（空）'
  const s = typeof v === 'string' ? v : JSON.stringify(v) ?? ''
  return s.length > 40 ? `${s.slice(0, 40)}…` : s
}

export function pathEquals(a: Path, b: unknown): a is Path {
  return Array.isArray(b) && b.length === a.length && a.every((k, i) => k === b[i])
}
