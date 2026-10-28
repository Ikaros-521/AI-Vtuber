/** 配置草稿状态：加载、编辑、diff、保存。 */
import { create } from 'zustand'
import { api } from '../api/client'
import { deepDiff, setByPath } from '../lib/path'
import type { ConfigChange, JsonObject, Path } from '../lib/path'

export interface SaveOutcome {
  ok: boolean
  message: string
  /** 校验失败时指向要跳转的配置路径 */
  path?: (string | number)[]
}

interface ConfigState {
  status: 'loading' | 'ready' | 'error'
  config: JsonObject | null
  draft: JsonObject | null
  sha256: string
  configPath: string
  loadError: string | null
  fetchConfig: () => Promise<void>
  setValue: (path: Path, value: unknown) => void
  save: () => Promise<SaveOutcome>
}

export const useConfigStore = create<ConfigState>((set, get) => ({
  status: 'loading',
  config: null,
  draft: null,
  sha256: '',
  configPath: '',
  loadError: null,

  fetchConfig: async () => {
    set({ status: 'loading', loadError: null })
    try {
      const resp = await api.getConfig()
      if (resp.code !== 200) {
        set({ status: 'error', loadError: resp.message ?? '读取配置失败' })
        return
      }
      set({
        status: 'ready',
        config: resp.config,
        draft: structuredClone(resp.config),
        sha256: resp.sha256,
        configPath: resp.path,
      })
      applyAccent(resp.config)
    } catch (e) {
      set({ status: 'error', loadError: `连不上后端服务：${e}` })
    }
  },

  setValue: (path, value) => {
    const draft = get().draft
    if (!draft) return
    set({ draft: setByPath(draft, path, value) })
  },

  save: async () => {
    const { config, draft, sha256 } = get()
    if (!config || !draft) return { ok: false, message: '配置还没加载好' }
    const changes = deepDiff(config, draft)
    if (changes.length === 0) return { ok: true, message: '没有未保存的改动' }

    const resp = await api.saveConfig(
      sha256,
      changes.map((c) => ({ path: c.path, value: c.value })),
    )
    if (resp.code === 200) {
      // 以服务端落盘结果为准，重新对齐基线
      set({ config: structuredClone(draft), sha256: (resp.sha256 as string) ?? sha256 })
      return { ok: true, message: `配置数据已成功写入文件！（${changes.length} 项改动）` }
    }
    return { ok: false, message: resp.message ?? '保存失败', path: resp.path }
  },
}))

/** 当前未保存改动（组件里用它订阅）。 */
export function useChanges(): ConfigChange[] {
  const config = useConfigStore((s) => s.config)
  const draft = useConfigStore((s) => s.draft)
  if (!config || !draft) return []
  return deepDiff(config, draft)
}

/** 主题色：webui.theme.list[choose].button_bottom_color，可能是 primary / 带尾分号（v2 同款坑）。 */
function applyAccent(config: JsonObject) {
  const theme = config.webui as JsonObject | undefined
  const list = (theme?.theme as JsonObject | undefined)?.list as Record<string, JsonObject> | undefined
  const choose = (theme?.theme as JsonObject | undefined)?.choose as string | undefined
  const color = choose && list ? (list[choose]?.button_bottom_color as string | undefined) : undefined
  let accent = (color ?? '').trim().replace(/;+$/, '')
  if (!accent || accent === 'primary') accent = '#2563eb'
  if (!/^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(accent)) accent = '#2563eb'
  document.documentElement.style.setProperty('--accent', accent)
  document.documentElement.style.setProperty('--accent-ink', readableOn(accent) ? '#111827' : '#ffffff')
}

export function readableOn(hex: string): boolean {
  const m = hex.replace('#', '')
  const full = m.length === 3 ? m.split('').map((c) => c + c).join('') : m
  const r = parseInt(full.slice(0, 2), 16) / 255
  const g = parseInt(full.slice(2, 4), 16) / 255
  const b = parseInt(full.slice(4, 6), 16) / 255
  const lin = (c: number) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
  const l = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
  return l > 0.45
}
