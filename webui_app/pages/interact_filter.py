"""互动 · 过滤页：违禁词、触发前后缀、消息历史清理、队列优先级、黑名单。

从 通用配置 拆出来的第一个页面。控件变量名与原来完全一致，方便和 git diff 对照；
「板块显示/隐藏」里关掉 过滤 时不再静默空白，而是说明去哪儿打开。
"""
from nicegui import ui

from webui_app.helpers import textarea_data_change
from webui_app.descriptions import show_card_desc
from webui_app.pages import PageConfig


def build_interact_filter_tab(config, card_css, switch_internal_css):
    if not config.get("webui", "show_card", "common_config", "filter"):
        with ui.card().style(card_css):
            ui.label('过滤板块已被隐藏')
            ui.label('页面配置 › 板块显示/隐藏 › 过滤 里勾上才会显示这些配置项。')
        return PageConfig()

    with ui.card().style(card_css):
        ui.label('过滤')    
        show_card_desc('过滤')
        with ui.grid(columns=6):
            textarea_filter_before_must_str = ui.textarea(label='弹幕触发前缀', placeholder='前缀必须携带其中任一字符串才能触发\n例如：配置#，那么这个会触发：#你好', value=textarea_data_change(config.get("filter", "before_must_str"))).style("width:200px;").tooltip("前缀必须携带其中任一字符串才能触发\n例如：配置#，那么这个会触发：#你好")
            textarea_filter_after_must_str = ui.textarea(label='弹幕触发后缀', placeholder='后缀必须携带其中任一字符串才能触发\n例如：配置。那么这个会触发：你好。', value=textarea_data_change(config.get("filter", "before_must_str"))).style("width:200px;").tooltip("后缀必须携带其中任一字符串才能触发\n例如：配置。那么这个会触发：你好。")
            textarea_filter_before_filter_str = ui.textarea(label='弹幕过滤前缀', placeholder='当前缀为其中任一字符串时，弹幕会被过滤\n例如：配置#，那么这个会被过滤：#你好', value=textarea_data_change(config.get("filter", "before_filter_str"))).style("width:200px;").tooltip("当前缀为其中任一字符串时，弹幕会被过滤\n例如：配置#，那么这个会被过滤：#你好")
            textarea_filter_after_filter_str = ui.textarea(label='弹幕过滤后缀', placeholder='当后缀为其中任一字符串时，弹幕会被过滤\n例如：配置#，那么这个会被过滤：你好#', value=textarea_data_change(config.get("filter", "before_filter_str"))).style("width:200px;").tooltip("当后缀为其中任一字符串时，弹幕会被过滤\n例如：配置#，那么这个会被过滤：你好#")
            textarea_filter_before_must_str_for_llm = ui.textarea(label='LLM触发前缀', placeholder='前缀必须携带其中任一字符串才能触发LLM\n例如：配置#，那么这个会触发：#你好', value=textarea_data_change(config.get("filter", "before_must_str_for_llm"))).style("width:200px;").tooltip("前缀必须携带其中任一字符串才能触发LLM\n例如：配置#，那么这个会触发：#你好")
            textarea_filter_after_must_str_for_llm = ui.textarea(label='LLM触发后缀', placeholder='后缀必须携带其中任一字符串才能触发LLM\n例如：配置。那么这个会触发：你好。', value=textarea_data_change(config.get("filter", "before_must_str_for_llm"))).style("width:200px;").tooltip('后缀必须携带其中任一字符串才能触发LLM\n例如：配置。那么这个会触发：你好。')

        # 这块原先是 ui.row()：flex 排出来的位置跟上下两块栅格对不上，看着就是每行错位一点
        with ui.grid(columns=6):
            input_filter_max_len = ui.input(label='最大单词数', placeholder='最长阅读的英文单词数（空格分隔）', value=config.get("filter", "max_len")).style("width:150px;").tooltip('最长阅读的英文单词数（空格分隔）')
            input_filter_max_char_len = ui.input(label='最大字符数', placeholder='最长阅读的字符数，双重过滤，避免溢出', value=config.get("filter", "max_char_len")).style("width:150px;").tooltip('最长阅读的字符数，双重过滤，避免溢出')
            switch_filter_username_convert_digits_to_chinese = ui.switch('用户名中的数字转中文', value=config.get("filter", "username_convert_digits_to_chinese")).style(switch_internal_css).tooltip('用户名中的数字转中文')
            switch_filter_emoji = ui.switch('弹幕表情过滤', value=config.get("filter", "emoji")).style(switch_internal_css)
        # 与上面那 6 个弹幕触发/过滤前缀同列数，两块才能纵向对齐（走查 audit-12）
        with ui.grid(columns=6):
            switch_filter_badwords_enable = ui.switch('违禁词过滤', value=config.get("filter", "badwords", "enable")).style(switch_internal_css)
            switch_filter_badwords_discard = ui.switch('违禁语句丢弃', value=config.get("filter", "badwords", "discard")).style(switch_internal_css)
            input_filter_badwords_path = ui.input(label='违禁词路径', value=config.get("filter", "badwords", "path"), placeholder='本地违禁词数据路径（你如果不需要，可以清空文件内容）').style("width:200px;").tooltip('本地违禁词数据路径（你如果不需要，可以清空文件内容）')
            input_filter_badwords_bad_pinyin_path = ui.input(label='违禁拼音路径', value=config.get("filter", "badwords", "bad_pinyin_path"), placeholder='本地违禁拼音数据路径（你如果不需要，可以清空文件内容）').style("width:200px;").tooltip('本地违禁拼音数据路径（你如果不需要，可以清空文件内容）')
            input_filter_badwords_replace = ui.input(label='违禁词替换', value=config.get("filter", "badwords", "replace"), placeholder='在不丢弃违禁语句的前提下，将违禁词替换成此项的文本').style("width:200px;").tooltip('在不丢弃违禁语句的前提下，将违禁词替换成此项的文本')

        with ui.expansion('消息历史清理设置', icon="settings", value=True).classes('w-full'):
            with ui.element('div').classes('tip-bar'):
                ui.label("程序会把收到的弹幕/礼物等留在内存里。清理间隔 是每隔多少秒丢一次这段时间内收到的旧消息，"
                         "保留条数 是每次清理之后仍留在内存里的最新条数。两类都只影响内存，不动数据库文件。")
            with ui.grid(columns=4):
                input_filter_comment_forget_duration = ui.input(
                    label='弹幕清理间隔（秒）', 
                    placeholder='例：1', 
                    value=config.get("filter", "comment_forget_duration")
                ).style("width:200px;").tooltip('每隔多少秒丢一次这段时间内收到的旧消息；留在内存里的条数看旁边的「保留条数」')
                input_filter_comment_forget_reserve_num = ui.input(label='弹幕保留条数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "comment_forget_reserve_num")).style("width:200px;").tooltip('保留最新收到的数据的数量')
                input_filter_gift_forget_duration = ui.input(label='礼物清理间隔（秒）', placeholder='每隔多少秒丢一次这段时间内收到的旧消息；留在内存里的条数看旁边的「保留条数」', value=config.get("filter", "gift_forget_duration")).style("width:200px;").tooltip('每隔多少秒丢一次这段时间内收到的旧消息；留在内存里的条数看旁边的「保留条数」')
                input_filter_gift_forget_reserve_num = ui.input(label='礼物保留条数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "gift_forget_reserve_num")).style("width:200px;").tooltip('保留最新收到的数据的数量')
            with ui.grid(columns=4):
                input_filter_entrance_forget_duration = ui.input(label='入场清理间隔（秒）', placeholder='每隔多少秒丢一次这段时间内收到的旧消息；留在内存里的条数看旁边的「保留条数」', value=config.get("filter", "entrance_forget_duration")).style("width:200px;").tooltip('每隔多少秒丢一次这段时间内收到的旧消息；留在内存里的条数看旁边的「保留条数」')
                input_filter_entrance_forget_reserve_num = ui.input(label='入场保留条数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "entrance_forget_reserve_num")).style("width:200px;").tooltip('保留最新收到的数据的数量')
                input_filter_follow_forget_duration = ui.input(label='关注清理间隔（秒）', placeholder='每隔多少秒丢一次这段时间内收到的旧消息；留在内存里的条数看旁边的「保留条数」', value=config.get("filter", "follow_forget_duration")).style("width:200px;").tooltip('每隔多少秒丢一次这段时间内收到的旧消息；留在内存里的条数看旁边的「保留条数」')
                input_filter_follow_forget_reserve_num = ui.input(label='关注保留条数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "follow_forget_reserve_num")).style("width:200px;").tooltip('保留最新收到的数据的数量')
            with ui.grid(columns=4):
                input_filter_talk_forget_duration = ui.input(label='聊天清理间隔（秒）', placeholder='每隔多少秒丢一次这段时间内收到的旧消息；留在内存里的条数看旁边的「保留条数」', value=config.get("filter", "talk_forget_duration")).style("width:200px;").tooltip('每隔多少秒丢一次这段时间内收到的旧消息；留在内存里的条数看旁边的「保留条数」')
                input_filter_talk_forget_reserve_num = ui.input(label='聊天保留条数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "talk_forget_reserve_num")).style("width:200px;").tooltip('保留最新收到的数据的数量')
                input_filter_schedule_forget_duration = ui.input(label='定时清理间隔（秒）', placeholder='每隔多少秒丢一次这段时间内收到的旧消息；留在内存里的条数看旁边的「保留条数」', value=config.get("filter", "schedule_forget_duration")).style("width:200px;").tooltip('每隔多少秒丢一次这段时间内收到的旧消息；留在内存里的条数看旁边的「保留条数」')
                input_filter_schedule_forget_reserve_num = ui.input(label='定时保留条数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "schedule_forget_reserve_num")).style("width:200px;").tooltip('保留最新收到的数据的数量')
            with ui.grid(columns=4):
                input_filter_idle_time_task_forget_duration = ui.input(label='闲时任务清理间隔（秒）', placeholder='每隔多少秒丢一次这段时间内收到的旧消息；留在内存里的条数看旁边的「保留条数」', value=config.get("filter", "idle_time_task_forget_duration")).style("width:200px;").tooltip('每隔多少秒丢一次这段时间内收到的旧消息；留在内存里的条数看旁边的「保留条数」')
                input_filter_idle_time_task_forget_reserve_num = ui.input(label='闲时任务保留条数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "idle_time_task_forget_reserve_num")).style("width:200px;").tooltip('保留最新收到的数据的数量')
                input_filter_image_recognition_schedule_forget_duration = ui.input(label='图像识别清理间隔（秒）', placeholder='每隔多少秒丢一次这段时间内收到的旧消息；留在内存里的条数看旁边的「保留条数」', value=config.get("filter", "image_recognition_schedule_forget_duration")).style("width:200px;").tooltip('每隔多少秒丢一次这段时间内收到的旧消息；留在内存里的条数看旁边的「保留条数」')
                input_filter_image_recognition_schedule_forget_reserve_num = ui.input(label='图像识别保留条数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "image_recognition_schedule_forget_reserve_num")).style("width:200px;").tooltip('保留最新收到的数据的数量')
        with ui.expansion('限定时间段内数据重复丢弃', icon="settings", value=True).classes('w-full'):
            with ui.row():
                switch_filter_limited_time_deduplication_enable = ui.switch('启用', value=config.get("filter", "limited_time_deduplication", "enable")).style(switch_internal_css)
                input_filter_limited_time_deduplication_comment = ui.input(label='弹幕检测周期', value=config.get("filter", "limited_time_deduplication", "comment"), placeholder='在这个周期时间（秒）内，重复的数据将被丢弃').style("width:200px;").tooltip('在这个周期时间（秒）内，重复的数据将被丢弃')
                input_filter_limited_time_deduplication_gift = ui.input(label='礼物检测周期', value=config.get("filter", "limited_time_deduplication", "gift"), placeholder='在这个周期时间（秒）内，重复的数据将被丢弃').style("width:200px;").tooltip('在这个周期时间（秒）内，重复的数据将被丢弃')
                input_filter_limited_time_deduplication_entrance = ui.input(label='入场检测周期', value=config.get("filter", "limited_time_deduplication", "entrance"), placeholder='在这个周期时间（秒）内，重复的数据将被丢弃').style("width:200px;").tooltip('在这个周期时间（秒）内，重复的数据将被丢弃')

        with ui.expansion('待合成音频的消息&待播放音频队列', icon="settings", value=True).classes('w-full'):
            with ui.row():
                input_filter_message_queue_max_len = ui.input(label='消息队列最大保留长度', placeholder='收到的消息，生成的文本内容，会根据优先级存入消息队列，当新消息的优先级低于队列中所有的消息且超过此长度时，此消息将被丢弃', value=config.get("filter", "message_queue_max_len")).style("width:160px;").tooltip('收到的消息，生成的文本内容，会根据优先级存入消息队列，当新消息的优先级低于队列中所有的消息且超过此长度时，此消息将被丢弃')
                input_filter_voice_tmp_path_queue_max_len = ui.input(label='音频播放队列最大保留长度', placeholder='合成后的音频，会根据优先级存入待播放音频队列，当新音频的优先级低于队列中所有的音频且超过此长度时，此音频将被丢弃', value=config.get("filter", "voice_tmp_path_queue_max_len")).style("width:200px;").tooltip('合成后的音频，会根据优先级存入待播放音频队列，当新音频的优先级低于队列中所有的音频且超过此长度时，此音频将被丢弃')

                input_filter_voice_tmp_path_queue_min_start_play = ui.input(
                    label='音频播放队列首次触发播放阈值', 
                    placeholder='正整数 例如：20，如果你不想开播前缓冲一定数量的音频，请配置0', 
                    value=config.get("filter", "voice_tmp_path_queue_min_start_play")
                ).style("width:200px;").tooltip('此功能用于缓存一定数量的音频后再开始播放。如果你不想开播前缓冲一定数量的音频，请配置0；如果你想提前准备一些音频，如因为TTS合成慢的原因，可以配置此值，让TTS提前合成你的其他任务触发的内容')

                with ui.element('div').classes('tip-bar'):
                    ui.label("下方优先级配置，请使用正整数。数字越大，优先级越高，就会优先合成音频播放")
                    ui.label("另外需要注意，由于shi山原因，目前这个队列内容是文本切分后计算的长度，所以如果回复内容过长，可能会有丢数据的情况")
            with ui.grid(columns=5):
                input_filter_priority_mapping_idle_time_task = ui.input(label='闲时任务 优先级', value=config.get("filter", "priority_mapping", "idle_time_task"), placeholder='数字越大，优先级越高，但这个并非文本，所以暂时没啥用，预留').style("width:200px;").tooltip('数字越大，优先级越高')
                input_filter_priority_mapping_image_recognition_schedule = ui.input(label='图像识别 优先级', value=config.get("filter", "priority_mapping", "image_recognition_schedule"), placeholder='数字越大，优先级越高').style("width:200px;").tooltip('数字越大，优先级越高')
                input_filter_priority_mapping_local_qa_audio = ui.input(label='本地问答-音频 优先级', value=config.get("filter", "priority_mapping", "local_qa_audio"), placeholder='数字越大，优先级越高').style("width:200px;").tooltip('数字越大，优先级越高')
                input_filter_priority_mapping_comment = ui.input(label='弹幕回复 优先级', value=config.get("filter", "priority_mapping", "comment"), placeholder='数字越大，优先级越高').style("width:200px;").tooltip('数字越大，优先级越高')
                input_filter_priority_mapping_copywriting = ui.input(label='文案 优先级', value=config.get("filter", "priority_mapping", "copywriting"), placeholder='数字越大，优先级越高，文案页的文案，但这个并非文本，所以暂时没啥用，预留').style("width:200px;").tooltip('数字越大，优先级越高')

            with ui.grid(columns=5):
                input_filter_priority_mapping_song = ui.input(label='点歌 优先级', value=config.get("filter", "priority_mapping", "song"), placeholder='数字越大，优先级越高，但这个并非文本，所以暂时没啥用，预留').style("width:200px;").tooltip('数字越大，优先级越高')
                input_filter_priority_mapping_read_comment = ui.input(label='念弹幕 优先级', value=config.get("filter", "priority_mapping", "read_comment"), placeholder='数字越大，优先级越高').style("width:200px;").tooltip('数字越大，优先级越高')
                input_filter_priority_mapping_entrance = ui.input(label='入场欢迎 优先级', value=config.get("filter", "priority_mapping", "entrance"), placeholder='数字越大，优先级越高').style("width:200px;").tooltip('数字越大，优先级越高')
                input_filter_priority_mapping_gift = ui.input(label='礼物答谢 优先级', value=config.get("filter", "priority_mapping", "gift"), placeholder='数字越大，优先级越高').style("width:200px;").tooltip('数字越大，优先级越高')
                input_filter_priority_mapping_follow = ui.input(label='关注答谢 优先级', value=config.get("filter", "priority_mapping", "follow"), placeholder='数字越大，优先级越高').style("width:200px;").tooltip('数字越大，优先级越高')
            with ui.grid(columns=5):
                input_filter_priority_mapping_talk = ui.input(label='聊天（语音输入） 优先级', value=config.get("filter", "priority_mapping", "talk"), placeholder='数字越大，优先级越高，但这个并非文本，所以暂时没啥用，预留').style("width:200px;").tooltip('数字越大，优先级越高')
                input_filter_priority_mapping_reread = ui.input(label='复读 优先级', value=config.get("filter", "priority_mapping", "reread"), placeholder='数字越大，优先级越高，但这个并非文本，所以暂时没啥用，预留').style("width:200px;").tooltip('数字越大，优先级越高')
                input_filter_priority_mapping_key_mapping = ui.input(label='按键映射 优先级', value=config.get("filter", "priority_mapping", "key_mapping"), placeholder='数字越大，优先级越高').style("width:200px;").tooltip('数字越大，优先级越高')
                input_filter_priority_mapping_integral = ui.input(label='积分 优先级', value=config.get("filter", "priority_mapping", "integral"), placeholder='数字越大，优先级越高').style("width:200px;").tooltip('数字越大，优先级越高')
                input_filter_priority_mapping_reread_top_priority = ui.input(label='最高优先级复读 优先级', value=config.get("filter", "priority_mapping", "reread_top_priority"), placeholder='数字越大，优先级越高').style("width:200px;").tooltip('数字越大，优先级越高')

            with ui.grid(columns=5):
                input_filter_priority_mapping_abnormal_alarm = ui.input(label='异常报警 优先级', value=config.get("filter", "priority_mapping", "abnormal_alarm"), placeholder='数字越大，优先级越高').style("width:200px;").tooltip('数字越大，优先级越高')
                input_filter_priority_mapping_trends_copywriting = ui.input(label='动态文案 优先级', value=config.get("filter", "priority_mapping", "trends_copywriting"), placeholder='数字越大，优先级越高').style("width:200px;").tooltip('数字越大，优先级越高')
                input_filter_priority_mapping_schedule = ui.input(label='定时任务 优先级', value=config.get("filter", "priority_mapping", "schedule"), placeholder='数字越大，优先级越高').style("width:200px;").tooltip('数字越大，优先级越高')
                input_filter_priority_mapping_assistant_anchor_text = ui.input(label='助播-文本 优先级', value=config.get("filter", "priority_mapping", "assistant_anchor_text"), placeholder='数字越大，优先级越高').style("width:200px;").tooltip('数字越大，优先级越高')
                input_filter_priority_mapping_assistant_anchor_audio = ui.input(label='助播-音频 优先级', value=config.get("filter", "priority_mapping", "assistant_anchor_audio"), placeholder='数字越大，优先级越高').style("width:200px;").tooltip('数字越大，优先级越高')


        with ui.expansion('弹幕黑名单', icon="settings", value=True).classes('w-full'):
            with ui.row():
                switch_filter_blacklist_enable = ui.switch('启用', value=config.get("filter", "blacklist", "enable")).style(switch_internal_css)

            with ui.row():
                textarea_filter_blacklist_username = ui.textarea(label='用户名 黑名单', value=textarea_data_change(config.get("filter", "blacklist", "username")), placeholder='屏蔽此名单内所有用户的弹幕，用户名以换行分隔').style("width:500px;")
    # 原来在 save_common 里的 config_mapping["filter"] 整块搬来，字段与类型一字未改

    mapping = {
        "filter": {
            "before_must_str": (textarea_filter_before_must_str, 'textarea'),
            "after_must_str": (textarea_filter_after_must_str, 'textarea'),
            "before_filter_str": (textarea_filter_before_filter_str, 'textarea'),
            "after_filter_str": (textarea_filter_after_filter_str, 'textarea'),
            "before_must_str_for_llm": (textarea_filter_before_must_str_for_llm, 'textarea'),
            "after_must_str_for_llm": (textarea_filter_after_must_str_for_llm, 'textarea'),
            "badwords": {
                "enable": (switch_filter_badwords_enable, 'bool'),
                "discard": (switch_filter_badwords_discard, 'bool'),
                "path": (input_filter_badwords_path,'str'),
                "bad_pinyin_path": (input_filter_badwords_bad_pinyin_path,'str'),
                "replace": (input_filter_badwords_replace,'str'),
            },
            "username_convert_digits_to_chinese": (switch_filter_username_convert_digits_to_chinese, 'bool'),
            "emoji": (switch_filter_emoji, 'bool'),
            "max_len": (input_filter_max_len, 'int'),
            "max_char_len": (input_filter_max_char_len, 'int'),
            "comment_forget_duration": (input_filter_comment_forget_duration, 'float'),
            "comment_forget_reserve_num": (input_filter_comment_forget_reserve_num, 'int'),
            "gift_forget_duration": (input_filter_gift_forget_duration, 'float'),
            "gift_forget_reserve_num": (input_filter_gift_forget_reserve_num, 'int'),
            "entrance_forget_duration": (input_filter_entrance_forget_duration, 'float'),
            "entrance_forget_reserve_num": (input_filter_entrance_forget_reserve_num, 'int'),
            "follow_forget_duration": (input_filter_follow_forget_duration, 'float'),
            "follow_forget_reserve_num": (input_filter_follow_forget_reserve_num, 'int'),
            "talk_forget_duration": (input_filter_talk_forget_duration, 'float'),
            "talk_forget_reserve_num": (input_filter_talk_forget_reserve_num, 'int'),
            "schedule_forget_duration": (input_filter_schedule_forget_duration, 'float'),
            "schedule_forget_reserve_num": (input_filter_schedule_forget_reserve_num, 'int'),
            "idle_time_task_forget_duration": (input_filter_idle_time_task_forget_duration, 'float'),
            "idle_time_task_forget_reserve_num": (input_filter_idle_time_task_forget_reserve_num, 'int'),
            "image_recognition_schedule_forget_duration": (input_filter_image_recognition_schedule_forget_duration, 'float'),
            "image_recognition_schedule_forget_reserve_num": (input_filter_image_recognition_schedule_forget_reserve_num, 'int'),
            "limited_time_deduplication": {
                "enable": (switch_filter_limited_time_deduplication_enable, 'bool'),
                "comment": (input_filter_limited_time_deduplication_comment, 'int'),
                "gift": (input_filter_limited_time_deduplication_gift, 'int'),
                "entrance": (input_filter_limited_time_deduplication_entrance, 'int'),
            },
            "message_queue_max_len": (input_filter_message_queue_max_len, 'int'),
            "voice_tmp_path_queue_max_len": (input_filter_voice_tmp_path_queue_max_len, 'int'),
            "voice_tmp_path_queue_min_start_play": (input_filter_voice_tmp_path_queue_min_start_play, 'int'),
            "priority_mapping": {
                "idle_time_task": (input_filter_priority_mapping_idle_time_task, 'int'),
                "image_recognition_schedule": (input_filter_priority_mapping_image_recognition_schedule, 'int'),
                "local_qa_audio": (input_filter_priority_mapping_local_qa_audio, 'int'),
                "comment": (input_filter_priority_mapping_comment, 'int'),
                "song": (input_filter_priority_mapping_song, 'int'),
                "read_comment": (input_filter_priority_mapping_read_comment, 'int'),
                "entrance": (input_filter_priority_mapping_entrance, 'int'),
                "gift": (input_filter_priority_mapping_gift, 'int'),
                "follow": (input_filter_priority_mapping_follow, 'int'),
                "talk": (input_filter_priority_mapping_talk, 'int'),
                "reread": (input_filter_priority_mapping_reread, 'int'),
                "key_mapping": (input_filter_priority_mapping_key_mapping, 'int'),
                "integral": (input_filter_priority_mapping_integral, 'int'),
                "reread_top_priority": (input_filter_priority_mapping_reread_top_priority, 'int'),
                "copywriting": (input_filter_priority_mapping_copywriting, 'int'),
                "abnormal_alarm": (input_filter_priority_mapping_abnormal_alarm, 'int'),
                "trends_copywriting": (input_filter_priority_mapping_trends_copywriting, 'int'),
                "schedule": (input_filter_priority_mapping_schedule, 'int'),
                "assistant_anchor_text": (input_filter_priority_mapping_assistant_anchor_text, 'int'),
                "assistant_anchor_audio": (input_filter_priority_mapping_assistant_anchor_audio, 'int'),
            },
            "blacklist": {
                "enable": (switch_filter_blacklist_enable, 'bool'),
                "username": (textarea_filter_blacklist_username, 'textarea'),
            }
        }
    }

    return PageConfig(mapping=mapping)
