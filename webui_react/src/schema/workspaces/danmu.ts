/** 弹幕与礼仪工作区：念弹幕、答谢（入场/礼物/关注）、过滤。

 * 字段与 config 键逐项对齐 v2 common_config.py（念弹幕/答谢）与 interact_filter.py。
 */
import type { Field, Workspace } from '../types'

const PERIODIC_TRIGGER_HINT = '每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成'
const TRIGGER_NUM_HINT = '周期到后，会触发n次此功能，次数从最大最小值之间随机生成'

/** 周期性触发四件套，念弹幕/本地问答/答谢三处重复出现。 */
function periodic(prefix: (string | number)[]): Field[] {
  return [
    { kind: 'switch', key: [...prefix, 'enable'], label: '周期性触发启用' },
    { kind: 'number', key: [...prefix, 'periodic_time_min'], label: '触发周期最小值', w: 'sm', int: true, placeholder: '例如：5', hint: PERIODIC_TRIGGER_HINT },
    { kind: 'number', key: [...prefix, 'periodic_time_max'], label: '触发周期最大值', w: 'sm', int: true, placeholder: '例如：10' },
    { kind: 'number', key: [...prefix, 'trigger_num_min'], label: '触发次数最小值', w: 'sm', int: true, placeholder: '例如：0', hint: TRIGGER_NUM_HINT },
    { kind: 'number', key: [...prefix, 'trigger_num_max'], label: '触发次数最大值', w: 'sm', int: true, placeholder: '例如：1' },
  ]
}

/** 消息历史清理一对字段（间隔秒 + 保留条数）。 */
function forget(kind: string, label: string): Field[] {
  return [
    { kind: 'number', key: ['filter', `${kind}_forget_duration`], label: `${label}清理间隔（秒）`, w: 'sm', placeholder: '例：1', hint: '每隔多少秒丢一次这段时间内收到的旧消息；留在内存里的条数看旁边的「保留条数」' },
    { kind: 'number', key: ['filter', `${kind}_forget_reserve_num`], label: `${label}保留条数`, w: 'sm', int: true, placeholder: '保留最新收到的数据的数量' },
  ]
}

function priority(label: string, key: string): Field {
  return { kind: 'number', key: ['filter', 'priority_mapping', key], label: `${label} 优先级`, w: 'sm', int: true, placeholder: '数字越大，优先级越高' }
}

export const danmuWorkspace: Workspace = {
  id: 'danmu',
  title: '弹幕与礼仪',
  groups: [
    {
      title: '安全风控',
      sections: [
        {
          id: 'filter',
          title: '过滤',
          showCard: ['common_config', 'filter'],
          desc: '弹幕触发/过滤前后缀、违禁词、消息历史清理、队列优先级与黑名单。这块被「板块显示/隐藏」关掉时，本组会整体隐藏。',
          rows: [
            [
              { kind: 'string-list', key: ['filter', 'before_must_str'], label: '弹幕触发前缀', w: 'md', placeholder: '前缀必须携带其中任一字符串才能触发\n例如：配置#，那么这个会触发：#你好' },
              { kind: 'string-list', key: ['filter', 'after_must_str'], label: '弹幕触发后缀', w: 'md', placeholder: '后缀必须携带其中任一字符串才能触发\n例如：配置。那么这个会触发：你好。' },
              { kind: 'string-list', key: ['filter', 'before_filter_str'], label: '弹幕过滤前缀', w: 'md', placeholder: '当前缀为其中任一字符串时，弹幕会被过滤\n例如：配置#，那么这个会被过滤：#你好' },
              { kind: 'string-list', key: ['filter', 'after_filter_str'], label: '弹幕过滤后缀', w: 'md', placeholder: '当后缀为其中任一字符串时，弹幕会被过滤\n例如：配置#，那么这个会被过滤：你好#' },
              { kind: 'string-list', key: ['filter', 'before_must_str_for_llm'], label: 'LLM触发前缀', w: 'md', placeholder: '前缀必须携带其中任一字符串才能触发LLM\n例如：配置#，那么这个会触发：#你好' },
              { kind: 'string-list', key: ['filter', 'after_must_str_for_llm'], label: 'LLM触发后缀', w: 'md', placeholder: '后缀必须携带其中任一字符串才能触发LLM\n例如：配置。那么这个会触发：你好。' },
            ],
            [
              { kind: 'number', key: ['filter', 'max_len'], label: '最大单词数', w: 'sm', int: true, placeholder: '最长阅读的英文单词数（空格分隔）' },
              { kind: 'number', key: ['filter', 'max_char_len'], label: '最大字符数', w: 'sm', int: true, placeholder: '最长阅读的字符数，双重过滤，避免溢出' },
              { kind: 'switch', key: ['filter', 'username_convert_digits_to_chinese'], label: '用户名中的数字转中文' },
              { kind: 'switch', key: ['filter', 'emoji'], label: '弹幕表情过滤' },
            ],
            [
              { kind: 'switch', key: ['filter', 'badwords', 'enable'], label: '违禁词过滤' },
              { kind: 'switch', key: ['filter', 'badwords', 'discard'], label: '违禁语句丢弃' },
              { kind: 'input', key: ['filter', 'badwords', 'path'], label: '违禁词路径', w: 'md', placeholder: '本地违禁词数据路径（你如果不需要，可以清空文件内容）' },
              { kind: 'input', key: ['filter', 'badwords', 'bad_pinyin_path'], label: '违禁拼音路径', w: 'md', placeholder: '本地违禁拼音数据路径（你如果不需要，可以清空文件内容）' },
              { kind: 'input', key: ['filter', 'badwords', 'replace'], label: '违禁词替换', w: 'md', placeholder: '在不丢弃违禁语句的前提下，将违禁词替换成此项的文本' },
            ],
          ],
          cards: [
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
              id: 'filter-queue',
              title: '待合成音频的消息&待播放音频队列',
              desc: '下方优先级配置请使用正整数，数字越大优先级越高，会优先合成播放。注意：目前队列长度按文本切分后计算，回复内容过长时可能丢数据。',
              rows: [
                [
                  { kind: 'number', key: ['filter', 'message_queue_max_len'], label: '消息队列最大保留长度', w: 'md', int: true, hint: '收到的消息生成的文本会按优先级存入消息队列，当新消息优先级低于队列中所有消息且超过此长度时会被丢弃' },
                  { kind: 'number', key: ['filter', 'voice_tmp_path_queue_max_len'], label: '音频播放队列最大保留长度', w: 'md', int: true, hint: '合成后的音频按优先级存入待播放队列，当新音频优先级低于队列所有音频且超过此长度时会被丢弃' },
                  { kind: 'number', key: ['filter', 'voice_tmp_path_queue_min_start_play'], label: '音频播放队列首次触发播放阈值', w: 'md', int: true, hint: '缓存一定数量的音频后再开始播放；不想开播前缓冲就配 0' },
                ],
                [
                  priority('闲时任务', 'idle_time_task'),
                  priority('图像识别', 'image_recognition_schedule'),
                  priority('本地问答-音频', 'local_qa_audio'),
                  priority('弹幕回复', 'comment'),
                  priority('文案', 'copywriting'),
                ],
                [
                  priority('点歌', 'song'),
                  priority('念弹幕', 'read_comment'),
                  priority('入场欢迎', 'entrance'),
                  priority('礼物答谢', 'gift'),
                  priority('关注答谢', 'follow'),
                ],
                [
                  priority('聊天（语音输入）', 'talk'),
                  priority('复读', 'reread'),
                  priority('按键映射', 'key_mapping'),
                  priority('积分', 'integral'),
                  priority('最高优先级复读', 'reread_top_priority'),
                ],
                [
                  priority('异常报警', 'abnormal_alarm'),
                  priority('动态文案', 'trends_copywriting'),
                  priority('定时任务', 'schedule'),
                  priority('助播-文本', 'assistant_anchor_text'),
                  priority('助播-音频', 'assistant_anchor_audio'),
                ],
              ],
            },
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
          ],
        },
      ],
    },
    {
      title: '弹幕响应',
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
  ],
}
