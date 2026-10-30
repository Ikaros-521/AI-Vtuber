/** 基础设置 · 第 1 步「直播间」：平台选卡墙 + 直播间号 + 各平台对接表单。

 * 原 v3「直播接入」工作区拆分后的连接部分：开播四件套里的平台选择不再是一排下拉框，
 * 而是选卡墙（选中即所见）；音频播放等输出配置移去了「声音」步。
 */
import {
  AUDIO_PLAYER_OPTIONS,
  BILIBILI_LOGIN_TYPE_OPTIONS,
  LEGACY_LIVE_MONITOR_PLATFORMS,
  PLATFORM_OPTIONS,
} from '../options'
import type { Section, Workspace } from '../types'

export const platformWorkspace: Workspace = {
  id: 'platform',
  title: '直播间',
  pick: { key: ['platform'], options: PLATFORM_OPTIONS },
  groups: [
    {
      title: '直播间',
      sections: [
        {
          id: 'room-info',
          title: '直播间号',
          desc: '直播间网址最后一段的字母或数字。「直播弹幕监听助手」「聊天模式」等由外部决定监听对象的平台不用填。',
          rows: [
            [
              { kind: 'input', key: ['room_display_id'], label: '直播间号', w: 'md', placeholder: '一般为直播间URL最后/后面的字母或数字' },
            ],
          ],
        },
        {
          id: 'bilibili',
          title: '哔哩哔哩',
          pickValue: ['bilibili', 'bilibili2'],
          tags: ['扫码最稳'],
          desc: '推荐「哔哩哔哩2」走扫码登录；cookie 方式有极低的封号风险，强烈建议使用小号。',
          rows: [
            [
              { kind: 'select', key: ['bilibili', 'login_type'], label: '登录方式', w: 'md', options: BILIBILI_LOGIN_TYPE_OPTIONS, hint: '拿不准就用手机扫码，扫一次就行；cookie 和开放平台是进阶方式' },
            ],
          ],
          rowsAdvanced: [
            [
              { kind: 'input', key: ['bilibili', 'cookie'], label: 'cookie', w: 'xl', placeholder: 'b站登录后F12抓网络包获取，强烈建议使用小号！有封号风险，虽然实际上没听说有人被封过' },
              { kind: 'input', key: ['bilibili', 'ac_time_value'], label: 'ac_time_value', w: 'xl', placeholder: 'b站登录后，F12控制台，输入window.localStorage.ac_time_value获取(如果没有，请重新登录)' },
            ],
          ],
          cards: [
            {
              id: 'bilibili-open-live',
              title: '开放平台',
              rows: [
                [
                  { kind: 'input', key: ['bilibili', 'open_live', 'ACCESS_KEY_ID'], label: 'ACCESS_KEY_ID', w: 'md' },
                  { kind: 'input', key: ['bilibili', 'open_live', 'ACCESS_KEY_SECRET'], label: 'ACCESS_KEY_SECRET', w: 'md' },
                  { kind: 'input', key: ['bilibili', 'open_live', 'APP_ID'], label: '项目ID', w: 'sm', hint: '开放平台 创作者服务中心 项目ID' },
                  { kind: 'input', key: ['bilibili', 'open_live', 'ROOM_OWNER_AUTH_CODE'], label: '身份码', w: 'sm', hint: '直播中心用户 身份码' },
                ],
              ],
            },
          ],
        },
        {
          id: 'twitch',
          title: 'twitch',
          pickValue: 'twitch',
          tags: ['需代理'],
          desc: '海外平台，需要配好代理才能连接。',
          rows: [
            [
              { kind: 'input', key: ['twitch', 'token'], label: 'token', w: 'lg', placeholder: '访问 https://twitchapps.com/tmi/ 获取，格式为：oauth:xxx' },
              { kind: 'input', key: ['twitch', 'user'], label: '用户名', w: 'md', placeholder: '你的twitch账号用户名' },
            ],
            [
              { kind: 'input', key: ['twitch', 'proxy_server'], label: 'HTTP代理IP地址', w: 'md', placeholder: '代理软件，http协议监听的ip地址，一般为：127.0.0.1' },
              { kind: 'input', key: ['twitch', 'proxy_port'], label: 'HTTP代理端口', w: 'sm', placeholder: '代理软件，http协议监听的端口，一般为：1080' },
            ],
          ],
        },
        {
          id: 'live-monitor-assistant',
          title: '直播弹幕监听助手',
          // 快手2/拼多多/斗鱼/1688/淘宝 的弹幕都由助手推送，老配置里的这些平台值也归到这张卡
          pickValue: ['live_monitor_assistant', ...Object.keys(LEGACY_LIVE_MONITOR_PLATFORMS)],
          desc: '快手2、拼多多、斗鱼、1688、淘宝这些平台的弹幕，是由「直播弹幕监听助手」通过 websocket 推给本机的；监听哪个直播间由助手那边决定。',
          rows: [
            [
              { kind: 'input', key: ['live_monitor_assistant', 'ws_ip'], label: '监听IP', w: 'md', placeholder: '本机监听地址，一般为：127.0.0.1', hint: '助手和本程序在同一台电脑就填 127.0.0.1；助手在别的设备上就填这台设备对内开放的地址' },
              { kind: 'input', key: ['live_monitor_assistant', 'ws_port'], label: '监听端口', w: 'sm', placeholder: '默认 5001', hint: '助手侧要连接的端口，必须和这里一致。端口填得不合法时，程序会退回默认端口 5001 并在日志里报错' },
            ],
          ],
        },
      ],
    },
  ],
}

/** 音频输出策略（原「直播接入 · 音视频输出」），由「声音」步的「说话」页签引用。 */
export const audioOutputSections: Section[] = [
  {
    id: 'play-audio',
    title: '音频播放',
    showCard: ['common_config', 'play_audio'],
    desc: '音频的播放策略与输出路径。',
    rows: [
      [
        { kind: 'switch', key: ['play_audio', 'enable'], label: '启用' },
        { kind: 'switch', key: ['play_audio', 'text_split_enable'], label: '启用文本切分', hint: '启用后会将LLM等待合成音频的消息根据内部切分算法切分成多个短句，以便TTS快速合成' },
        { kind: 'switch', key: ['play_audio', 'info_to_callback'], label: '音频信息回传给内部接口', hint: '用于闲时任务的闲时清零功能。这个功能会一定程度的拖慢程序运行，如果你不需要闲时清零，可以关闭此功能来提高响应速度' },
      ],
    ],
    rowsAdvanced: [
      [
        { kind: 'number', key: ['play_audio', 'interval_num_min'], label: '间隔时间重复次数最小值', w: 'md', int: true, hint: '会在最大最小值之间随机生成一个重复次数，就是 次数 x 时间 = 最终间隔时间' },
        { kind: 'number', key: ['play_audio', 'interval_num_max'], label: '间隔时间重复次数最大值', w: 'md', int: true },
        { kind: 'number', key: ['play_audio', 'normal_interval_min'], label: '普通音频播放间隔最小值(秒)', w: 'md', int: true },
        { kind: 'number', key: ['play_audio', 'normal_interval_max'], label: '普通音频播放间隔最大值(秒)', w: 'md', int: true },
      ],
      [
        { kind: 'input', key: ['play_audio', 'out_path'], label: '音频输出路径', w: 'md', placeholder: '音频文件合成后存储的路径，支持相对路径或绝对路径' },
        { kind: 'select', key: ['play_audio', 'player'], label: '音频播放器', w: 'md', options: AUDIO_PLAYER_OPTIONS, hint: '默认pygame不需要再安装其他程序。audio player需要单独安装对接，详情看视频教程' },
        { kind: 'input', key: ['audio_player', 'api_ip_port'], label: 'audio_player API地址', w: 'md', placeholder: '只需要 http://ip:端口 即可', hint: '仅在 音频播放器：audio_player等，情况下填写' },
      ],
    ],
    cards: [
      {
        id: 'audio-random-speed',
        title: '音频随机变速',
        desc: '需要安装配置 ffmpeg 才能使用。',
        rows: [
          [
            { kind: 'switch', key: ['audio_random_speed', 'normal', 'enable'], label: '普通音频变速' },
            { kind: 'number', key: ['audio_random_speed', 'normal', 'speed_min'], label: '速度下限', w: 'sm', step: 0.1 },
            { kind: 'number', key: ['audio_random_speed', 'normal', 'speed_max'], label: '速度上限', w: 'sm', step: 0.1 },
          ],
          [
            { kind: 'switch', key: ['audio_random_speed', 'copywriting', 'enable'], label: '文案音频变速' },
            { kind: 'number', key: ['audio_random_speed', 'copywriting', 'speed_min'], label: '速度下限', w: 'sm', step: 0.1 },
            { kind: 'number', key: ['audio_random_speed', 'copywriting', 'speed_max'], label: '速度上限', w: 'sm', step: 0.1 },
          ],
        ],
      },
    ],
  },
  {
    id: 'web-captions-printer',
    title: 'web字幕打印机',
    showCard: ['common_config', 'web_captions_printer'],
    desc: '如果您使用了audio player来做音频播放，并开启了其web字幕打印机功能，那请勿启动此功能，因为这样就重复惹',
    rows: [
      [
        { kind: 'switch', key: ['web_captions_printer', 'enable'], label: '启用' },
        { kind: 'input', key: ['web_captions_printer', 'api_ip_port'], label: 'API地址', w: 'md', placeholder: '只需要 http://ip:端口 即可' },
      ],
    ],
  },
]
