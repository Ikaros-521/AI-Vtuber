/** 运行态轮询：状态可能被 /sys_cmd 从别处改掉，只能轮询，不能只靠按钮回调。 */
import { create } from 'zustand'
import { api } from '../api/client'

interface OpsState {
  running: boolean
  loaded: boolean
  refresh: () => Promise<void>
}

export const useOpsStore = create<OpsState>((set) => ({
  running: false,
  loaded: false,
  refresh: async () => {
    try {
      const resp = await api.opsStatus()
      if (resp.code === 200) set({ running: resp.running, loaded: true })
    } catch {
      // 后端瞬断不惊动用户，下一轮再试
    }
  },
}))
