/** 工作区注册表与字段索引。

 * 9 大核心工作区与 v2 webui_app/overview.PAGE_LIST 一一对应；尚未迁移的
 * 工作区标记 stub，页面会明确提示「继续用 v2 配置」，不放假数据。
 */
import type { JsonObject, Path } from '../lib/path'
import { brainWorkspace } from './workspaces/brain'
import { danmuWorkspace } from './workspaces/danmu'
import { hardwareWorkspace } from './workspaces/hardware'
import { interactionWorkspace } from './workspaces/interaction'
import { liveWorkspace } from './workspaces/live'
import { systemWorkspace } from './workspaces/system'
import { voiceWorkspace } from './workspaces/voice'
import type { Field, Section, Workspace } from './types'

export const WORKSPACES: Workspace[] = [
  { id: 'overview', title: '总览', groups: [], custom: 'overview' },
  { id: 'chat', title: '聊天', groups: [], custom: 'chat' },
  liveWorkspace,
  brainWorkspace,
  voiceWorkspace,
  danmuWorkspace,
  interactionWorkspace,
  hardwareWorkspace,
  systemWorkspace,
]

/** 聊天页里的三个配置字段（talk.username 等），未保存清单里要显示中文标签。 */
export const CHAT_SETTINGS_SECTION: Section = {
  id: 'chat-settings',
  title: '聊天设置',
  rows: [
    [
      { kind: 'input', key: ['talk', 'username'], label: '说话人昵称', w: 'sm', hint: '在此输入您与 AI 对话时的昵称/身份' },
      { kind: 'switch', key: ['talk', 'show_chat_log'], label: '同步弹幕', hint: '开启后，直播间弹幕与 AI 回复将实时同步显示到本聊天窗口' },
      { kind: 'switch', key: ['talk', 'direct_run_talk'], label: '语音对话（直接拾音）', hint: '开启后无需按键，麦克风将自动监听语音并与 AI 实时对话' },
    ],
  ],
}

// ---------- 可见性（板块开关） ----------

export function sectionVisible(section: Section, draft: JsonObject | null): boolean {
  if (!section.showCard) return true
  const [page, key] = section.showCard
  let cur: unknown = draft
  for (const k of ['webui', 'show_card', page, key]) {
    if (typeof cur !== 'object' || cur === null) return false
    cur = (cur as JsonObject)[k]
  }
  return Boolean(cur)
}

// ---------- 字段索引（搜索、未保存清单标签、总览跳转共用） ----------

export interface FieldIndexEntry {
  workspaceId: string
  workspaceTitle: string
  groupTitle: string
  sectionId: string
  sectionTitle: string
  field: Field
  fieldId: string
}

function indexSection(ws: Workspace, groupTitle: string, section: Section, out: FieldIndexEntry[]) {
  const baseFieldId = (field: Field) => `${ws.id}__${section.id}__${field.key.join('.')}`
  for (const row of section.rows ?? []) {
    for (const field of row) {
      const entry: FieldIndexEntry = {
        workspaceId: ws.id,
        workspaceTitle: ws.title,
        groupTitle,
        sectionId: section.id,
        sectionTitle: section.title,
        field,
        fieldId: baseFieldId(field),
      }
      out.push(entry)
      // 动态配置组：把组内字段也列进索引（label 供搜索与未保存清单用），
      // 跳转落点是组容器本身
      if (field.kind === 'group-list') {
        for (const innerRow of field.rows) {
          for (const inner of innerRow) {
            if (inner.kind.startsWith('_')) continue
            out.push({
              ...entry,
              field: { ...inner, key: [...field.key, ...inner.key] } as Field,
              fieldId: entry.fieldId,
            })
          }
        }
      }
    }
  }
  for (const card of section.cards ?? []) {
    indexSection(ws, groupTitle, card, out)
  }
}

function buildIndex(): FieldIndexEntry[] {
  const out: FieldIndexEntry[] = []
  for (const ws of WORKSPACES) {
    for (const group of ws.groups) {
      for (const section of group.sections) {
        indexSection(ws, group.title, section, out)
      }
    }
  }
  // 聊天页的配置字段也进索引（搜索能搜到）
  indexSection(
    { id: 'chat', title: '聊天', groups: [] },
    '聊天',
    CHAT_SETTINGS_SECTION,
    out,
  )
  return out
}

export const FIELD_INDEX: FieldIndexEntry[] = buildIndex()

const LABEL_BY_PATH = new Map<string, FieldIndexEntry>(
  FIELD_INDEX.map((e) => [e.field.key.join('.'), e]),
)

/** 未保存清单里的一条改动对应的字段信息（可能不在任何 schema 里）。

 * 动态配置组的条目路径带序号（key_mapping.config.0.keywords），
 * 精确匹配不到时去掉数字段再匹配一次（key_mapping.config.keywords）。
 */
export function entryForPath(path: Path): FieldIndexEntry | undefined {
  const exact = LABEL_BY_PATH.get(path.join('.'))
  if (exact) return exact
  const stripped = path.filter((k) => typeof k !== 'number').join('.')
  return stripped ? LABEL_BY_PATH.get(stripped) : undefined
}

/** 搜索用：忽略分隔符（_- / 空格）后做子串匹配，名字命中排前面。 */
export function normalizeForSearch(s: string): string {
  return s.toLowerCase().replace(/[\s_\-/]/g, '')
}

export function searchFields(query: string): FieldIndexEntry[] {
  const q = normalizeForSearch(query)
  if (!q) return []
  const scored: { entry: FieldIndexEntry; score: number }[] = []
  for (const entry of FIELD_INDEX) {
    const label = normalizeForSearch(entry.field.label)
    const path = normalizeForSearch(entry.field.key.join('.'))
    const section = normalizeForSearch(entry.sectionTitle)
    let score = 0
    if (label.includes(q)) score = label.startsWith(q) ? 3 : 2
    else if (path.includes(q) || section.includes(q)) score = 1
    if (score > 0) scored.push({ entry, score })
  }
  scored.sort((a, b) => b.score - a.score)
  return scored.slice(0, 60).map((s) => s.entry)
}
