/** 弹幕管家工作区：触发规则 / 过滤屏蔽 / 念弹幕与答谢 / 播报顺序 四页签。

 * 字段与 config 键逐项对齐 v2 common_config.py（念弹幕/答谢）与 interact_filter.py；
 * 原先一张巨型「过滤」卡按任务拆成了页签，config 键不变。
 */
import type { Field, Workspace } from '../types'

const PERIODIC_TRIGGER_HINT = '每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成'
const TRIGGER_NUM_HINT = '周期到后，会触发n次此功能，次数从最大最小值之间随机生成'

/** 周期性触发，念弹幕/本地问答/答谢三处重复出现：
 * 开关 + 频率复合控件（周期 min/max 秒 · 次数 min/max 一行编辑）。 */
function periodic(prefix: (string | number)[]): Field[] {
  return [
    { kind: 'switch', key: [...prefix, 'enable'], label: '周期性触发启用' },
    { kind: 'frequency', key: prefix, label: '触发频率', w: 'xl', hint: `${PERIODIC_TRIGGER_HINT}；${TRIGGER_NUM_HINT}` },
  ]
}

/** 消息历史清理一对字段（间隔秒 + 保留条数）。 */
function forget(kind: string, label: string): Field[] {
  return [
    { kind: 'number', key: ['filter', `${kind}_forget_duration`], label: `${label}清理间隔（秒）`, w: 'sm', placeholder: '例：1', hint: '每隔多少秒丢一次这段时间内收到的旧消息；留在内存里的条数看旁边的「保留条数」' },
    { kind: 'number', key: ['filter', `${kind}_forget_reserve_num`], label: `${label}保留条数`, w: 'sm', int: true, placeholder: '保留最新收到的数据的数量' },
  ]
}

/** 板块开关：整块「过滤」被关掉时四个页签里的过滤内容一起隐藏。 */
const FILTER_CARD: [page: string, key: string] = ['common_config', 'filter']

export const danmuWorkspace: Workspace = {
  id: 'mod',
  title: '弹幕管家',
  tabbed: true,
  groups: [
    {
      title: '触发规则',
      sections: [
        {
          id: 'filter-trigger',
          title: '触发前后缀',
          showCard: FILTER_CARD,
          desc: '不设任何前后缀 = 所有弹幕都进大脑，新手建议全空；弹幕太吵时再设置触发词。',
          rows: [
            [
              { kind: 'string-list', key: ['filter', 'before_must_str'], label: '弹幕触发前缀', w: 'md', placeholder: '前缀必须携带其中任一字符串才能触发\n例如：配置#，那么这个会触发：#你好' },
              { kind: 'string-list', key: ['filter', 'after_must_str'], label: '弹幕触发后缀', w: 'md', placeholder: '后缀必须携带其中任一字符串才能触发\n例如：配置。那么这个会触发：你好。' },
              { kind: 'string-list', key: ['filter', 'before_must_str_for_llm'], label: 'LLM触发前缀', w: 'md', placeholder: '前缀必须携带其中任一字符串才能触发LLM\n例如：配置#，那么这个会触发：#你好' },
              { kind: 'string-list', key: ['filter', 'after_must_str_for_llm'], label: 'LLM触发后缀', w: 'md', placeholder: '后缀必须携带其中任一字符串才能触发LLM\n例如：配置。那么这个会触发：你好。' },
              { kind: 'string-list', key: ['filter', 'before_filter_str'], label: '弹幕过滤前缀', w: 'md', placeholder: '当前缀为其中任一字符串时，弹幕会被过滤\n例如：配置#，那么这个会被过滤：#你好' },
              { kind: 'string-list', key: ['filter', 'after_filter_str'], label: '弹幕过滤后缀', w: 'md', placeholder: '当后缀为其中任一字符串时，弹幕会被过滤\n例如：配置#，那么这个会被过滤：你好#' },
            ],
          ],
        },
      ],
    },
    {
      title: '过滤屏蔽',
      sections: [
        {
          id: 'filter-block',
          title: '屏蔽规则',
          showCard: FILTER_CARD,
          desc: '违禁词、黑名单与长度限制：不让脏东西和杠精进直播间。',
          rows: [
            [
              { kind: 'switch', key: ['filter', 'badwords', 'enable'], label: '违禁词过滤' },
              { kind: 'switch', key: ['filter', 'badwords', 'discard'], label: '违禁语句丢弃' },
              { kind: 'input', key: ['filter', 'badwords', 'path'], label: '违禁词路径', w: 'md', placeholder: '本地违禁词数据路径（你如果不需要，可以清空文件内容）' },
              { kind: 'input', key: ['filter', 'badwords', 'bad_pinyin_path'], label: '违禁拼音路径', w: 'md', placeholder: '本地违禁拼音数据路径（你如果不需要，可以清空文件内容）' },
              { kind: 'input', key: ['filter', 'badwords', 'replace'], label: '违禁词替换', w: 'md', placeholder: '在不丢弃违禁语句的前提下，将违禁词替换成此项的文本' },
            ],
            [
              { kind: 'number', key: ['filter', 'max_len'], label: '最大单词数', w: 'sm', int: true, placeholder: '最长阅读的英文单词数（空格分隔）' },
              { kind: 'number', key: ['filter', 'max_char_len'], label: '最大字符数', w: 'sm', int: true, placeholder: '最长阅读的字符数，双重过滤，避免溢出' },
              { kind: 'switch', key: ['filter', 'username_convert_digits_to_chinese'], label: '用户名中的数字转中文' },
              { kind: 'switch', key: ['filter', 'emoji'], label: '弹幕表情过滤' },
            ],
          ],
          cards: [
            {
              id: 'filter-blacklist',
              title: '弹幕黑名单',
              rows: [
                [
                  { kind: 'switch', key: ['filter', 'blacklist', 'enable'], label: '启用' },
                  { kind: 'string-list', key: ['filter', 'blacklist', 'username'], label: '用户名 黑名单', w: 'xl', placeholder: '屏蔽此名单内所有用户的弹幕，用户名以换行分隔' },
                ],
              ],
            },
            {
              id: 'filter-dedup',
              title: '限定时间段内数据重复丢弃',
              rows: [
                [
                  { kind: 'switch', key: ['filter', 'limited_time_deduplication', 'enable'], label: '启用' },
                  { kind: 'number', key: ['filter', 'limited_time_deduplication', 'comment'], label: '弹幕检测周期', w: 'sm', int: true, placeholder: '在这个周期时间（秒）内，重复的数据将被丢弃' },
                  { kind: 'number', key: ['filter', 'limited_time_deduplication', 'gift'], label: '礼物检测周期', w: 'sm', int: true, placeholder: '在这个周期时间（秒）内，重复的数据将被丢弃' },
                  { kind: 'number', key: ['filter', 'limited_time_deduplication', 'entrance'], label: '入场检测周期', w: 'sm', int: true, placeholder: '在这个周期时间（秒）内，重复的数据将被丢弃' },
                ],
              ],
            },
            {
              id: 'filter-forget',
              title: '消息历史清理设置',
              desc: '程序会把收到的弹幕/礼物等留在内存里。清理间隔是每隔多少秒丢一次这段时间内收到的旧消息，保留条数是每次清理之后仍留在内存里的最新条数。两类都只影响内存，不动数据库文件。',
              rows: [
                forget('comment', '弹幕'),
                forget('gift', '礼物'),
                forget('entrance', '入场'),
                forget('follow', '关注'),
                forget('talk', '聊天'),
                forget('schedule', '定时'),
                forget('idle_time_task', '闲时任务'),
                forget('image_recognition_schedule', '图像识别'),
              ],
            },
          ],
        },
      ],
    },
    {
      title: '念弹幕与答谢',
      sections: [
        {
          id: 'read-comment',
          title: '念弹幕',
          showCard: ['common_config', 'read_comment'],
          desc: '弹幕播报策略：过滤、排序、频率控制与回复逻辑，避免弹幕刷屏或遗漏关键互动。',
          rows: [
            [
              { kind: 'switch', key: ['read_comment', 'enable'], label: '启用' },
              { kind: 'switch', key: ['read_comment', 'read_username_enable'], label: '念用户名' },
              { kind: 'number', key: ['read_comment', 'username_max_len'], label: '用户名最大长度', w: 'sm', int: true, placeholder: '需要保留的用户名的最大长度，超出部分将被丢弃' },
              { kind: 'switch', key: ['read_comment', 'voice_change'], label: '变声' },
            ],
            [
              { kind: 'string-list', key: ['read_comment', 'read_username_copywriting'], label: '念用户名文案', w: 'lg', placeholder: '念用户名时使用的文案，可以自定义编辑多个（换行分隔），实际中会随机一个使用' },
            ],
            periodic(['read_comment', 'periodic_trigger']),
          ],
        },
        {
          id: 'thanks',
          title: '答谢',
          showCard: ['common_config', 'thanks'],
          desc: '入场欢迎、礼物赠送、关注感谢的自动语音播报与文案轮播系统。',
          rows: [
            [{ kind: 'number', key: ['thanks', 'username_max_len'], label: '用户名最大长度', w: 'sm', int: true, placeholder: '需要保留的用户名的最大长度，超出部分将被丢弃' }],
          ],
          cards: [
            {
              id: 'thanks-entrance',
              title: '入场设置',
              rows: [
                [
                  { kind: 'switch', key: ['thanks', 'entrance_enable'], label: '启用入场欢迎' },
                  { kind: 'switch', key: ['thanks', 'entrance_random'], label: '随机选取' },
                  { kind: 'string-list', key: ['thanks', 'entrance_copy'], label: '入场文案', w: 'lg', placeholder: '用户进入直播间的相关文案，请勿动 {username}，此字符串用于替换用户名' },
                ],
                periodic(['thanks', 'entrance', 'periodic_trigger']),
              ],
            },
            {
              id: 'thanks-gift',
              title: '礼物设置',
              rows: [
                [
                  { kind: 'switch', key: ['thanks', 'gift_enable'], label: '启用礼物答谢' },
                  { kind: 'switch', key: ['thanks', 'gift_random'], label: '随机选取' },
                  { kind: 'string-list', key: ['thanks', 'gift_copy'], label: '礼物文案', w: 'lg', placeholder: '用户赠送礼物的相关文案，请勿动 {username} 和 {gift_name}，此字符串用于替换用户名和礼物名' },
                  { kind: 'number', key: ['thanks', 'lowest_price'], label: '最低答谢礼物价格', w: 'sm', int: true, placeholder: '设置最低答谢礼物的价格（元），低于这个设置的礼物不会触发答谢' },
                ],
                periodic(['thanks', 'gift', 'periodic_trigger']),
              ],
            },
            {
              id: 'thanks-follow',
              title: '关注设置',
              rows: [
                [
                  { kind: 'switch', key: ['thanks', 'follow_enable'], label: '启用关注答谢' },
                  { kind: 'switch', key: ['thanks', 'follow_random'], label: '随机选取' },
                  { kind: 'string-list', key: ['thanks', 'follow_copy'], label: '关注文案', w: 'lg', placeholder: '用户关注时的相关文案，请勿动 {username}，此字符串用于替换用户名' },
                ],
                periodic(['thanks', 'follow', 'periodic_trigger']),
              ],
            },
          ],
        },
      ],
    },
    {
      title: '播报顺序',
      sections: [
        {
          id: 'filter-priority',
          title: '播报优先级',
          custom: 'priority-list',
          showCard: FILTER_CARD,
          desc: '消息排队时谁先合成先播放。拖拽排序，越靠上越优先（数据对应 filter.priority_mapping）。',
        },
        {
          id: 'filter-queue',
          title: '消息与音频队列',
          showCard: FILTER_CARD,
          desc: '队列长度按文本切分后计算，回复内容过长时可能丢数据。',
          rows: [
            [
              { kind: 'number', key: ['filter', 'message_queue_max_len'], label: '消息队列最大保留长度', w: 'md', int: true, hint: '收到的消息生成的文本会按优先级存入消息队列，当新消息优先级低于队列中所有消息且超过此长度时会被丢弃' },
              { kind: 'number', key: ['filter', 'voice_tmp_path_queue_max_len'], label: '音频播放队列最大保留长度', w: 'md', int: true, hint: '合成后的音频按优先级存入待播放队列，当新音频优先级低于队列所有音频且超过此长度时会被丢弃' },
              { kind: 'number', key: ['filter', 'voice_tmp_path_queue_min_start_play'], label: '音频播放队列首次触发播放阈值', w: 'md', int: true, hint: '缓存一定数量的音频后再开始播放；不想开播前缓冲就配 0' },
            ],
          ],
        },
      ],
    },
  ],
}
