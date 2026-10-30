/** 基础设置 · 第 4 步「形象」：虚拟身体选卡墙（visual_body），与 v2 visual_body.py 对齐。 */
import { VISUAL_BODY_OPTIONS } from '../options'
import type { Workspace } from '../types'

export const bodyWorkspace: Workspace = {
  id: 'body',
  title: '形象',
  pick: { key: ['visual_body'], options: VISUAL_BODY_OPTIONS },
  groups: [
    {
      title: '形象驱动',
      sections: [
        {
          // Live2D 由自身 enable 开关驱动，不占 visual_body 选项位，作为推荐路径常驻展示
          id: 'live2d',
          title: 'Live2D（推荐）',
          showCard: ['visual_body', 'live2d'],
          desc: '基于 Web 端的 Live2D 虚拟形象驱动服务，支持口型同步、表情动作触发。模型放本地即用，无需独立显卡——下面的选卡墙保持「其他（外置）」就能用。',
          rows: [
            [
              { kind: 'switch', key: ['live2d', 'enable'], label: '启用' },
              { kind: 'number', key: ['live2d', 'port'], label: '端口', w: 'sm', int: true, placeholder: 'web服务运行的端口号，默认：12345' },
              { kind: 'select', key: ['live2d', 'name'], label: '模型名', w: 'md', free: true, options: {}, dynamicOptions: 'live2d-models', hint: '点「刷新模型列表」从 Live2D/live2d-model 目录读取；也可以直接手输' },
              { kind: 'action', key: ['_a', 'models'], label: '刷新模型列表', w: 'sm', action: 'live2d-models' },
            ],
          ],
        },
        {
          id: 'digital-human',
          title: '数字人视频播放器',
          pickValue: 'digital_human_video_player',
          tags: ['需外部服务'],
          showCard: ['visual_body', 'digital_human_video_player'],
          desc: '基于预录制动作视频片段无缝切片轮播的数字人驱动（无需高性能独立显卡）。',
          rows: [
            [
              { kind: 'select', key: ['digital_human_video_player', 'type'], label: '类型', w: 'md', options: { metahuman_stream_ernerf: 'metahuman_stream_ernerf', metahuman_stream_musetalk: 'metahuman_stream_musetalk', metahuman_stream_wav2lip: 'metahuman_stream_wav2lip' } },
              { kind: 'input', key: ['digital_human_video_player', 'api_ip_port'], label: 'API地址', w: 'md' },
            ],
          ],
        },
        {
          id: 'metahuman',
          title: 'metahuman_stream',
          pickValue: 'metahuman_stream',
          tags: ['需外部服务'],
          showCard: ['visual_body', 'metahuman_stream'],
          desc: '对接虚幻引擎 MetaHuman 实时视频流驱动，呈现电影级超写实 3D 数字人。语音合成由 metahuman_stream 托管，不受本程序控制。',
          rows: [
            [
              { kind: 'select', key: ['metahuman_stream', 'type'], label: '类型', w: 'sm', options: { ernerf: 'ernerf', musetalk: 'musetalk', wav2lip: 'wav2lip' } },
              { kind: 'input', key: ['metahuman_stream', 'api_ip_port'], label: 'API地址', w: 'md' },
            ],
          ],
        },
        {
          id: 'easyai',
          title: 'EasyAIVtuber',
          pickValue: 'EasyAIVtuber',
          tags: ['需客户端'],
          showCard: ['visual_body', 'EasyAIVtuber'],
          desc: '对接 EasyAIVtuber 客户端，实现轻量级二次元虚拟主播形象动作与说话联动。',
          rows: [[{ kind: 'input', key: ['EasyAIVtuber', 'api_ip_port'], label: 'API地址', w: 'md' }]],
        },
        {
          id: 'live2d-combo',
          title: 'live2d_TTS_LLM_GPT_SoVITS_Vtuber',
          pickValue: 'live2d_TTS_LLM_GPT_SoVITS_Vtuber',
          tags: ['第三方'],
          showCard: ['visual_body', 'live2d_TTS_LLM_GPT_SoVITS_Vtuber'],
          desc: '第三方开源 Live2D+LLM+GPT-SoVITS 一体化 Vtuber 推流客户端联动方案。',
          rows: [[{ kind: 'input', key: ['live2d_TTS_LLM_GPT_SoVITS_Vtuber', 'api_ip_port'], label: 'API地址', w: 'md' }]],
        },
        {
          id: 'xuniren',
          title: 'xuniren',
          pickValue: 'xuniren',
          tags: ['需外部服务'],
          showCard: ['visual_body', 'xuniren'],
          desc: '对接腾讯智影/虚拟人驱动服务，呈现高拟真口型同步与虚拟主播画面推流。',
          rows: [[{ kind: 'input', key: ['xuniren', 'api_ip_port'], label: 'API地址', w: 'md' }]],
        },
        {
          id: 'unity',
          title: 'Unity',
          pickValue: 'unity',
          tags: ['需外部程序'],
          showCard: ['visual_body', 'unity'],
          desc: '通过 WebSocket / TCP 与 Unity 3D 虚拟主播项目联动，传递语音口型、骨骼动画与交互特效。',
          rows: [
            [
              { kind: 'input', key: ['unity', 'api_ip_port'], label: 'API地址', w: 'md' },
              { kind: 'input', key: ['unity', 'password'], label: '密码', w: 'md', password: true, placeholder: '对接Unity应用使用的HTTP中转站的密码' },
            ],
          ],
        },
      ],
    },
  ],
}
