/** 服务测试记录：LLM 测试 / TTS 试听的结果按 provider 值记账，选卡墙与信号链据此显示「已测通」。

 * 「配好了」的定义从填过变成测过——记录跨刷新保留（localStorage），换 provider 后
 * 旧记录仍在（各自的卡各自的状态），重新测试覆盖。
 */
import { create } from 'zustand'

export interface TestRecord {
  ok: boolean
  message: string
  at: number
}

export type TestKind = 'llm' | 'tts'

interface TestState {
  llm: Record<string, TestRecord>
  tts: Record<string, TestRecord>
  record: (kind: TestKind, value: string, ok: boolean, message: string) => void
}

const LS_KEY = 'aiv-test-status'

function load(): Pick<TestState, 'llm' | 'tts'> {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (raw) {
      const parsed = JSON.parse(raw) as Pick<TestState, 'llm' | 'tts'>
      return { llm: parsed.llm ?? {}, tts: parsed.tts ?? {} }
    }
  } catch {
    /* 坏数据当没有 */
  }
  return { llm: {}, tts: {} }
}

export const useTestStore = create<TestState>((set) => ({
  ...load(),
  record: (kind, value, ok, message) =>
    set((s) => {
      const next = { ...s, [kind]: { ...s[kind], [value]: { ok, message, at: Date.now() } } } as TestState
      try {
        localStorage.setItem(LS_KEY, JSON.stringify({ llm: next.llm, tts: next.tts }))
      } catch {
        /* 隐私模式/配额满：内存里生效即可 */
      }
      return next
    }),
}))
