/** 运维与系统工作区：日志/数据库/异常报警/数据分析、webui 自身配置、板块开关、账号、文档。

 * 字段与 config 键逐项对齐 v2 common_config.py（日志/数据库/异常报警）与
 * web_page.py（webui配置/本地路径映射/配置模板/账号管理）。
 * 板块开关墙与文档资源卡是两个专用组件（SystemExtras.tsx），由 custom 标记挂载。
 */
import type { Field, Workspace } from '../types'

function alarmRow(prefix: string, label: string): Field[] {
  return [
    { kind: 'switch', key: ['abnormal_alarm', prefix, 'enable'], label: `启用${label}报警` },
    { kind: 'select', key: ['abnormal_alarm', prefix, 'type'], label: '类型', w: 'xs', options: { local_audio: '本地音频' } },
    { kind: 'number', key: ['abnormal_alarm', prefix, 'start_alarm_error_num'], label: '开始报警错误数', w: 'sm', int: true, placeholder: '超过这个数后就会报警' },
    { kind: 'number', key: ['abnormal_alarm', prefix, 'auto_restart_error_num'], label: '自动重启错误数', w: 'sm', int: true, placeholder: '记得先启用「自动运行」；超过这个数后自动重启webui' },
    { kind: 'input', key: ['abnormal_alarm', prefix, 'local_audio_path'], label: '本地音频路径', w: 'lg', placeholder: '本地音频存储的文件路径（可以是多个音频，随机一个）' },
  ]
}

export const systemWorkspace: Workspace = {
  id: 'system',
  title: '运维与系统',
  groups: [
    {
      title: '监控与数据',
      sections: [
        {
          id: 'log',
          title: '日志',
          showCard: ['common_config', 'log'],
          desc: '字幕与问答日志的落盘开关。',
          rows: [
            [
              { kind: 'switch', key: ['captions', 'enable'], label: '启用' },
              { kind: 'select', key: ['comment_log_type'], label: '弹幕日志类型', w: 'sm', options: { 问答: '问答', 问题: '问题', 回答: '回答', 不记录: '不记录' } },
              { kind: 'input', key: ['captions', 'file_path'], label: '字幕日志路径', w: 'md', placeholder: '字幕日志存储路径' },
              { kind: 'input', key: ['captions', 'raw_file_path'], label: '原文字幕日志路径', w: 'md', placeholder: '原文字幕日志存储路径' },
            ],
          ],
        },
        {
          id: 'database',
          title: '数据库',
          showCard: ['common_config', 'database'],
          desc: '弹幕/入场/礼物记录写入 SQLite 数据库的开关，供数据分析页统计。',
          rows: [
            [
              { kind: 'switch', key: ['database', 'comment_enable'], label: '弹幕日志' },
              { kind: 'switch', key: ['database', 'entrance_enable'], label: '入场日志' },
              { kind: 'switch', key: ['database', 'gift_enable'], label: '礼物日志' },
              { kind: 'input', key: ['database', 'path'], label: '数据库路径', w: 'md', placeholder: '数据库文件存储路径' },
            ],
          ],
        },
        {
          id: 'abnormal-alarm',
          title: '异常报警',
          showCard: ['common_config', 'abnormal_alarm'],
          desc: '各模块连续报错时播放本地音频提醒，超过阈值可自动重启 webui（需先启用「自动运行」）。',
          rows: [
            alarmRow('platform', '平台'),
            alarmRow('llm', 'LLM'),
            alarmRow('tts', 'TTS'),
            alarmRow('svc', 'SVC'),
            alarmRow('visual_body', '虚拟身体'),
            alarmRow('other', '其他'),
          ],
        },
        {
          id: 'data-analysis',
          title: '数据分析',
          desc: '词云与榜单的取数参数。图表本体还在 v2 WebUI（echart），这里先把参数迁过来。',
          rows: [
            [
              { kind: 'number', key: ['data_analysis', 'comment_word_cloud', 'top_num'], label: '词云前N个关键词', w: 'sm', int: true, placeholder: '筛选前N个弹幕关键词做为词云数据' },
              { kind: 'number', key: ['data_analysis', 'integral', 'top_num'], label: '榜单Top N', w: 'sm', int: true, placeholder: '积分/观看/签到/金额榜的取数条数' },
              { kind: 'number', key: ['data_analysis', 'gift', 'top_num'], label: '礼物榜Top N', w: 'sm', int: true },
            ],
          ],
        },
      ],
    },
    {
      title: '系统与设置',
      sections: [
        {
          id: 'webui-config',
          title: 'webui配置',
          desc: 'WebUI 自身的监听参数；改完需要重启 webui 才生效。',
          rows: [
            [
              { kind: 'input', key: ['webui', 'title'], label: '标题', w: 'lg', placeholder: 'webui的标题' },
              { kind: 'input', key: ['webui', 'ip'], label: 'IP地址', w: 'sm', placeholder: 'webui监听的IP地址' },
              { kind: 'number', key: ['webui', 'port'], label: '端口', w: 'xs', int: true, placeholder: 'webui监听的端口' },
              { kind: 'switch', key: ['webui', 'auto_run'], label: '自动运行', hint: 'webui 启动后自动运行 main.py' },
            ],
          ],
        },
        {
          id: 'local-dir',
          title: '本地路径指定URL路径访问',
          desc: '把本地文件夹映射成 webui 的静态 URL（如音频输出目录），改完需重启生效。',
          rows: [
            [
              { kind: 'switch', key: ['webui', 'local_dir_to_endpoint', 'enable'], label: '启用' },
              {
                kind: 'group-list',
                key: ['webui', 'local_dir_to_endpoint', 'config'],
                label: '映射配置组',
                w: 'xl',
                itemTitle: '映射',
                addLabel: '增加映射组',
                itemDefaults: { url_path: '', local_dir: '' },
                rows: [
                  [
                    { kind: 'input', key: ['url_path'], label: 'URL路径', w: 'md', placeholder: '以斜杠（"/"）开始的字符串，标识提供给客户端的URL路径' },
                    { kind: 'input', key: ['local_dir'], label: '本地文件夹路径', w: 'xl', placeholder: '本地文件夹路径，建议相对路径，最好是项目内部的路径' },
                  ],
                ],
              },
            ],
          ],
        },
        {
          id: 'theme',
          title: 'CSS',
          desc: '主题选择。v3 会实时换主题色（保存后写进配置；主题的完整渐变样式仍以重启后的效果为准）。',
          rows: [
            [
              { kind: 'select', key: ['webui', 'theme', 'choose'], label: '主题', w: 'md', options: {}, dynamicOptions: 'theme-list', keepUnknown: true },
            ],
          ],
        },
        {
          id: 'config-template',
          title: '配置模板',
          desc: '把当前 config.json 存成模板，或用模板覆盖当前 config.json。',
          rows: [
            [
              { kind: 'transient-input', key: ['_t', 'path'], label: '配置模板路径', w: 'md', placeholder: '先「列出模板」再选，或直接手输 *.json 路径' },
              { kind: 'action', key: ['_a', 'list'], label: '列出模板', w: 'sm', action: 'config-templates', hint: '列出项目根目录下的 *.json，填进左边的输入框' },
            ],
            [
              { kind: 'action', key: ['_a', 'save'], label: '保存当前配置到模板', w: 'md', action: 'config-template-save', params: { path: '$transient:path' }, hint: '存的是配置文件当前内容——界面上的未保存改动不含在内，先点「保存配置」' },
              { kind: 'action', key: ['_a', 'load'], label: '读取模板覆盖当前配置（慎点）', w: 'md', action: 'config-template-load', params: { path: '$transient:path' }, confirm: '这一步直接把模板写进 config.json，不经过「保存配置」，写完要重启 webui 才生效，也没法撤销。确认继续？' },
            ],
          ],
        },
        {
          id: 'section-toggles',
          title: '板块显示/隐藏',
          custom: 'section-toggles',
          desc: '关掉某块，它就会从对应工作区里移除（v3 与 v2 共用这份开关）。',
        },
        {
          id: 'login',
          title: '账号管理',
          desc: '登录功能由 v2 WebUI 实现（UMS 账号体系）；这里先能改配置开关，v3 的登录页在后续版本补上。',
          rows: [
            [
              { kind: 'switch', key: ['login', 'enable'], label: '登录功能' },
              { kind: 'input', key: ['login', 'username'], label: '用户名', w: 'md', placeholder: '您的账号，配置在config.json中' },
              { kind: 'input', key: ['login', 'password'], label: '密码', w: 'md', password: true, placeholder: '您的密码，配置在config.json中' },
              { kind: 'input', key: ['login', 'ums_api'], label: 'UMS接口地址', w: 'md' },
            ],
          ],
        },
      ],
    },
    {
      title: '文档与关于',
      sections: [
        // 文档资源 + 关于信息（版本/许可/仓库）都由 docs 自定义组件渲染
        { id: 'docs', title: '文档与关于', custom: 'docs' },
      ],
    },
  ],
}
