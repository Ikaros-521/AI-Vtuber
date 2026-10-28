/** 动作按钮的运行时：动态选项缓存 + 临时输入框值。 */
import { create } from 'zustand'

interface ActionState {
  /** 动作拉回的选项列表（模型名/窗口标题/串口/模板…），key 由字段声明 */
  options: Record<string, string[]>
  setOptions: (key: string, items: string[]) => void
  /** 临时输入框的值（串口发送数据这类），key 用 fieldId */
  transient: Record<string, string>
  setTransient: (key: string, value: string) => void
}

export const useActionStore = create<ActionState>((set) => ({
  options: {},
  setOptions: (key, items) => set((s) => ({ options: { ...s.options, [key]: items } })),
  transient: {},
  setTransient: (key, value) => set((s) => ({ transient: { ...s.transient, [key]: value } })),
}))
