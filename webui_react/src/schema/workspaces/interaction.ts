/** 互动与玩法工作区：点歌、积分、定时任务、闲时任务、动态配置、联网搜索、动态文案、
 * Stable Diffusion、文案播放。
 *
 * 字段与 config 键逐项对齐 v2 common_config.py（点歌/定时/闲时/搜索/动态文案/动态配置/SD）、
 * integral.py 与 copywriting.py。
 */
import { AUDIO_SYNTHESIS_TYPE_OPTIONS, CHAT_TYPE_OPTIONS } from '../options'
import type { Field, Workspace } from '../types'

/** 区间文案动态组（签到数/礼物价格/入场数区间 → 文案），积分三处复用。 */
function intervalCopywriting(prefix: (string | number)[], intervalKey: string, intervalLabel: string, itemTitle: string): Field {
  return {
    kind: 'group-list',
    key: [...prefix, 'copywriting'],
    label: `${itemTitle}文案`,
    w: 'xl',
    itemTitle,
    addLabel: `增加${itemTitle}文案组`,
    itemDefaults: { [intervalKey]: '', copywriting: [] } as Record<string, unknown>,
    rows: [
      [
        { kind: 'input', key: [intervalKey], label: intervalLabel, w: 'md', placeholder: '用-号划分区间，包含边界值' },
        { kind: 'string-list', key: ['copywriting'], label: '文案', w: 'xl', placeholder: '在此区间内触发的文案内容，换行分隔' },
      ],
    ],
  }
}

export const interactionWorkspace: Workspace = {
  id: 'interaction',
  title: '互动与玩法',
  groups: [
    {
      title: '直播间互动',
      sections: [
        {
          id: 'choose-song',
          title: '点歌模式',
          showCard: ['common_config', 'choose_song'],
          desc: '弹幕点歌玩法：观众发送「点歌 歌名」自动检索并播放歌曲，支持插队与优先级排序。',
          rows: [
            [
              { kind: 'switch', key: ['choose_song', 'enable'], label: '启用' },
              { kind: 'string-list', key: ['choose_song', 'start_cmd'], label: '点歌触发命令', w: 'sm', placeholder: '换行分隔，弹幕发送触发（完全匹配才行）' },
              { kind: 'string-list', key: ['choose_song', 'stop_cmd'], label: '取消点歌命令', w: 'sm', placeholder: '换行分隔，弹幕发送触发（完全匹配才行）' },
              { kind: 'string-list', key: ['choose_song', 'random_cmd'], label: '随机点歌命令', w: 'sm', placeholder: '换行分隔，弹幕发送触发（完全匹配才行）' },
            ],
            [
              { kind: 'input', key: ['choose_song', 'song_path'], label: '歌曲路径', w: 'md', placeholder: '歌曲音频存放的路径，会自动读取音频文件' },
              { kind: 'input', key: ['choose_song', 'match_fail_copy'], label: '匹配失败文案', w: 'xl', placeholder: '注意 {content} 用于替换用户发送的歌名，请勿乱删' },
              { kind: 'number', key: ['choose_song', 'similarity'], label: '匹配最低相似度', w: 'sm', placeholder: '低了就会被当做一般弹幕处理' },
            ],
          ],
        },
        {
          id: 'integral',
          title: '积分系统',
          desc: '签到、礼物、入场送积分；区间文案按积累量播报。',
          rows: [[{ kind: 'switch', key: ['integral', 'enable'], label: '启用' }]],
          cards: [
            {
              id: 'integral-sign',
              title: '签到',
              rows: [
                [
                  { kind: 'switch', key: ['integral', 'sign', 'enable'], label: '启用' },
                  { kind: 'number', key: ['integral', 'sign', 'get_integral'], label: '获得积分数', w: 'sm', int: true, placeholder: '签到成功可以获得的积分数，请填写正整数' },
                  { kind: 'string-list', key: ['integral', 'sign', 'cmd'], label: '命令', w: 'md', placeholder: '弹幕发送以下命令可以触发签到功能，换行分隔命令' },
                ],
                [intervalCopywriting(['integral', 'sign'], 'sign_num_interval', '签到数区间', '签到')],
              ],
            },
            {
              id: 'integral-gift',
              title: '礼物',
              rows: [
                [
                  { kind: 'switch', key: ['integral', 'gift', 'enable'], label: '启用' },
                  { kind: 'number', key: ['integral', 'gift', 'get_integral_proportion'], label: '获得积分比例', w: 'sm', placeholder: '和礼物真实金额（元）挂钩，默认 1元=10积分' },
                ],
                [intervalCopywriting(['integral', 'gift'], 'gift_price_interval', '礼物价格区间', '礼物')],
              ],
            },
            {
              id: 'integral-entrance',
              title: '入场',
              rows: [
                [
                  { kind: 'switch', key: ['integral', 'entrance', 'enable'], label: '启用' },
                  { kind: 'number', key: ['integral', 'entrance', 'get_integral'], label: '获得积分数', w: 'sm', int: true },
                ],
                [intervalCopywriting(['integral', 'entrance'], 'entrance_num_interval', '入场数区间', '入场')],
              ],
            },
            {
              id: 'integral-crud',
              title: '增删改查',
              desc: '观众查询自己积分的命令。',
              rows: [
                [
                  { kind: 'switch', key: ['integral', 'crud', 'query', 'enable'], label: '查询启用' },
                  { kind: 'string-list', key: ['integral', 'crud', 'query', 'cmd'], label: '命令', w: 'md', placeholder: '弹幕发送触发查询功能，换行分隔命令' },
                  { kind: 'string-list', key: ['integral', 'crud', 'query', 'copywriting'], label: '文案', w: 'xl', placeholder: '触发查询功能后返回的文案内容' },
                ],
              ],
            },
          ],
        },
        {
          id: 'sd',
          title: 'Stable Diffusion',
          showCard: ['common_config', 'sd'],
          desc: '弹幕绘图玩法：观众发送指令让 AI 实时画画，并在直播间动态展示生成的画面。',
          rows: [
            [
              { kind: 'switch', key: ['sd', 'enable'], label: '启用' },
              { kind: 'select', key: ['sd', 'translate_type'], label: '翻译类型', w: 'sm', options: { none: '不启用', baidu: '百度翻译', google: '谷歌翻译' }, hint: '针对触发的画图命令使用翻译页的配置，进行翻译后再丢给SD画图' },
              { kind: 'select', key: ['sd', 'prompt_llm', 'type'], label: 'LLM类型', w: 'md', options: CHAT_TYPE_OPTIONS },
              { kind: 'input', key: ['sd', 'prompt_llm', 'before_prompt'], label: '提示词前缀', w: 'md' },
              { kind: 'input', key: ['sd', 'prompt_llm', 'after_prompt'], label: '提示词后缀', w: 'md' },
            ],
            [
              { kind: 'input', key: ['sd', 'trigger'], label: '弹幕触发前缀', w: 'sm', placeholder: '触发的关键词（弹幕头部触发）' },
              { kind: 'input', key: ['sd', 'ip'], label: 'IP地址', w: 'md' },
              { kind: 'number', key: ['sd', 'port'], label: '端口', w: 'xs', int: true },
              { kind: 'input', key: ['sd', 'negative_prompt'], label: '负面提示词', w: 'md', placeholder: '用于指定与生成图像相矛盾或相反的内容' },
              { kind: 'number', key: ['sd', 'seed'], label: '随机种子', w: 'sm', int: true, placeholder: '设置整数值可获得可重复的结果' },
              { kind: 'string-list', key: ['sd', 'styles'], label: '图像风格', w: 'sm', placeholder: '例如 ["anime", "portrait"]' },
            ],
            [
              { kind: 'number', key: ['sd', 'cfg_scale'], label: '提示词相关性', w: 'sm' },
              { kind: 'number', key: ['sd', 'steps'], label: '生成图像步数', w: 'sm', int: true },
              { kind: 'number', key: ['sd', 'hr_resize_x'], label: '图像水平像素', w: 'sm', int: true },
              { kind: 'number', key: ['sd', 'hr_resize_y'], label: '图像垂直像素', w: 'sm', int: true },
              { kind: 'number', key: ['sd', 'denoising_strength'], label: '去噪强度', w: 'sm' },
            ],
            [
              { kind: 'switch', key: ['sd', 'enable_hr'], label: '高分辨率生成' },
              { kind: 'number', key: ['sd', 'hr_scale'], label: '高分辨率缩放因子', w: 'sm' },
              { kind: 'number', key: ['sd', 'hr_second_pass_steps'], label: '高分二次传递步数', w: 'sm', int: true },
              { kind: 'switch', key: ['sd', 'save_enable'], label: '保存图片到本地' },
              { kind: 'switch', key: ['sd', 'loop_cover'], label: '本地图片循环覆盖' },
              { kind: 'input', key: ['sd', 'save_path'], label: '图片保存路径', w: 'md', placeholder: '生成图片存储路径，不建议修改' },
            ],
          ],
        },
        {
          id: 'copywriting',
          title: '文案播放',
          desc: '文案音频轮播：多组播放列表按连续播放数/时长切换，弹幕来了暂停让位。合成与试听入口在 v2。',
          rows: [
            [
              { kind: 'switch', key: ['copywriting', 'auto_play'], label: '自动播放' },
              { kind: 'switch', key: ['copywriting', 'random_play'], label: '音频随机播放' },
              { kind: 'number', key: ['copywriting', 'audio_interval'], label: '音频播放间隔', w: 'sm', placeholder: '前一个文案播放完到下一个开始之间的间隔时间（秒）' },
              { kind: 'number', key: ['copywriting', 'switching_interval'], label: '音频切换间隔', w: 'sm', placeholder: '文案音频与弹幕音频互相切换的间隔时间（秒）' },
            ],
            [
              { kind: 'input', key: ['copywriting', 'text_path'], label: '文案文本路径', w: 'md', placeholder: '待合成的文案文本文件的路径（合成入口在 v2 文案页）' },
              { kind: 'input', key: ['copywriting', 'audio_save_path'], label: '音频存储路径', w: 'md' },
              { kind: 'select', key: ['copywriting', 'audio_synthesis_type'], label: '合成TTS', w: 'md', options: AUDIO_SYNTHESIS_TYPE_OPTIONS },
            ],
            [
              {
                kind: 'group-list',
                key: ['copywriting', 'config'],
                label: '文案组',
                w: 'xl',
                itemTitle: '文案组',
                addLabel: '增加文案组',
                itemDefaults: { file_path: '', audio_path: '', continuous_play_num: 1, max_play_time: 120, play_list: [] },
                rows: [
                  [
                    { kind: 'input', key: ['file_path'], label: '文案存储路径', w: 'md', placeholder: '文案文件存储路径。不建议更改' },
                    { kind: 'input', key: ['audio_path'], label: '音频存储路径', w: 'md', placeholder: '文案音频文件存储路径。不建议更改' },
                    { kind: 'number', key: ['continuous_play_num'], label: '连续播放数', w: 'sm', int: true, placeholder: '超过这个个数就切换下一个文案列表' },
                    { kind: 'number', key: ['max_play_time'], label: '连续播放时间', w: 'sm', placeholder: '超过这个时长（秒）就切换下一个文案列表' },
                  ],
                  [
                    { kind: 'string-list', key: ['play_list'], label: '播放列表', w: 'xl', placeholder: '要播放的音频文件全名，从音频列表中复制，换行分隔' },
                  ],
                ],
              },
            ],
          ],
        },
      ],
    },
    {
      title: '运营与保活',
      sections: [
        {
          id: 'schedule',
          title: '定时任务',
          showCard: ['common_config', 'schedule'],
          desc: '周期性广播与通知：按随机周期循环播报指定公告或互动提示。',
          rows: [
            [
              {
                kind: 'group-list',
                key: ['schedule'],
                label: '任务组',
                w: 'xl',
                itemTitle: '任务',
                addLabel: '增加任务组',
                itemDefaults: { enable: false, time_min: 3600, time_max: 7200, copy: [] },
                rows: [
                  [
                    { kind: 'switch', key: ['enable'], label: '启用任务' },
                    { kind: 'number', key: ['time_min'], label: '最小循环周期(秒)', w: 'sm', placeholder: '最终周期从最大最小之间随机生成' },
                    { kind: 'number', key: ['time_max'], label: '最大循环周期(秒)', w: 'sm' },
                    { kind: 'string-list', key: ['copy'], label: '文案列表', w: 'xl', placeholder: '通过{变量}替换关键数据，如 {time}' },
                  ],
                ],
              },
            ],
          ],
        },
        {
          id: 'idle-time-task',
          title: '闲时任务',
          showCard: ['common_config', 'idle_time_task'],
          desc: '直播间冷场自动保活：一段时间没有弹幕时，AI 自动发起话题暖场，防止冷场。',
          rows: [
            [
              { kind: 'switch', key: ['idle_time_task', 'enable'], label: '启用' },
              {
                kind: 'select',
                key: ['idle_time_task', 'type'],
                label: '机制类型',
                w: 'md',
                options: { 待合成消息队列更新闲时: '待合成消息队列更新闲时', 待播放音频队列更新闲时: '待播放音频队列更新闲时', 直播间无消息更新闲时: '直播间无消息更新闲时' },
                hint: '带货推荐「待播放音频队列」+触发值1；不需要一直说话的场景推荐「直播间无消息」+大间隔',
              },
            ],
            [
              { kind: 'number', key: ['idle_time_task', 'min_msg_queue_len_to_trigger'], label: '待合成消息队列个数小于此值时触发', w: 'md', int: true },
              { kind: 'number', key: ['idle_time_task', 'min_audio_queue_len_to_trigger'], label: '待播放音频队列个数小于此值时触发', w: 'md', int: true },
            ],
            [
              { kind: 'number', key: ['idle_time_task', 'idle_time_min'], label: '最小闲时时间(秒)', w: 'sm', int: true },
              { kind: 'number', key: ['idle_time_task', 'idle_time_max'], label: '最大闲时时间(秒)', w: 'sm', int: true },
              { kind: 'number', key: ['idle_time_task', 'wait_play_audio_num_threshold'], label: '等待播放音频数量阈值', w: 'sm', int: true, hint: '超过阈值时播放完毕后把闲时计时压到下面的缩减值，控制触发总量' },
              { kind: 'number', key: ['idle_time_task', 'idle_time_reduce_to'], label: '闲时计时减小到', w: 'sm', int: true },
            ],
            [
              { kind: 'checkboxes', key: ['idle_time_task', 'trigger_type'], label: '刷新闲时计时的消息类型', w: 'xl', options: { comment: '弹幕', gift: '礼物', entrance: '入场', follow: '关注' } },
            ],
            [
              { kind: 'switch', key: ['idle_time_task', 'copywriting', 'enable'], label: '文案模式' },
              { kind: 'switch', key: ['idle_time_task', 'copywriting', 'random'], label: '随机文案' },
              { kind: 'string-list', key: ['idle_time_task', 'copywriting', 'copy'], label: '文案列表', w: 'xl', placeholder: '文案会丢LLM处理后合成播放' },
            ],
            [
              { kind: 'switch', key: ['idle_time_task', 'comment', 'enable'], label: '弹幕触发LLM模式' },
              { kind: 'switch', key: ['idle_time_task', 'comment', 'random'], label: '随机弹幕' },
              { kind: 'string-list', key: ['idle_time_task', 'comment', 'copy'], label: '弹幕列表', w: 'xl', placeholder: '弹幕会丢LLM处理后合成播放' },
            ],
            [
              { kind: 'switch', key: ['idle_time_task', 'local_audio', 'enable'], label: '本地音频模式' },
              { kind: 'switch', key: ['idle_time_task', 'local_audio', 'random'], label: '随机本地音频' },
              { kind: 'string-list', key: ['idle_time_task', 'local_audio', 'path'], label: '本地音频路径列表', w: 'xl', placeholder: '相对/绝对路径换行分隔，音频直接进播放队列' },
            ],
          ],
        },
        {
          id: 'trends-config',
          title: '动态配置',
          showCard: ['common_config', 'trends_config'],
          desc: '按直播间在线人数自动切换整份配置文件。',
          rows: [
            [
              { kind: 'switch', key: ['trends_config', 'enable'], label: '启用' },
              {
                kind: 'group-list',
                key: ['trends_config', 'path'],
                label: '人数区间映射',
                w: 'xl',
                itemTitle: '区间',
                addLabel: '增加区间映射',
                itemDefaults: { online_num: '0-10', path: 'config.json' },
                rows: [
                  [
                    { kind: 'input', key: ['online_num'], label: '在线人数范围', w: 'sm', placeholder: '用减号-分隔，例如：0-10' },
                    { kind: 'input', key: ['path'], label: '配置路径', w: 'md', placeholder: '此人数区间加载的配置文件路径' },
                  ],
                ],
              },
            ],
          ],
        },
        {
          id: 'search-online',
          title: '联网搜索',
          showCard: ['common_config', 'search_online'],
          desc: '命中关键词时先检索网页，把结果拼进问题再交给 LLM 回答。',
          rows: [
            [
              { kind: 'switch', key: ['search_online', 'enable'], label: '启用' },
              { kind: 'switch', key: ['search_online', 'keyword_enable'], label: '关键词触发' },
              { kind: 'string-list', key: ['search_online', 'before_keyword'], label: '关键词前缀', w: 'sm', placeholder: '例如配置【联网：】则 联网：杭州天气 会触发' },
              { kind: 'select', key: ['search_online', 'engine'], label: '搜索引擎', w: 'sm', options: { baidu: '百度搜索', google: '谷歌搜索' } },
              { kind: 'number', key: ['search_online', 'engine_id'], label: '引擎ID', w: 'xs', int: true, placeholder: '默认1，不建议修改' },
              { kind: 'number', key: ['search_online', 'count'], label: '检索的文章数', w: 'xs', int: true, placeholder: '默认1，内容为空可适当扩大' },
            ],
            [
              { kind: 'input', key: ['search_online', 'resp_template'], label: '结果模板', w: 'xl', placeholder: '检索后数据以此模板生成问题，请勿删除{}里的两个变量' },
              { kind: 'input', key: ['search_online', 'http_proxy'], label: 'HTTP代理地址', w: 'md' },
              { kind: 'input', key: ['search_online', 'https_proxy'], label: 'HTTPS代理地址', w: 'md' },
            ],
          ],
        },
        {
          id: 'trends-copywriting',
          title: '动态文案',
          showCard: ['common_config', 'trends_copywriting'],
          desc: '文件夹文案库轮播：从指定文件夹读取文案，支持由大语言模型二次润色后再播报。',
          rows: [
            [
              { kind: 'switch', key: ['trends_copywriting', 'enable'], label: '启用' },
              { kind: 'select', key: ['trends_copywriting', 'llm_type'], label: 'LLM类型', w: 'md', options: CHAT_TYPE_OPTIONS },
              { kind: 'switch', key: ['trends_copywriting', 'random_play'], label: '随机播放' },
              { kind: 'number', key: ['trends_copywriting', 'play_interval'], label: '文案播放间隔(秒)', w: 'sm' },
            ],
            [
              {
                kind: 'group-list',
                key: ['trends_copywriting', 'copywriting'],
                label: '文案组',
                w: 'xl',
                itemTitle: '文案',
                addLabel: '增加文案组',
                itemDefaults: { folder_path: '', prompt_change_enable: false, prompt_change_content: '' },
                rows: [
                  [
                    { kind: 'input', key: ['folder_path'], label: '文案路径', w: 'md', placeholder: '文案文件存储的文件夹路径' },
                    { kind: 'switch', key: ['prompt_change_enable'], label: '提示词转换' },
                    { kind: 'input', key: ['prompt_change_content'], label: '提示词转换内容', w: 'xl', placeholder: '用此提示词对文案内容转换后再合成，使用聊天类型配置的LLM' },
                  ],
                ],
              },
            ],
          ],
        },
      ],
    },
  ],
}
