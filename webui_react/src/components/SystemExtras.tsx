/** 运维与系统工作区的专用组件：板块开关墙、文档与关于。 */
import { useConfigStore } from '../state/configStore'
import { getByPath } from '../lib/path'

// ---------- 板块开关墙 ----------

/** show_card 各键的中文标签；没收录的键直接显示键名。 */
const SHOW_CARD_LABELS: Record<string, string> = {
  // common_config
  read_comment: '念弹幕',
  read_username: '念用户名',
  filter: '过滤',
  thanks: '答谢',
  local_qa: '本地问答',
  choose_song: '点歌',
  schedule: '定时任务',
  idle_time_task: '闲时任务',
  search_online: '联网搜索',
  trends_copywriting: '动态文案',
  key_mapping: '按键/文案映射',
  custom_cmd: '自定义命令',
  trends_config: '动态配置',
  abnormal_alarm: '异常报警',
  coordination_program: '联动程序',
  log: '日志',
  database: '数据库',
  sd: 'Stable Diffusion',
  play_audio: '音频播放',
  web_captions_printer: 'web字幕打印机',
  // llm
  chatgpt: 'ChatGPT',
  zhipu: '智谱AI',
  langchain_chatchat: 'langchain_chatchat',
  tongyi: '通义千问',
  my_wenxinworkshop: '千帆大模型',
  gemini: 'Gemini',
  anythingllm: 'AnythingLLM',
  dify: 'Dify',
  volcengine: '火山引擎',
  custom_llm: '自定义LLM',
  // tts
  'edge-tts': 'Edge TTS',
  vits: 'VITS',
  bert_vits2: 'Bert-VITS2',
  elevenlabs: 'elevenlabs',
  openai_tts: 'OpenAI TTS',
  gradio_tts: 'Gradio',
  gpt_sovits: 'GPT-SoVITS',
  azure_tts: 'Azure TTS',
  cosyvoice: 'CosyVoice',
  f5_tts: 'F5-TTS',
  multitts: 'MultiTTS',
  melotts: 'MeloTTS',
  index_tts: 'Index-TTS',
  // svc / visual_body 常见项
  'so-vits-svc': 'SO-VITS-SVC',
  so_vits_svc: 'SO-VITS-SVC',
  'ddsp-svc': 'DDSP-SVC',
  ddsp_svc: 'DDSP-SVC',
  live2d: 'Live2D',
  metahuman_stream: 'metahuman_stream',
  xuniren: 'xuniren',
  unity: 'Unity',
  digital_human_video_player: '数字人视频播放器',
  EasyAIVtuber: 'EasyAIVtuber',
  live2d_TTS_LLM_GPT_SoVITS_Vtuber: 'Live2D+LLM+GPT-SoVITS 组合方案',
}

const PAGE_LABELS: Record<string, string> = {
  common_config: '功能板块',
  llm: '大语言模型',
  tts: '文本转语音',
  svc: '变声',
  visual_body: '虚拟身体',
}

export function SectionToggleWall() {
  const draft = useConfigStore((s) => s.draft)
  const setValue = useConfigStore((s) => s.setValue)
  if (!draft) return null

  const showCard = (getByPath(draft, ['webui', 'show_card']) ?? {}) as Record<string, Record<string, unknown>>
  const pages = Object.entries(showCard)

  return (
    <div className="flex flex-col gap-4">
      {pages.map(([page, entries]) => (
        <div key={page} className="rounded-xl border border-slate-200 bg-slate-50/70 p-4">
          <h4 className="text-[13px] font-semibold">{PAGE_LABELS[page] ?? page}</h4>
          <div className="mt-2 flex flex-wrap gap-x-6 gap-y-2.5">
            {Object.entries(entries).map(([key, on]) => (
              <label key={key} className="switch">
                <input
                  type="checkbox"
                  checked={Boolean(on)}
                  onChange={(e) => setValue(['webui', 'show_card', page, key], e.target.checked)}
                />
                <span className="track" />
                <span className="text-[13px] font-medium">{SHOW_CARD_LABELS[key] ?? key}</span>
              </label>
            ))}
          </div>
        </div>
      ))}
      {pages.length === 0 && (
        <p className="text-[13px] text-[var(--ink-mut)]">配置里还没有 webui.show_card 数据。</p>
      )}
      <p className="text-xs leading-relaxed text-[var(--ink-mut)]">
        改动会进「未保存」清单，点右下角「保存配置」生效。还没迁移到 v3 的板块开关（如 TTS 各家）控制的是 v2 页面的显示。
      </p>
    </div>
  )
}

// ---------- 文档与关于 ----------

const RESOURCES: { title: string; url: string; tags: string[]; summary: string }[] = [
  {
    title: '在线文档（主站）',
    url: 'https://ikaros521.eu.org/site/',
    tags: ['入门', '配置项', '部署'],
    summary: '部署步骤、每个配置项的含义、常见问题都在这里。第一次搭环境从这页开始。',
  },
  {
    title: 'gitee 备份文档',
    url: 'https://ikaros-521.gitee.io/luna-docs/site/index.html',
    tags: ['镜像'],
    summary: '主站打不开时用这个，内容与在线文档一致。',
  },
  {
    title: '视频教程合集',
    url: 'https://space.bilibili.com/3709626/channel/collectiondetail?sid=1422512',
    tags: ['视频', 'B 站'],
    summary: '作者整理的系列视频，适合不想读文档、跟着做一遍的人。',
  },
  {
    title: 'GitHub 仓库',
    url: 'https://github.com/Ikaros-521/AI-Vtuber',
    tags: ['源码', 'Issue'],
    summary: '源码、更新日志与提 Bug 的地方；本地文件缺失时也可以重新 clone。',
  },
]

export function DocsCard() {
  return (
    <div className="flex flex-col gap-5">
      <div className="grid gap-4 sm:grid-cols-2">
        {RESOURCES.map((item) => (
          <a
            key={item.url}
            href={item.url}
            target="_blank"
            rel="noreferrer"
            className="card-surface block p-4 transition hover:-translate-y-0.5 hover:shadow-md"
          >
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-[15px] font-semibold">{item.title}</span>
              <span className="text-xs font-medium" style={{ color: 'var(--accent)' }}>
                打开 ↗
              </span>
            </div>
            <p className="mt-1.5 text-[13px] leading-relaxed text-[var(--ink-mut)]">{item.summary}</p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {item.tags.map((tag) => (
                <span key={tag} className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] text-[var(--ink-mut)]">
                  {tag}
                </span>
              ))}
            </div>
          </a>
        ))}
      </div>

      <div className="card-surface p-5">
        <h3 className="text-[15px] font-semibold">关于</h3>
        <div className="mt-2 space-y-1.5 text-[13px] leading-relaxed text-[var(--ink-mut)]">
          <p>AI Vtuber —— 数字虚拟主播直播系统。当前界面是 v3 React 版 WebUI，与 v2（NiceGUI 版）并行运行，读写同一份 config.json。</p>
          <p>开源协议：AGPL-3.0（以仓库 LICENSE 为准）。</p>
          <p>
            v3 还在迁移中：声音与表现、互动与玩法两个工作区请继续用 v2 WebUI 配置；遇到 v3 的问题可以直接切回{' '}
            <code className="rounded bg-slate-100 px-1.5 py-0.5">webui.py</code>。
          </p>
        </div>
      </div>
    </div>
  )
}
