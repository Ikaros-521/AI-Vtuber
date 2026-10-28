/** 配置表单的 schema 定义：React 版用数据描述取代 v2 的命令式建页。 */

export type FieldWidth = 'xs' | 'sm' | 'md' | 'lg' | 'xl'

export type SelectOptions = Record<string, string> | ((current: unknown) => Record<string, string>)

export interface FieldBase {
  /** config.json 里的路径，如 ['openai', 'api'] */
  key: (string | number)[]
  label: string
  /** 字段下方的常驻说明（v2 把长 placeholder 挪过来的那批） */
  hint?: string
  placeholder?: string
  w?: FieldWidth
}

export type Field =
  | (FieldBase & { kind: 'input'; password?: boolean })
  | (FieldBase & { kind: 'number'; int?: boolean; step?: number })
  | (FieldBase & {
      kind: 'select'
      options: SelectOptions
      /** 配置里的当前值不在选项里时保留显示（老平台名这类场景） */
      keepUnknown?: boolean
    })
  | (FieldBase & { kind: 'switch' })
  | (FieldBase & { kind: 'textarea' })
  /** string[] 与多行文本互转（v2 的 textarea_data_change 语义） */
  | (FieldBase & { kind: 'string-list' })

export function resolveOptions(field: Extract<Field, { kind: 'select' }>, current: unknown): Record<string, string> {
  return typeof field.options === 'function' ? field.options(current) : field.options
}

export interface Section {
  id: string
  title: string
  desc?: string
  /** 板块开关：config.webui.show_card.<page>.<key> 为真才显示 */
  showCard?: [page: string, key: string]
  rows?: Field[][]
  cards?: Section[]
}

export interface SectionGroup {
  title: string
  sections: Section[]
}

export interface Workspace {
  id: string
  title: string
  groups: SectionGroup[]
  /** 非表单驱动的页面 */
  custom?: 'overview' | 'chat'
  /** 尚未从 v2 迁移过来的工作区 */
  stub?: string
}

/** 全局唯一的字段定位 id，跳转/搜索用它找 DOM。 */
export function fieldIdOf(workspaceId: string, sectionId: string, field: Field): string {
  return `${workspaceId}__${sectionId}__${field.key.join('.')}`
}
