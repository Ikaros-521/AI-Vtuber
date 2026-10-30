/** 工作区注册表与字段索引 —— 重设计后的新 IA（2026-10 方案文档 docs/redesign/）。

 * 顶层 5 页：开播台(dash) / 基础设置(settings=platform+brain+voice+body 四步) /
 * 玩法库(play) / 弹幕管家(mod) / 系统(sys)；聊天(chat) 从开播台进入，不占主导航。
 * ?tab= 深链兼容老 v3 的九个标题，也接受新页面 id。
 */
import type { JsonObject, Path } from '../lib/path'
import { getByPath } from '../lib/path'
import { LEGACY_LIVE_MONITOR_PLATFORMS } from './options'
import { fieldIdOf } from './types'
import { bodyWorkspace } from './workspaces/body'
import { brainWorkspace } from './workspaces/brain'
import { danmuWorkspace } from './workspaces/danmu'
import { platformWorkspace } from './workspaces/platform'
import { playWorkspace } from './workspaces/play'
import { systemWorkspace } from './workspaces/system'
import { voiceWorkspace } from './workspaces/voice'
import type { Field, Section, Workspace } from './types'

export const WORKSPACES: Workspace[] = [
  platformWorkspace,
  brainWorkspace,
  voiceWorkspace,
  bodyWorkspace,
  playWorkspace,
  danmuWorkspace,
  systemWorkspace,
]

/** 基础设置的四个步骤（也是信号链的四个节点）。 */
export const SETTINGS_STEPS: Workspace[] = [platformWorkspace, brainWorkspace, voiceWorkspace, bodyWorkspace]

/** 顶层页面：dash/chat 是非表单页，其余映射到工作区或 settings 组合页。 */
export type PageId = 'dash' | 'settings' | 'play' | 'mod' | 'sys' | 'chat'

export interface PageDef {
  id: PageId
  title: string
  sub: string
}

export const PAGES: PageDef[] = [
  { id: 'dash', title: '开播台', sub: '现在能开播吗？差哪一步？' },
  { id: 'settings', title: '基础设置', sub: '四步配齐信号链：直播间 → AI 大脑 → 声音 → 形象' },
  { id: 'play', title: '玩法库', sub: '可选玩法，开关式启用' },
  { id: 'mod', title: '弹幕管家', sub: '什么弹幕进、怎么答谢、谁先播' },
  { id: 'sys', title: '系统', sub: '数据 / 备份 / 账号 / 外观 / 模块' },
]

/** 老 v3 九工作区标题 → 新页面（+settings 步骤）。 */
const LEGACY_TAB_MAP: Record<string, { page: PageId; step?: string }> = {
  总览: { page: 'dash' },
  聊天: { page: 'chat' },
  直播接入: { page: 'settings', step: 'platform' },
  人设与大脑: { page: 'settings', step: 'brain' },
  声音与表现: { page: 'settings', step: 'voice' },
  弹幕与礼仪: { page: 'mod' },
  互动与玩法: { page: 'play' },
  外设与联动: { page: 'play' },
  运维与系统: { page: 'sys' },
  // 新 id 直填也认
  dash: { page: 'dash' },
  chat: { page: 'chat' },
  settings: { page: 'settings' },
  play: { page: 'play' },
  mod: { page: 'mod' },
  sys: { page: 'sys' },
  platform: { page: 'settings', step: 'platform' },
  brain: { page: 'settings', step: 'brain' },
  voice: { page: 'settings', step: 'voice' },
  body: { page: 'settings', step: 'body' },
}

/** ?tab= 的值 → 页面 + 步骤。认老标题、新 id、settings 步骤 id。 */
export function resolveTab(tab: string | null): { page: PageId; step: string } {
  if (!tab) return { page: 'dash', step: 'platform' }
  const hit = LEGACY_TAB_MAP[tab]
  if (hit) return { page: hit.page, step: hit.step ?? 'platform' }
  // 没见过的标题：如果恰好是某个 settings 步骤的标题也接住
  const byTitle = SETTINGS_STEPS.find((w) => w.title === tab)
  if (byTitle) return { page: 'settings', step: byTitle.id }
  return { page: 'dash', step: 'platform' }
}

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

/** pickValue 是否命中当前选择值（string 或 string[] 都支持）。 */
export function pickMatches(section: Section, value: unknown): boolean {
  if (section.pickValue === undefined) return false
  const v = String(value ?? '')
  return Array.isArray(section.pickValue) ? section.pickValue.includes(v) : section.pickValue === v
}

// ---------- 保存前预检 ----------

export interface PrecheckIssue {
  stepId: string
  stepTitle: string
  sectionTitle: string
  label: string
  fieldId: string
}

/** 保存前预检：四个选择步骤里，当前选中服务的必填型字段（rows 里的输入类，未标 skipPrecheck）
 * 空着就报出来——是提醒不是拦截，用户可以「仍要保存」。 */
export function precheckSettings(draft: JsonObject): PrecheckIssue[] {
  const issues: PrecheckIssue[] = []

  for (const ws of SETTINGS_STEPS) {
    if (!ws.pick) continue
    const current = getByPath(draft, ws.pick.key)
    const section = ws.groups[0]?.sections.find((s) => pickMatches(s, current))
    if (section) {
      for (const row of section.rows ?? []) {
        for (const field of row) {
          if (field.kind !== 'input' && field.kind !== 'string-list' && field.kind !== 'textarea') continue
          if (field.skipPrecheck) continue
          if (typeof field.key[0] === 'string' && field.key[0].startsWith('_')) continue
          const v = getByPath(draft, field.key)
          const empty = v === undefined || v === null || v === '' || (Array.isArray(v) && v.length === 0)
          if (empty) {
            issues.push({
              stepId: ws.id,
              stepTitle: ws.title,
              sectionTitle: section.title,
              label: field.label,
              fieldId: fieldIdOf(ws.id, section.id, field),
            })
          }
        }
      }
    }

    // 直播间号：非「由外部决定监听」的平台需要填
    if (ws.id === 'platform') {
      const platform = String(current ?? '')
      const externallyDecided = ['talk', 'live_monitor_assistant', ...Object.keys(LEGACY_LIVE_MONITOR_PLATFORMS)].includes(platform)
      const room = getByPath(draft, ['room_display_id'])
      if (platform && !externallyDecided && (room === undefined || room === null || room === '')) {
        issues.push({
          stepId: 'platform',
          stepTitle: '直播间',
          sectionTitle: '直播间号',
          label: '直播间号',
          fieldId: 'platform__room-info__room_display_id',
        })
      }
    }
  }

  return issues
}

// ---------- 字段索引（搜索、未保存清单标签、开播台跳转共用） ----------

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
  for (const row of [...(section.rows ?? []), ...(section.rowsAdvanced ?? [])]) {
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
