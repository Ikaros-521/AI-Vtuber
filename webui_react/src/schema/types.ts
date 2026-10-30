/** 配置表单的 schema 定义：React 版用数据描述取代 v2 的命令式建页。 */

export type Path = (string | number)[]

export type FieldWidth = 'xs' | 'sm' | 'md' | 'lg' | 'xl'

export type SelectOptions = Record<string, string> | ((current: unknown) => Record<string, string>)

export type ActionId =
  | 'llm-test'
  | 'llm-models'
  | 'window-titles'
  | 'cameras'
  | 'config-templates'
  | 'config-template-save'
  | 'config-template-load'
  | 'anythingllm-workspaces'
  | 'serial-ports'
  | 'serial-connect'
  | 'serial-disconnect'
  | 'serial-send'
  | 'img-screenshot'
  | 'live2d-models'
  | 'audio-devices'
  | 'vits-speakers'
  | 'tts-test'

export interface FieldBase {
  /** config.json 里的路径；在 group-list 内为相对条目路径（渲染时拼上基座路径） */
  key: Path
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
      /** 可输入的下拉（v2 的 with_input + add-unique），用于模型名这类可手输项 */
      free?: boolean
      /** 选项来自动作按钮动态拉取（模型列表/窗口标题/串口/模板…），key 对应 actionStore.options */
      dynamicOptions?: string
    })
  | (FieldBase & { kind: 'switch' })
  | (FieldBase & { kind: 'textarea' })
  /** string[] 与多行文本互转（v2 的 textarea_data_change 语义） */
  | (FieldBase & { kind: 'string-list' })
  /** string[] 多选框（洛曦触发类型/触发位置） */
  | (FieldBase & { kind: 'checkboxes'; options: Record<string, string> })
  /** 周期触发复合控件：key 指向 periodic_trigger 对象基座，
   * 行内编辑 periodic_time_min/max（秒）与 trigger_num_min/max（次数）四个数 */
  | (FieldBase & { kind: 'frequency' })
  /** 动作按钮：params 的值是「相对本字段基座」的取值路径；$transient:<fieldId> 取临时输入框的值 */
  | (FieldBase & {
      kind: 'action'
      action: ActionId
      params?: Record<string, Path | string>
      /** 点按钮前弹确认框（危险操作） */
      confirm?: string
    })
  /** 外部 JSON 文件编辑器（本地问答），不走 config 草稿，显式加载/保存 */
  | (FieldBase & { kind: 'file-json' })
  /** 动态配置组：key 指向 config 里的对象数组，条目字段用相对路径 */
  | (FieldBase & {
      kind: 'group-list'
      itemDefaults: Record<string, unknown>
      rows: Field[][]
      itemTitle?: string
      addLabel?: string
      itemDesc?: string
    })
  /** 临时输入框（串口发送数据这类不进 config 的值），值存 actionStore.transient */
  | (FieldBase & { kind: 'transient-input' })

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
  /** 高级参数行：默认折叠（渐进披露），迁移到哪张卡就拆到哪 */
  rowsAdvanced?: Field[][]
  /** 玩法库卡片图标名（SecIcon 组件维护映射） */
  icon?: string
  cards?: Section[]
  /** 专用组件标记（板块开关墙 / 文档与关于 / TTS试听 / 数据分析 / 优先级拖拽列表），由 WorkspacePage 分发渲染 */
  custom?: 'section-toggles' | 'docs' | 'tts-tester' | 'data-analysis' | 'priority-list'
  /** 选卡墙归属：pickKey 当前值命中 pickValue 时本区块渲染为完整表单，否则只是选卡墙上的一张卡。
   * 数组用于「一个区块服务多个选项」的场景（bilibili2 复用 bilibili 区块、遗留平台归监听助手）。 */
  pickValue?: string | string[]
  /** 选卡墙卡片上的标签（免费 / 需 API Key / 需本地部署…） */
  tags?: string[]
  /** 玩法库主开关：指向本区块的布尔 config 键，开关卡片据此点亮 */
  masterKey?: Path
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
  /** 多组时用页签切组而不是纵向堆叠（弹幕管家：触发/过滤/答谢/顺序） */
  tabbed?: boolean
  /** N 选 1 键（platform / chat_type / audio_synthesis_type / visual_body）：
   * 有 pickKey 的工作区用「选卡墙 + 只渲染选中者的表单」替代全量平铺 */
  pick?: {
    key: Path
    /** 无对应表单区块的特殊选项（none / reread / talk…）也在这里给标签 */
    options: Record<string, string>
  }
}

/** 全局唯一的字段定位 id，跳转/搜索用它找 DOM。 */
export function fieldIdOf(workspaceId: string, sectionId: string, field: Field): string {
  return `${workspaceId}__${sectionId}__${field.key.join('.')}`
}
