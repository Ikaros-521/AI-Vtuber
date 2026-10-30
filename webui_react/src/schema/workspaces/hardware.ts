/** 玩法库区块 · 进阶联动部分（原「外设与联动」工作区）。

 * 字段与 config 键逐项对齐 v2 common_config.py（按键映射/洛曦/自定义命令/联动程序）与 serial.py。
 */
import type { Section } from '../types'

const TRIGGER_TYPE_OPTIONS = { 不启用: '不启用', 关键词: '关键词', 礼物: '礼物', '关键词+礼物': '关键词+礼物' }

/** 「单句仅触发一次」类开关的统一提示 */
const ONCE_HINT = '一句话的数据是否只触发一次对应映射（一句话中可能有多个关键词，触发多次）'

export const keyMappingSection: Section = {
  id: 'key-mapping',
  title: '按键联动',
  icon: 'plug',
  masterKey: ['key_mapping', 'enable'],
  showCard: ['common_config', 'key_mapping'],
  desc: '弹幕指令与外部联动：观众发送特定弹幕时，自动触发键盘按键、本地音效、串口硬件或图片弹窗。',
  rows: [
    [
      { kind: 'switch', key: ['key_mapping', 'enable'], label: '启用' },
      { kind: 'input', key: ['key_mapping', 'start_cmd'], label: '命令前缀', w: 'md', hint: '想要触发此功能必须以这个字符串做为命令起始，不然将不会被解析为按键映射命令' },
      { kind: 'select', key: ['key_mapping', 'type'], label: '捕获类型', w: 'sm', options: { 弹幕: '弹幕', 回复: '回复', '弹幕+回复': '弹幕+回复' }, hint: '什么类型的数据会触发这个板块的功能' },
    ],
    [
      {
        kind: 'group-list',
        key: ['key_mapping', 'config'],
        label: '映射配置组',
        w: 'xl',
        itemTitle: '映射',
        addLabel: '增加映射组',
        itemDefaults: { keywords: [], gift: [], keys: [], similarity: 1, copywriting: [], local_audio: [], serial_name: '', serial_send_data: [], img_path: [] },
        rows: [
          [
            { kind: 'string-list', key: ['keywords'], label: '关键词', w: 'sm', placeholder: '触发的关键词，多个换行分隔' },
            { kind: 'string-list', key: ['gift'], label: '礼物', w: 'sm', placeholder: '触发的礼物名，多个换行分隔' },
            { kind: 'string-list', key: ['keys'], label: '按键', w: 'sm', placeholder: '要映射的按键，多个换行分隔（按键名参考pyautogui规则）' },
            { kind: 'number', key: ['similarity'], label: '相似度', w: 'xs', placeholder: '默认1即100%' },
          ],
          [
            { kind: 'string-list', key: ['copywriting'], label: '文案', w: 'md', placeholder: '触发后合成的文案内容，多个换行分隔' },
            { kind: 'string-list', key: ['local_audio'], label: '本地音频', w: 'md', placeholder: '触发后播放的本地音频路径，多个换行分隔' },
          ],
          [
            { kind: 'input', key: ['serial_name'], label: '串口名', w: 'sm', placeholder: '串口页配置的串口名，例如：COM1' },
            { kind: 'string-list', key: ['serial_send_data'], label: '串口发送内容', w: 'md', placeholder: '多个换行分隔，ASCII例如：open led\nHEX例如：313233' },
            { kind: 'string-list', key: ['img_path'], label: '图片路径', w: 'md', placeholder: '多个换行分隔，支持绝对/相对路径，默认随机显示' },
          ],
        ],
      },
    ],
  ],
  rowsAdvanced: [
    [
      { kind: 'select', key: ['key_mapping', 'key_trigger_type'], label: '按键触发类型', w: 'sm', options: TRIGGER_TYPE_OPTIONS },
      { kind: 'switch', key: ['key_mapping', 'key_single_sentence_trigger_once'], label: '单句仅触发一次（按键）', hint: ONCE_HINT },
      { kind: 'select', key: ['key_mapping', 'copywriting_trigger_type'], label: '文案触发类型', w: 'sm', options: TRIGGER_TYPE_OPTIONS },
      { kind: 'switch', key: ['key_mapping', 'copywriting_single_sentence_trigger_once'], label: '单句仅触发一次（文案）', hint: ONCE_HINT },
    ],
    [
      { kind: 'select', key: ['key_mapping', 'local_audio_trigger_type'], label: '本地音频触发类型', w: 'sm', options: TRIGGER_TYPE_OPTIONS },
      { kind: 'switch', key: ['key_mapping', 'local_audio_single_sentence_trigger_once'], label: '单句仅触发一次（本地音频）', hint: ONCE_HINT },
      { kind: 'select', key: ['key_mapping', 'serial_trigger_type'], label: '串口触发类型', w: 'sm', options: TRIGGER_TYPE_OPTIONS },
      { kind: 'switch', key: ['key_mapping', 'serial_single_sentence_trigger_once'], label: '单句仅触发一次（串口）', hint: ONCE_HINT },
    ],
    [
      { kind: 'select', key: ['key_mapping', 'img_path_trigger_type'], label: '图片触发类型', w: 'sm', options: TRIGGER_TYPE_OPTIONS },
      { kind: 'switch', key: ['key_mapping', 'img_path_single_sentence_trigger_once'], label: '单句仅触发一次（图片显示）', hint: ONCE_HINT },
    ],
  ],
}

export const customCmdSection: Section = {
  id: 'custom-cmd',
  title: '自定义命令',
  icon: 'puzzle',
  masterKey: ['custom_cmd', 'enable'],
  showCard: ['common_config', 'custom_cmd'],
  desc: '弹幕高级指令匹配：通过关键词触发自定义外部 HTTP 接口，把返回内容合成播报。',
  rows: [
    [
      { kind: 'switch', key: ['custom_cmd', 'enable'], label: '启用' },
      { kind: 'select', key: ['custom_cmd', 'type'], label: '类型', w: 'sm', options: { 弹幕: '弹幕' } },
    ],
    [
      {
        kind: 'group-list',
        key: ['custom_cmd', 'config'],
        label: '命令配置组',
        w: 'xl',
        itemTitle: '命令',
        addLabel: '增加命令组',
        itemDefaults: { keywords: [], similarity: 1, api_url: '', api_type: 'GET', resp_data_type: 'json', data_analysis: '', resp_template: '' },
        rows: [
          [
            { kind: 'string-list', key: ['keywords'], label: '关键词', w: 'md', placeholder: '触发的关键词，多个换行分隔' },
            { kind: 'number', key: ['similarity'], label: '相似度', w: 'xs', placeholder: '默认1即100%' },
            { kind: 'input', key: ['api_url'], label: 'API URL', w: 'md', placeholder: '发送HTTP请求的API链接' },
          ],
          [
            { kind: 'select', key: ['api_type'], label: 'API类型', w: 'xs', options: { GET: 'GET' } },
            { kind: 'select', key: ['resp_data_type'], label: '请求返回数据类型', w: 'sm', options: { json: 'json', content: 'content' } },
            { kind: 'textarea', key: ['data_analysis'], label: '数据解析（eval执行）', w: 'md', placeholder: '请不要随意修改resp变量' },
            { kind: 'textarea', key: ['resp_template'], label: '返回内容模板', w: 'md', placeholder: '请不要随意删除data变量，支持动态变量' },
          ],
        ],
      },
    ],
  ],
}

export const luoxiSection: Section = {
  id: 'luoxi',
  title: '洛曦弹幕助手',
  icon: 'radio',
  masterKey: ['luoxi_project', 'Live_Comment_Assistant', 'enable'],
  desc: '对接第三方「洛曦 直播弹幕助手」软件，扩展支持更多平台的弹幕数据监听。',
  rows: [
    [
      { kind: 'switch', key: ['luoxi_project', 'Live_Comment_Assistant', 'enable'], label: '启用' },
      { kind: 'select', key: ['luoxi_project', 'Live_Comment_Assistant', 'version'], label: '对接版本', w: 'xs', options: { 'V0.1.x': 'V0.1.x' }, hint: '因为不同版本可能会有接口上的改动' },
      { kind: 'input', key: ['luoxi_project', 'Live_Comment_Assistant', 'api_ip_port'], label: 'API地址', w: 'md', placeholder: '洛曦 直播弹幕助手 API地址' },
    ],
  ],
  cards: [
    {
      id: 'luoxi-types',
      title: '触发类型',
      rows: [
        [
          {
            kind: 'checkboxes',
            key: ['luoxi_project', 'Live_Comment_Assistant', 'type'],
            label: '推送给助手的消息类型',
            w: 'xl',
            options: {
              comment: '弹幕消息', comment_reply: '弹幕回复', idle_time_task: '闲时任务',
              entrance_reply: '入场回复', follow_reply: '关注回复', gift_reply: '礼物回复',
              reread: '复读', schedule: '定时任务', integral: '积分消息', key_mapping_copywriting: '按键映射-文案',
            },
          },
        ],
      ],
    },
    {
      id: 'luoxi-positions',
      title: '触发位置',
      rows: [
        [
          {
            kind: 'checkboxes',
            key: ['luoxi_project', 'Live_Comment_Assistant', 'trigger_position'],
            label: '消息推送时机',
            w: 'xl',
            options: { 消息产生时: '消息产生时', 音频播放时: '音频播放时' },
          },
        ],
      ],
    },
  ],
}

export const coordinationSection: Section = {
  id: 'coordination',
  title: '联动程序',
  icon: 'gear',
  showCard: ['common_config', 'coordination_program'],
  desc: '伴随进程生命周期管理：随 AI-Vtuber 启动/停止时自动唤起或终止绑定的第三方配套软件。每个程序自带启用开关。',
  rows: [
    [
      {
        kind: 'group-list',
        key: ['coordination_program'],
        label: '联动程序列表',
        w: 'xl',
        itemTitle: '程序',
        addLabel: '增加联动程序',
        itemDefaults: { enable: false, name: '', executable: '', parameters: [] },
        rows: [
          [
            { kind: 'switch', key: ['enable'], label: '启用' },
            { kind: 'input', key: ['name'], label: '程序名', w: 'md', placeholder: '给你的程序取个名字，别整特殊符号！' },
          ],
          [
            { kind: 'input', key: ['executable'], label: '可执行程序', w: 'xl', placeholder: '可执行程序的路径，最好是绝对路径，如python的程序' },
            { kind: 'string-list', key: ['parameters'], label: '参数', w: 'xl', placeholder: '参数，可以传入多个参数，换行分隔。如启动的程序的路径，命令携带的传参等' },
          ],
        ],
      },
    ],
  ],
}

export const serialSection: Section = {
  id: 'serial',
  title: '串口硬件',
  icon: 'chip',
  desc: '通过串口与 Arduino / ESP32 等单片机通信，联动控制物理指示灯、舵机机械臂或互动实体道具。配好后在「按键联动」里按串口名引用。',
  rows: [
    [
      {
        kind: 'group-list',
        key: ['serial', 'config'],
        label: '串口配置组',
        w: 'xl',
        itemTitle: '串口',
        addLabel: '增加串口配置组',
        itemDesc: '此页完成串口配置后，可以在「按键联动」里引用串口名。注意：此处连接测试完成后请点「关闭串口」——程序是跨进程使用串口的，不关掉会占用串口导致无法正常使用！',
        itemDefaults: { serial_name: 'COM1', baudrate: '115200', serial_data_type: 'ASCII' },
        rows: [
          [
            { kind: 'select', key: ['serial_name'], label: '串口名', w: 'md', free: true, options: {}, dynamicOptions: 'serial-ports' },
            { kind: 'action', key: ['_a', 'refresh'], label: '刷新串口', w: 'sm', action: 'serial-ports' },
            { kind: 'select', key: ['baudrate'], label: '波特率', w: 'sm', options: { 9600: '9600', 19200: '19200', 38400: '38400', 115200: '115200' } },
          ],
          [
            { kind: 'action', key: ['_a', 'connect'], label: '打开串口', w: 'sm', action: 'serial-connect', params: { serial_name: ['serial_name'], baudrate: ['baudrate'] } },
            { kind: 'action', key: ['_a', 'disconnect'], label: '关闭串口', w: 'sm', action: 'serial-disconnect', params: { serial_name: ['serial_name'] } },
            { kind: 'select', key: ['serial_data_type'], label: '发送数据类型', w: 'xs', options: { ASCII: 'ASCII', HEX: 'HEX' } },
            { kind: 'transient-input', key: ['_t', 'data'], label: '发送数据', w: 'md', placeholder: '填要发的内容，连接后点「发送」（不会存进配置）' },
            { kind: 'action', key: ['_a', 'send'], label: '发送', w: 'xs', action: 'serial-send', params: { serial_name: ['serial_name'], data: '$transient:data', data_type: ['serial_data_type'] } },
          ],
        ],
      },
    ],
  ],
}
