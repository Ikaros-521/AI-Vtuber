/** 登录门禁：login.enable 打开时，先过这张卡才能进功能页。

 * 校验走后端 /api/auth（账号密码存于 config.json 的 login 节）。
 */
import { useState } from 'react'
import { api } from '../api/client'

export function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    if (!username || !password) {
      setError('用户名或密码不能为空')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const resp = await api.authLogin(username, password)
      if (resp.code === 200) {
        onLogin()
      } else {
        setError(resp.message ?? '登录失败')
      }
    } catch {
      setError('登录请求没走通，请确认服务在运行')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200 px-4">
      <div className="card-surface w-full max-w-[340px] p-7">
        <h1 className="text-center text-[26px] font-bold tracking-[0.4em] text-[#3b3838]">AI&nbsp;Vtuber</h1>
        <div className="mt-6 flex flex-col gap-3">
          <input
            className="inp"
            placeholder="用户名"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && void submit()}
          />
          <input
            className="inp"
            type="password"
            placeholder="密码"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && void submit()}
          />
          {error && <p className="text-xs leading-relaxed text-red-600">{error}</p>}
          <button
            className="rounded-lg py-2 text-[14px] font-semibold text-white transition hover:opacity-90 disabled:opacity-50"
            style={{ background: 'var(--accent)' }}
            disabled={busy}
            onClick={() => void submit()}
          >
            {busy ? '登录中…' : '登录'}
          </button>
          <p className="text-center text-xs text-[var(--ink-mut)]">忘记账号/密码请联系管理员修改密码！</p>
        </div>
      </div>
    </div>
  )
}
