/** 声音与表现工作区：形象驱动(Avatar)、变声后期(SVC)、语音合成(TTS×14)、语音识别(STT)。

 * 字段与 config 键逐项对齐 v2 tts.py / talk.py / svc.py / visual_body.py。
 * TTS 调试卡与「检索说话人/加载模型」等按钮暂留 v2（涉及音频播放与本地模型加载）。
 */
import type { Workspace } from '../types'

const LANG_OPTIONS = { 自动: '自动', 中文: '中文', 英文: '英文', 日文: '日文' }
const GPT_SOVITS_PROMPT_LANG = { 中文: '中文', 英文: '英文', 日文: '日文', 中英混合: '中英混合', 日英混合: '日英混合', 多语种混合: '多语种混合' }
const GPT_SOVITS_TEXT_LANG = { 自动识别: '自动识别', ...GPT_SOVITS_PROMPT_LANG, 翻译: '翻译', 切句: '切句' }
const GPT_SOVITS_CUT = { 凑四句一切: '凑四句一切', 凑五句一切: '凑五句一切', '按中文句号切': '按中文句号切', '按英文句号切': '按英文句号切', '按标点符号切': '按标点符号切', 不切: '不切' }

export const voiceWorkspace: Workspace = {
  id: 'voice',
  title: '声音与表现',
  groups: [
    {
      title: '形象驱动 (Avatar)',
      sections: [
        {
          id: 'live2d',
          title: 'Live2D',
          showCard: ['visual_body', 'live2d'],
          desc: '基于 Web 端的 Live2D 虚拟形象驱动服务，支持口型同步、表情动作触发。',
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
          id: 'easyai',
          title: 'EasyAIVtuber',
          showCard: ['visual_body', 'EasyAIVtuber'],
          desc: '对接 EasyAIVtuber 客户端，实现轻量级二次元虚拟主播形象动作与说话联动。',
          rows: [[{ kind: 'input', key: ['EasyAIVtuber', 'api_ip_port'], label: 'API地址', w: 'md' }]],
        },
        {
          id: 'digital-human',
          title: '数字人视频播放器',
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
          id: 'live2d-combo',
          title: 'live2d_TTS_LLM_GPT_SoVITS_Vtuber',
          showCard: ['visual_body', 'live2d_TTS_LLM_GPT_SoVITS_Vtuber'],
          desc: '第三方开源 Live2D+LLM+GPT-SoVITS 一体化 Vtuber 推流客户端联动方案。',
          rows: [[{ kind: 'input', key: ['live2d_TTS_LLM_GPT_SoVITS_Vtuber', 'api_ip_port'], label: 'API地址', w: 'md' }]],
        },
        {
          id: 'xuniren',
          title: 'xuniren',
          showCard: ['visual_body', 'xuniren'],
          desc: '对接腾讯智影/虚拟人驱动服务，呈现高拟真口型同步与虚拟主播画面推流。',
          rows: [[{ kind: 'input', key: ['xuniren', 'api_ip_port'], label: 'API地址', w: 'md' }]],
        },
        {
          id: 'unity',
          title: 'Unity',
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
    {
      title: '变声后期 (SVC)',
      sections: [
        {
          id: 'ddsp-svc',
          title: 'DDSP-SVC',
          showCard: ['svc', 'ddsp_svc'],
          desc: '基于可微数字信号处理（DDSP）的超低延迟实时歌声与语音变声，适合直播实时换声。',
          rows: [
            [
              { kind: 'switch', key: ['ddsp_svc', 'enable'], label: '启用' },
              { kind: 'input', key: ['ddsp_svc', 'config_path'], label: '配置文件路径', w: 'md', placeholder: '模型配置文件config.yaml的路径（可不留，暂时没用到）' },
              { kind: 'input', key: ['ddsp_svc', 'api_ip_port'], label: 'API地址', w: 'md' },
              { kind: 'number', key: ['ddsp_svc', 'fSafePrefixPadLength'], label: '安全前缀填充长度', w: 'sm', placeholder: '默认为0' },
              { kind: 'number', key: ['ddsp_svc', 'fPitchChange'], label: '变调', w: 'xs', placeholder: '默认为0' },
              { kind: 'number', key: ['ddsp_svc', 'sSpeakId'], label: '说话人ID', w: 'xs', placeholder: '需和模型数据对应，默认为0' },
              { kind: 'number', key: ['ddsp_svc', 'sampleRate'], label: '采样率', w: 'sm', placeholder: 'DAW所需的采样率，默认44100' },
            ],
          ],
        },
        {
          id: 'so-vits-svc',
          title: 'SO-VITS-SVC',
          showCard: ['svc', 'so_vits_svc'],
          desc: '基于 SoftVC VITS 深度学习架构的高保真音色转换变声系统。',
          rows: [
            [
              { kind: 'switch', key: ['so_vits_svc', 'enable'], label: '启用' },
              { kind: 'input', key: ['so_vits_svc', 'config_path'], label: '配置文件路径', w: 'md', placeholder: '模型配置文件config.json的路径' },
              { kind: 'input', key: ['so_vits_svc', 'api_ip_port'], label: 'API地址', w: 'md' },
              { kind: 'input', key: ['so_vits_svc', 'spk'], label: '说话人', w: 'sm', placeholder: '需和配置文件内容对应' },
              { kind: 'number', key: ['so_vits_svc', 'tran'], label: '音调', w: 'xs', placeholder: '默认为1' },
              { kind: 'input', key: ['so_vits_svc', 'wav_format'], label: '输出音频格式', w: 'sm' },
            ],
          ],
        },
      ],
    },
    {
      title: '语音合成 (TTS)',
      sections: [
        {
          id: 'tts-debug',
          title: 'TTS 语音合成调试',
          custom: 'tts-tester',
          desc: '在线试听与快速测试当前配置的语音合成效果与音色表现。',
        },
        {
          id: 'edge-tts',
          title: 'Edge-TTS',
          showCard: ['tts', 'edge-tts'],
          desc: '微软 Edge 浏览器内置的高品质云端语音合成，免费免配置、多语言、开箱即用。',
          rows: [
            [
              { kind: 'input', key: ['edge-tts', 'voice'], label: '说话人', w: 'md', hint: '如 zh-CN-XiaoxiaoNeural；完整音色列表见微软文档，直接手输即可' },
              { kind: 'input', key: ['edge-tts', 'rate'], label: '语速增益', w: 'sm', placeholder: '默认 +0%，注意别搞丢 + - % 符号' },
              { kind: 'input', key: ['edge-tts', 'volume'], label: '音量增益', w: 'sm', placeholder: '默认 +0%' },
              { kind: 'input', key: ['edge-tts', 'proxy'], label: 'HTTP代理地址', w: 'md', placeholder: '例：http://127.0.0.1:10809' },
            ],
          ],
        },
        {
          id: 'vits',
          title: 'VITS-Simple-API',
          showCard: ['tts', 'vits'],
          desc: '基于 VITS-Simple-API 开源推理服务的本地/云端高拟真二次元音色生成。',
          rows: [
            [
              { kind: 'select', key: ['vits', 'type'], label: '类型', w: 'sm', options: { vits: 'vits', bert_vits2: 'bert_vits2', gpt_sovits: 'gpt_sovits' } },
              { kind: 'input', key: ['vits', 'config_path'], label: '配置文件路径', w: 'md', placeholder: '模型配置文件存储路径' },
              { kind: 'input', key: ['vits', 'api_ip_port'], label: 'API地址', w: 'md', placeholder: 'vits-simple-api启动后监听的ip端口地址' },
              { kind: 'number', key: ['vits', 'id'], label: '说话人ID', w: 'xs', int: true, hint: '不知道ID就点「检索说话人」，从返回列表里挑一个填进来' },
              { kind: 'action', key: ['_a', 'speakers'], label: '检索说话人', w: 'sm', action: 'vits-speakers', params: { api_ip_port: ['vits', 'api_ip_port'] } },
              { kind: 'select', key: ['vits', 'lang'], label: '语言', w: 'sm', options: LANG_OPTIONS },
            ],
            [
              { kind: 'number', key: ['vits', 'length'], label: '语音长度', w: 'sm', placeholder: '相当于调节语速，越大越慢' },
              { kind: 'number', key: ['vits', 'noise'], label: '噪声', w: 'sm', placeholder: '控制感情变化程度' },
              { kind: 'number', key: ['vits', 'noisew'], label: '噪声偏差', w: 'sm', placeholder: '控制音素发音长度' },
              { kind: 'number', key: ['vits', 'max'], label: '分段阈值', w: 'sm', placeholder: '按标点分段，加起来大于max为一段；<=0不分段' },
              { kind: 'input', key: ['vits', 'format'], label: '音频格式', w: 'sm', placeholder: '支持wav,ogg,silk,mp3,flac' },
              { kind: 'number', key: ['vits', 'sdp_radio'], label: 'SDP/DP混合比', w: 'sm', placeholder: '越高语调方差越大' },
            ],
          ],
          cards: [
            {
              id: 'vits-gpt-sovits',
              title: 'gpt_sovits（vits 模式）',
              rows: [
                [
                  { kind: 'number', key: ['vits', 'gpt_sovits', 'id'], label: '说话人ID', w: 'xs', int: true },
                  { kind: 'select', key: ['vits', 'gpt_sovits', 'lang'], label: '语言', w: 'sm', options: GPT_SOVITS_TEXT_LANG },
                  { kind: 'input', key: ['vits', 'gpt_sovits', 'format'], label: '音频格式', w: 'sm' },
                  { kind: 'number', key: ['vits', 'gpt_sovits', 'segment_size'], label: 'segment_size', w: 'xs', int: true },
                  { kind: 'input', key: ['vits', 'gpt_sovits', 'reference_audio'], label: '参考音频路径', w: 'md' },
                  { kind: 'input', key: ['vits', 'gpt_sovits', 'prompt_text'], label: '参考音频文本内容', w: 'md' },
                  { kind: 'select', key: ['vits', 'gpt_sovits', 'prompt_lang'], label: '参考音频语言', w: 'sm', options: GPT_SOVITS_PROMPT_LANG },
                  { kind: 'number', key: ['vits', 'gpt_sovits', 'top_k'], label: 'top_k', w: 'xs' },
                  { kind: 'number', key: ['vits', 'gpt_sovits', 'top_p'], label: 'top_p', w: 'xs' },
                  { kind: 'number', key: ['vits', 'gpt_sovits', 'temperature'], label: 'temperature', w: 'xs' },
                  { kind: 'input', key: ['vits', 'gpt_sovits', 'preset'], label: 'preset', w: 'sm' },
                ],
              ],
            },
          ],
        },
        {
          id: 'bert-vits2',
          title: 'bert_vits2',
          showCard: ['tts', 'bert_vits2'],
          desc: 'Bert-VITS2 情感语音合成系统，引入 BERT 增强语意，音调更自然富含情感。',
          rows: [
            [
              { kind: 'select', key: ['bert_vits2', 'type'], label: '类型', w: 'md', options: { hiyori: 'hiyori', '刘悦-中文特化API': '刘悦-中文特化API' } },
            ],
          ],
          cards: [
            {
              id: 'bert-vits2-hiyori',
              title: 'hiyori',
              rows: [
                [
                  { kind: 'input', key: ['bert_vits2', 'api_ip_port'], label: 'API地址', w: 'md' },
                  { kind: 'number', key: ['bert_vits2', 'model_id'], label: '模型ID', w: 'xs', int: true },
                  { kind: 'input', key: ['bert_vits2', 'speaker_name'], label: '说话人名称', w: 'sm' },
                  { kind: 'number', key: ['bert_vits2', 'speaker_id'], label: '说话人ID', w: 'xs', int: true },
                  { kind: 'select', key: ['bert_vits2', 'language'], label: '语言', w: 'sm', options: { zh: 'zh', ja: 'ja', en: 'en', mix: 'mix', auto: 'auto', auto_yue: 'auto_yue', yue: 'yue' } },
                ],
                [
                  { kind: 'number', key: ['bert_vits2', 'length'], label: '语音长度', w: 'sm' },
                  { kind: 'number', key: ['bert_vits2', 'noise'], label: '噪声', w: 'sm' },
                  { kind: 'number', key: ['bert_vits2', 'noisew'], label: '噪声偏差', w: 'sm' },
                  { kind: 'number', key: ['bert_vits2', 'sdp_radio'], label: 'SDP/DP混合比', w: 'sm' },
                  { kind: 'input', key: ['bert_vits2', 'emotion'], label: 'emotion', w: 'sm' },
                  { kind: 'input', key: ['bert_vits2', 'style_text'], label: '风格文本', w: 'sm' },
                  { kind: 'number', key: ['bert_vits2', 'style_weight'], label: '风格权重', w: 'sm', placeholder: '0仅主文本，1仅辅助文本' },
                  { kind: 'switch', key: ['bert_vits2', 'auto_translate'], label: '自动翻译' },
                  { kind: 'switch', key: ['bert_vits2', 'auto_split'], label: '自动切分' },
                ],
              ],
            },
            {
              id: 'bert-vits2-liuyue',
              title: '刘悦-中文特化API',
              rows: [
                [
                  { kind: 'input', key: ['bert_vits2', '刘悦-中文特化API', 'api_ip_port'], label: 'API地址', w: 'md' },
                  { kind: 'input', key: ['bert_vits2', '刘悦-中文特化API', 'speaker'], label: '说话人名称', w: 'sm' },
                  { kind: 'select', key: ['bert_vits2', '刘悦-中文特化API', 'language'], label: '语言', w: 'sm', options: { zh: 'zh' } },
                ],
                [
                  { kind: 'number', key: ['bert_vits2', '刘悦-中文特化API', 'length_scale'], label: '语音长度', w: 'sm' },
                  { kind: 'number', key: ['bert_vits2', '刘悦-中文特化API', 'interval_between_para'], label: 'interval_between_para', w: 'sm' },
                  { kind: 'number', key: ['bert_vits2', '刘悦-中文特化API', 'interval_between_sent'], label: 'interval_between_sent', w: 'sm' },
                  { kind: 'number', key: ['bert_vits2', '刘悦-中文特化API', 'noise_scale'], label: '噪声', w: 'sm' },
                  { kind: 'number', key: ['bert_vits2', '刘悦-中文特化API', 'noise_scale_w'], label: '噪声偏差', w: 'sm' },
                  { kind: 'number', key: ['bert_vits2', '刘悦-中文特化API', 'sdp_radio'], label: 'SDP/DP混合比', w: 'sm' },
                  { kind: 'input', key: ['bert_vits2', '刘悦-中文特化API', 'emotion'], label: 'emotion', w: 'sm' },
                  { kind: 'input', key: ['bert_vits2', '刘悦-中文特化API', 'style_text'], label: '风格文本', w: 'sm' },
                  { kind: 'number', key: ['bert_vits2', '刘悦-中文特化API', 'style_weight'], label: '风格权重', w: 'sm' },
                  { kind: 'switch', key: ['bert_vits2', '刘悦-中文特化API', 'cut_by_sent'], label: 'cut_by_sent' },
                ],
              ],
            },
          ],
        },
        {
          id: 'elevenlabs',
          title: 'elevenlabs',
          showCard: ['tts', 'elevenlabs'],
          desc: 'ElevenLabs 商业级极高拟真度多语言语音生成服务。',
          rows: [
            [
              { kind: 'input', key: ['elevenlabs', 'api_key'], label: 'api密钥', w: 'lg', placeholder: '可以不填，默认有一定免费额度' },
              { kind: 'input', key: ['elevenlabs', 'voice'], label: '说话人', w: 'md' },
              { kind: 'input', key: ['elevenlabs', 'model'], label: '模型', w: 'md' },
            ],
          ],
        },
        {
          id: 'openai-tts',
          title: 'OpenAI TTS',
          showCard: ['tts', 'openai_tts'],
          desc: 'OpenAI 官方语音合成模型（如 tts-1 / tts-1-hd），发音清晰自然。',
          rows: [
            [
              { kind: 'select', key: ['openai_tts', 'type'], label: '类型', w: 'sm', options: { api: 'api', huggingface: 'huggingface' } },
              { kind: 'input', key: ['openai_tts', 'api_ip_port'], label: 'API地址', w: 'md' },
              { kind: 'select', key: ['openai_tts', 'model'], label: '模型', w: 'sm', options: { 'tts-1': 'tts-1', 'tts-1-hd': 'tts-1-hd' } },
              { kind: 'select', key: ['openai_tts', 'voice'], label: '说话人', w: 'sm', options: { alloy: 'alloy', echo: 'echo', fable: 'fable', onyx: 'onyx', nova: 'nova', shimmer: 'shimmer' } },
              { kind: 'input', key: ['openai_tts', 'api_key'], label: 'api key', w: 'md' },
            ],
          ],
        },
        {
          id: 'gradio-tts',
          title: 'Gradio',
          showCard: ['tts', 'gradio_tts'],
          desc: '通用 Gradio WebUI TTS 接口对接，可连接各类以 Gradio 形式部署的语音合成服务。',
          rows: [
            [
              { kind: 'textarea', key: ['gradio_tts', 'request_parameters'], label: '请求参数', w: 'xl', placeholder: '{content}替换待合成文本；url是请求地址；fn_index是api索引；data_analysis是数据解析规则；参数顺序需和API请求一致' },
            ],
          ],
        },
        {
          id: 'gpt-sovits',
          title: 'GPT-SoVITS',
          showCard: ['tts', 'gpt_sovits'],
          desc: '少样本零样本语音克隆神器，仅需数秒音频即可精准复刻主播或特定角色声线。',
          rows: [
            [
              { kind: 'select', key: ['gpt_sovits', 'type'], label: 'API类型', w: 'md', options: { api: 'api', api_0322: 'api_0322', api_0706: 'api_0706', v2_api_0821: 'v2_api_0821', webtts: 'WebTTS', gradio_0322: 'gradio_0322' } },
              { kind: 'input', key: ['gpt_sovits', 'gradio_ip_port'], label: 'Gradio API地址', w: 'md' },
              { kind: 'input', key: ['gpt_sovits', 'api_ip_port'], label: 'API地址', w: 'md' },
              { kind: 'input', key: ['gpt_sovits', 'gpt_model_path'], label: 'GPT模型路径', w: 'lg', placeholder: '填绝对路径' },
              { kind: 'input', key: ['gpt_sovits', 'sovits_model_path'], label: 'SOVITS模型路径', w: 'lg', placeholder: '填绝对路径' },
            ],
          ],
          cards: [
            {
              id: 'gpt-sovits-api',
              title: 'api',
              rows: [
                [
                  { kind: 'input', key: ['gpt_sovits', 'ref_audio_path'], label: '参考音频路径', w: 'lg', placeholder: '建议填绝对路径' },
                  { kind: 'input', key: ['gpt_sovits', 'prompt_text'], label: '参考音频的文本', w: 'md' },
                  { kind: 'select', key: ['gpt_sovits', 'prompt_language'], label: '参考音频语言', w: 'sm', options: GPT_SOVITS_PROMPT_LANG },
                  { kind: 'select', key: ['gpt_sovits', 'language'], label: '文本语言', w: 'sm', options: GPT_SOVITS_TEXT_LANG },
                  { kind: 'select', key: ['gpt_sovits', 'cut'], label: '切分方式', w: 'sm', options: GPT_SOVITS_CUT },
                ],
              ],
            },
            {
              id: 'gpt-sovits-0322',
              title: 'api_0322 | gradio_0322',
              rows: [
                [
                  { kind: 'input', key: ['gpt_sovits', 'api_0322', 'ref_audio_path'], label: '参考音频路径', w: 'lg' },
                  { kind: 'input', key: ['gpt_sovits', 'api_0322', 'prompt_text'], label: '参考音频的文本', w: 'md' },
                  { kind: 'select', key: ['gpt_sovits', 'api_0322', 'prompt_lang'], label: '参考语言', w: 'sm', options: GPT_SOVITS_PROMPT_LANG },
                  { kind: 'select', key: ['gpt_sovits', 'api_0322', 'text_lang'], label: '文本语言', w: 'sm', options: GPT_SOVITS_TEXT_LANG },
                  { kind: 'select', key: ['gpt_sovits', 'api_0322', 'text_split_method'], label: '切分方式', w: 'sm', options: GPT_SOVITS_CUT },
                ],
                [
                  { kind: 'number', key: ['gpt_sovits', 'api_0322', 'top_k'], label: 'top_k', w: 'xs' },
                  { kind: 'number', key: ['gpt_sovits', 'api_0322', 'top_p'], label: 'top_p', w: 'xs' },
                  { kind: 'number', key: ['gpt_sovits', 'api_0322', 'temperature'], label: 'temperature', w: 'xs' },
                  { kind: 'number', key: ['gpt_sovits', 'api_0322', 'batch_size'], label: 'batch_size', w: 'xs', int: true },
                  { kind: 'number', key: ['gpt_sovits', 'api_0322', 'speed_factor'], label: 'speed_factor', w: 'xs' },
                  { kind: 'number', key: ['gpt_sovits', 'api_0322', 'fragment_interval'], label: '分段间隔(秒)', w: 'xs' },
                  { kind: 'switch', key: ['gpt_sovits', 'api_0322', 'split_bucket'], label: 'split_bucket' },
                  { kind: 'switch', key: ['gpt_sovits', 'api_0322', 'return_fragment'], label: 'return_fragment' },
                ],
              ],
            },
            {
              id: 'gpt-sovits-0706',
              title: 'api_0706',
              rows: [
                [
                  { kind: 'input', key: ['gpt_sovits', 'api_0706', 'refer_wav_path'], label: '参考音频路径', w: 'lg' },
                  { kind: 'input', key: ['gpt_sovits', 'api_0706', 'prompt_text'], label: '参考音频的文本', w: 'md' },
                  { kind: 'select', key: ['gpt_sovits', 'api_0706', 'prompt_language'], label: '参考语言', w: 'sm', options: GPT_SOVITS_PROMPT_LANG },
                  { kind: 'select', key: ['gpt_sovits', 'api_0706', 'text_language'], label: '文本语言', w: 'sm', options: GPT_SOVITS_TEXT_LANG },
                  { kind: 'input', key: ['gpt_sovits', 'api_0706', 'cut_punc'], label: '文本切分', w: 'sm', placeholder: '符号范围 ,.;?!、，。？！；：…' },
                ],
              ],
            },
            {
              id: 'gpt-sovits-0821',
              title: 'v2_api_0821',
              rows: [
                [
                  { kind: 'input', key: ['gpt_sovits', 'v2_api_0821', 'ref_audio_path'], label: '参考音频路径', w: 'lg' },
                  { kind: 'input', key: ['gpt_sovits', 'v2_api_0821', 'prompt_text'], label: '参考音频的文本', w: 'md' },
                  { kind: 'select', key: ['gpt_sovits', 'v2_api_0821', 'prompt_lang'], label: '参考语言', w: 'sm', options: GPT_SOVITS_PROMPT_LANG },
                  { kind: 'select', key: ['gpt_sovits', 'v2_api_0821', 'text_lang'], label: '文本语言', w: 'sm', options: GPT_SOVITS_TEXT_LANG },
                  { kind: 'select', key: ['gpt_sovits', 'v2_api_0821', 'text_split_method'], label: '切分方式', w: 'sm', options: GPT_SOVITS_CUT },
                ],
                [
                  { kind: 'number', key: ['gpt_sovits', 'v2_api_0821', 'top_k'], label: 'top_k', w: 'xs' },
                  { kind: 'number', key: ['gpt_sovits', 'v2_api_0821', 'top_p'], label: 'top_p', w: 'xs' },
                  { kind: 'number', key: ['gpt_sovits', 'v2_api_0821', 'temperature'], label: 'temperature', w: 'xs' },
                  { kind: 'number', key: ['gpt_sovits', 'v2_api_0821', 'batch_size'], label: 'batch_size', w: 'xs', int: true },
                  { kind: 'number', key: ['gpt_sovits', 'v2_api_0821', 'batch_threshold'], label: 'batch_threshold', w: 'xs' },
                  { kind: 'number', key: ['gpt_sovits', 'v2_api_0821', 'speed_factor'], label: 'speed_factor', w: 'xs' },
                  { kind: 'number', key: ['gpt_sovits', 'v2_api_0821', 'fragment_interval'], label: '分段间隔(秒)', w: 'xs' },
                  { kind: 'input', key: ['gpt_sovits', 'v2_api_0821', 'seed'], label: 'seed', w: 'xs' },
                  { kind: 'input', key: ['gpt_sovits', 'v2_api_0821', 'media_type'], label: 'media_type', w: 'xs' },
                  { kind: 'switch', key: ['gpt_sovits', 'v2_api_0821', 'split_bucket'], label: 'split_bucket' },
                  { kind: 'switch', key: ['gpt_sovits', 'v2_api_0821', 'parallel_infer'], label: 'parallel_infer' },
                  { kind: 'number', key: ['gpt_sovits', 'v2_api_0821', 'repetition_penalty'], label: 'repetition_penalty', w: 'xs' },
                ],
              ],
            },
            {
              id: 'gpt-sovits-webtts',
              title: 'WebTTS相关配置',
              desc: '基于浏览器端 Web Speech API 或网页端 TTS 服务生成音频。',
              rows: [
                [
                  { kind: 'select', key: ['gpt_sovits', 'webtts', 'version'], label: '版本', w: 'sm', options: { v1: 'v1', v2: 'v2' } },
                  { kind: 'input', key: ['gpt_sovits', 'webtts', 'api_ip_port'], label: 'API地址', w: 'md' },
                  { kind: 'input', key: ['gpt_sovits', 'webtts', 'spk'], label: '音色', w: 'sm' },
                  { kind: 'select', key: ['gpt_sovits', 'webtts', 'lang'], label: '语言', w: 'sm', options: { zh: '中文', en: '英文', ja: '日文' } },
                  { kind: 'number', key: ['gpt_sovits', 'webtts', 'speed'], label: '语速', w: 'xs' },
                  { kind: 'input', key: ['gpt_sovits', 'webtts', 'emotion'], label: '情感', w: 'sm' },
                ],
              ],
            },
          ],
        },
        {
          id: 'azure-tts',
          title: 'azure_tts',
          showCard: ['tts', 'azure_tts'],
          desc: '微软 Azure 认知服务官方语音合成，工业级稳定性和超丰富多国语言音色。',
          rows: [
            [
              { kind: 'input', key: ['azure_tts', 'subscription_key'], label: '密钥', w: 'md' },
              { kind: 'input', key: ['azure_tts', 'region'], label: '区域', w: 'md' },
              { kind: 'input', key: ['azure_tts', 'voice_name'], label: '说话人名', w: 'md', placeholder: 'Speech Studio平台试听获取说话人名' },
            ],
          ],
        },
        {
          id: 'cosyvoice',
          title: 'CosyVoice',
          showCard: ['tts', 'cosyvoice'],
          desc: '阿里通义实验室开源的多语言情感语音合成与零样本音色克隆模型。',
          rows: [
            [
              { kind: 'select', key: ['cosyvoice', 'type'], label: '类型', w: 'sm', options: { api_0819: 'api_0819', gradio_0707: 'gradio_0707' } },
              { kind: 'input', key: ['cosyvoice', 'gradio_ip_port'], label: 'Gradio API地址', w: 'md' },
              { kind: 'input', key: ['cosyvoice', 'api_ip_port'], label: 'API地址', w: 'md' },
            ],
          ],
          cards: [
            {
              id: 'cosyvoice-0707',
              title: 'gradio_0707',
              rows: [
                [
                  { kind: 'select', key: ['cosyvoice', 'gradio_0707', 'mode_checkbox_group'], label: '推理模式', w: 'md', options: { 预训练音色: '预训练音色', '3秒极速复刻': '3秒极速复刻', 跨语种复刻: '跨语种复刻', 自然语言控制: '自然语言控制' } },
                  { kind: 'input', key: ['cosyvoice', 'gradio_0707', 'sft_dropdown'], label: 'sft模型', w: 'sm' },
                  { kind: 'input', key: ['cosyvoice', 'gradio_0707', 'prompt_text'], label: 'prompt文本', w: 'sm', placeholder: '不用就留空' },
                  { kind: 'input', key: ['cosyvoice', 'gradio_0707', 'prompt_wav_upload'], label: 'prompt音频路径', w: 'sm', placeholder: '例如：E:\\1.wav' },
                  { kind: 'input', key: ['cosyvoice', 'gradio_0707', 'instruct_text'], label: 'instruct文本', w: 'sm', placeholder: '不用就留空' },
                  { kind: 'number', key: ['cosyvoice', 'gradio_0707', 'seed'], label: '随机推理种子', w: 'xs', placeholder: '默认0' },
                ],
              ],
            },
            {
              id: 'cosyvoice-0819',
              title: 'api_0819',
              rows: [
                [
                  { kind: 'input', key: ['cosyvoice', 'api_0819', 'speaker'], label: '说话人', w: 'sm' },
                  { kind: 'input', key: ['cosyvoice', 'api_0819', 'new'], label: 'new', w: 'xs', placeholder: '0' },
                  { kind: 'number', key: ['cosyvoice', 'api_0819', 'speed'], label: '语速', w: 'xs', placeholder: '1' },
                ],
              ],
            },
          ],
        },
        {
          id: 'f5-tts',
          title: 'F5-TTS',
          showCard: ['tts', 'f5_tts'],
          desc: '基于非自回归 Flow Matching 的零样本语音克隆框架，生成速度极快。',
          rows: [
            [
              { kind: 'select', key: ['f5_tts', 'type'], label: '类型', w: 'sm', options: { gradio_1023: 'gradio_1023' } },
              { kind: 'input', key: ['f5_tts', 'gradio_ip_port'], label: 'Gradio API地址', w: 'md' },
              { kind: 'select', key: ['f5_tts', 'model'], label: '模型', w: 'md', options: { F5TTS_Base: 'F5TTS_Base', F5TTS_Small: 'F5TTS_Small', E2TTS_Base: 'E2TTS_Base' } },
              { kind: 'input', key: ['f5_tts', 'ref_audio_orig'], label: '参考音频路径', w: 'sm', placeholder: '例如：E:\\1.wav' },
              { kind: 'input', key: ['f5_tts', 'ref_text'], label: '参考文本', w: 'sm', placeholder: '参考音频的文本' },
            ],
            [
              { kind: 'switch', key: ['f5_tts', 'remove_silence'], label: 'remove_silence' },
              { kind: 'number', key: ['f5_tts', 'cross_fade_duration'], label: 'cross_fade_duration', w: 'xs', placeholder: '0.15' },
              { kind: 'number', key: ['f5_tts', 'speed'], label: '语速', w: 'xs', placeholder: '默认1' },
            ],
          ],
        },
        {
          id: 'multitts',
          title: 'MultiTTS',
          showCard: ['tts', 'multitts'],
          desc: '对接安卓端 MultiTTS 语音引擎聚合服务端。',
          rows: [
            [
              { kind: 'input', key: ['multitts', 'api_ip_port'], label: 'API地址', w: 'md' },
              { kind: 'number', key: ['multitts', 'speed'], label: '语速', w: 'xs', placeholder: '0-100，默认1' },
              { kind: 'number', key: ['multitts', 'volume'], label: '音量', w: 'xs', placeholder: '0-100，默认50' },
              { kind: 'number', key: ['multitts', 'pitch'], label: '音调', w: 'xs', placeholder: '0-100，默认50' },
              { kind: 'input', key: ['multitts', 'voice'], label: '声音ID', w: 'sm', placeholder: '不填就是默认选中的发言人' },
            ],
          ],
        },
        {
          id: 'melotts',
          title: 'MeloTTS',
          showCard: ['tts', 'melotts'],
          desc: '轻量级极速多语言 TTS 库，CPU 上即可实现毫秒级快速合成。',
          rows: [
            [
              { kind: 'input', key: ['melotts', 'api_ip_port'], label: 'API地址', w: 'md' },
              { kind: 'input', key: ['melotts', 'language'], label: '语言', w: 'sm' },
              { kind: 'select', key: ['melotts', 'device'], label: '设备', w: 'xs', options: { auto: 'auto', cpu: 'cpu', cuda: 'cuda' } },
              { kind: 'switch', key: ['melotts', 'use_hf'], label: '使用HF默认模型' },
            ],
            [
              { kind: 'input', key: ['melotts', 'config_path'], label: '配置文件路径', w: 'md', placeholder: 'config.json路径' },
              { kind: 'input', key: ['melotts', 'ckpt_path'], label: '模型路径', w: 'md', placeholder: 'G_*.pth模型路径' },
              { kind: 'number', key: ['melotts', 'speaker_id'], label: '说话人ID', w: 'xs', int: true },
              { kind: 'number', key: ['melotts', 'sdp_ratio'], label: 'sdp_ratio', w: 'xs' },
              { kind: 'number', key: ['melotts', 'noise_scale'], label: 'noise_scale', w: 'xs' },
              { kind: 'number', key: ['melotts', 'noise_scale_w'], label: 'noise_scale_w', w: 'xs' },
              { kind: 'number', key: ['melotts', 'speed'], label: '语速', w: 'xs', placeholder: '0-10，默认1' },
            ],
          ],
        },
        {
          id: 'index-tts',
          title: 'Index-TTS',
          showCard: ['tts', 'index_tts'],
          desc: 'Index 语音合成模型接口，适用于特定训练音色。',
          rows: [
            [
              { kind: 'input', key: ['index_tts', 'api_ip_port'], label: 'API地址', w: 'md' },
              { kind: 'input', key: ['index_tts', 'prompt_audio'], label: 'prompt音频路径', w: 'md', placeholder: '例如：E:\\1.wav' },
              { kind: 'number', key: ['index_tts', 'temperature'], label: 'temperature', w: 'sm' },
            ],
          ],
        },
      ],
    },
    {
      title: '语音识别 (STT)',
      sections: [
        {
          id: 'talk-basic',
          title: '语音对话与拾音',
          desc: '通过本地麦克风捕捉说话声音并转写为文字，让主播能与 AI 进行面对面语音对话。声卡设备枚举和试录在 v2 语音页。',
          rows: [
            [
              { kind: 'switch', key: ['talk', 'key_listener_enable'], label: '启用按键监听', hint: '启用后可按录音按键启动语音识别对话' },
              { kind: 'switch', key: ['talk', 'direct_run_talk'], label: '直接语音对话', hint: '首次运行直接进入语音识别，不需手动按键；配合连续对话和唤醒词使用' },
              { kind: 'input', key: ['talk', 'device_index'], label: '声卡输入设备索引', w: 'sm', placeholder: '设备索引号' },
              { kind: 'action', key: ['_a', 'devices'], label: '枚举声卡', w: 'sm', action: 'audio-devices', hint: '列出本机声卡输入设备（索引=名称），把想要的索引填进左边' },
              { kind: 'switch', key: ['talk', 'no_recording_during_playback'], label: '播放中不进行录音', hint: '防止麦克风和扬声器太近导致循环录音' },
              { kind: 'number', key: ['talk', 'no_recording_during_playback_sleep_interval'], label: '播放中不录音的检测间隔(秒)', w: 'sm' },
              { kind: 'switch', key: ['talk', 'continuous_talk'], label: '连续对话', hint: '仅需按一次录音按键，按沉默阈值自动切分连续录音' },
            ],
            [
              { kind: 'select', key: ['talk', 'type'], label: '录音类型', w: 'sm', options: { google: 'google', baidu: 'baidu', faster_whisper: 'faster_whisper', sensevoice: 'sensevoice' } },
              { kind: 'input', key: ['talk', 'trigger_key'], label: '录音按键', w: 'sm', hint: '按键名参考 data/keyboard.txt（如 Q、Space），直接手输' },
              { kind: 'input', key: ['talk', 'stop_trigger_key'], label: '停止录音按键', w: 'sm', hint: '按键名参考 data/keyboard.txt，直接手输' },
              { kind: 'number', key: ['talk', 'volume_threshold'], label: '音量阈值', w: 'xs', placeholder: '触发录音的起始音量，按麦克风微调' },
              { kind: 'number', key: ['talk', 'silence_threshold'], label: '停录计数', w: 'xs', placeholder: '低于阈值的计数，越大切分越慢' },
              { kind: 'number', key: ['talk', 'CHANNELS'], label: 'CHANNELS', w: 'xs', int: true },
              { kind: 'number', key: ['talk', 'RATE'], label: 'RATE', w: 'xs', int: true },
            ],
          ],
        },
        {
          id: 'talk-interrupt',
          title: '对话打断',
          desc: '当主播插话或麦克风再次拾音时，立即中断正在播放的 AI 语音，体验如同真人交谈。',
          rows: [
            [
              { kind: 'switch', key: ['talk', 'interrupt_talk', 'enable'], label: '启用' },
              { kind: 'string-list', key: ['talk', 'interrupt_talk', 'keywords'], label: '打断关键词', w: 'md', placeholder: '如：等一下、住嘴，换行分隔' },
              { kind: 'checkboxes', key: ['talk', 'interrupt_talk', 'clean_type'], label: '清除类型', w: 'xl', options: { message_queue: '待合成消息队列', voice_tmp_path_queue: '待播放音频队列', audio_play: '正在播放中的音频' } },
            ],
          ],
        },
        {
          id: 'talk-wakeup',
          title: '语音唤醒与睡眠',
          desc: '设置唤醒词与休眠词，进入睡眠状态后将忽略普通对话。',
          rows: [
            [
              { kind: 'switch', key: ['talk', 'wakeup_sleep', 'enable'], label: '启用' },
              { kind: 'select', key: ['talk', 'wakeup_sleep', 'mode'], label: '模式', w: 'md', options: { 唤醒词触发: '唤醒词触发', 唤醒词常驻: '唤醒词常驻' } },
            ],
            [
              { kind: 'string-list', key: ['talk', 'wakeup_sleep', 'wakeup_word'], label: '唤醒词', w: 'sm', placeholder: '如：管家，换行分隔' },
              { kind: 'string-list', key: ['talk', 'wakeup_sleep', 'sleep_word'], label: '睡眠词', w: 'sm', placeholder: '如：关机，换行分隔' },
              { kind: 'string-list', key: ['talk', 'wakeup_sleep', 'wakeup_copywriting'], label: '唤醒提示语', w: 'md', placeholder: '如：在的，换行分隔' },
              { kind: 'string-list', key: ['talk', 'wakeup_sleep', 'sleep_copywriting'], label: '睡眠提示语', w: 'md', placeholder: '如：晚安，换行分隔' },
            ],
          ],
        },
        {
          id: 'talk-engines',
          title: 'STT 引擎配置',
          desc: '谷歌/百度/faster_whisper/SenseVoice 四家的识别参数。',
          rows: [
            [
              { kind: 'select', key: ['talk', 'google', 'tgt_lang'], label: '谷歌目标语言', w: 'sm', options: { zh: '中文', en: '英文', ja: '日文', ko: '韩文' } },
            ],
            [
              { kind: 'input', key: ['talk', 'baidu', 'app_id'], label: '百度AppID', w: 'sm' },
              { kind: 'input', key: ['talk', 'baidu', 'api_key'], label: '百度API Key', w: 'md' },
              { kind: 'input', key: ['talk', 'baidu', 'secret_key'], label: '百度Secret Key', w: 'md' },
            ],
            [
              { kind: 'input', key: ['talk', 'faster_whisper', 'model_size'], label: 'model_size', w: 'sm', placeholder: '如 tiny/base/small/medium/large-v3' },
              { kind: 'select', key: ['talk', 'faster_whisper', 'language'], label: 'language', w: 'sm', options: { 自动识别: '自动识别', zh: 'zh', en: 'en', ja: 'ja' } },
              { kind: 'select', key: ['talk', 'faster_whisper', 'device'], label: 'device', w: 'xs', options: { cuda: 'cuda', cpu: 'cpu', auto: 'auto' } },
              { kind: 'select', key: ['talk', 'faster_whisper', 'compute_type'], label: 'compute_type', w: 'sm', options: { float16: 'float16', int8_float16: 'int8_float16', int8: 'int8' } },
              { kind: 'input', key: ['talk', 'faster_whisper', 'download_root'], label: 'download_root', w: 'md', placeholder: '模型下载路径' },
              { kind: 'number', key: ['talk', 'faster_whisper', 'beam_size'], label: 'beam_size', w: 'xs', int: true, placeholder: '越大越准但越慢' },
            ],
            [
              { kind: 'input', key: ['talk', 'sensevoice', 'asr_model_path'], label: 'ASR 模型路径', w: 'md' },
              { kind: 'input', key: ['talk', 'sensevoice', 'vad_model_path'], label: 'VAD 模型路径', w: 'md' },
              { kind: 'number', key: ['talk', 'sensevoice', 'vad_max_single_segment_time'], label: 'VAD单段最大语音时间', w: 'sm', int: true },
              { kind: 'input', key: ['talk', 'sensevoice', 'device'], label: 'device', w: 'xs', placeholder: 'cpu / cuda' },
              { kind: 'select', key: ['talk', 'sensevoice', 'language'], label: 'language', w: 'sm', options: { auto: 'auto', zh: 'zh', en: 'en', yue: 'yue', ja: 'ja', ko: 'ko' } },
              { kind: 'input', key: ['talk', 'sensevoice', 'text_norm'], label: 'text_norm', w: 'xs' },
              { kind: 'number', key: ['talk', 'sensevoice', 'batch_size_s'], label: 'batch_size_s', w: 'xs', int: true },
              { kind: 'number', key: ['talk', 'sensevoice', 'batch_size'], label: 'batch_size', w: 'xs', int: true },
            ],
          ],
        },
      ],
    },
  ],
}
