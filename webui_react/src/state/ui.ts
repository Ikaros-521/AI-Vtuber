/** 轻量 UI 状态：toast、确认框、跳转定位。 */
import { create } from 'zustand'

// ---------- Toast ----------

export interface Toast {
  id: number
  kind: 'info' | 'positive' | 'warning' | 'negative'
  message: string
}

interface ToastState {
  toasts: Toast[]
  notify: (kind: Toast['kind'], message: string) => void
  dismiss: (id: number) => void
}

let toastSeq = 0

export const useToastStore = create<ToastState>((set) => ({
  toasts: [],
  notify: (kind, message) => {
    const id = ++toastSeq
    set((s) => ({ toasts: [...s.toasts, { id, kind, message }] }))
    setTimeout(() => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })), kind === 'negative' ? 6000 : 3500)
  },
  dismiss: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}))

export const notify = {
  info: (m: string) => useToastStore.getState().notify('info', m),
  ok: (m: string) => useToastStore.getState().notify('positive', m),
  warn: (m: string) => useToastStore.getState().notify('warning', m),
  err: (m: string) => useToastStore.getState().notify('negative', m),
}

// ---------- 确认框 ----------

export interface ConfirmRequest {
  title: string
  body?: string
  onOk: () => void
}

interface ConfirmState {
  current: ConfirmRequest | null
  ask: (title: string, onOk: () => void, body?: string) => void
  close: () => void
}

export const useConfirmStore = create<ConfirmState>((set) => ({
  current: null,
  ask: (title, onOk, body) => set({ current: { title, onOk, body } }),
  close: () => set({ current: null }),
}))

// ---------- 跳转定位（搜索 / 总览「去配置」/ 未保存清单 共用） ----------

export interface JumpTarget {
  workspace: string
  /** 字段：data-field-id；区块：data-section-id */
  fieldId?: string
  sectionId?: string
  seq: number
}

interface JumpState {
  target: JumpTarget | null
  jump: (workspace: string, target: { fieldId?: string; sectionId?: string }) => void
  /** 一次性消费：AppShell 完成路由后清掉，避免残留目标在渲染期顶掉用户的手动切换 */
  clear: () => void
}

let jumpSeq = 0

export const useJumpStore = create<JumpState>((set) => ({
  target: null,
  jump: (workspace, target) => set({ target: { workspace, ...target, seq: ++jumpSeq } }),
  clear: () => set({ target: null }),
}))
