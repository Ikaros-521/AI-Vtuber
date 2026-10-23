"""总览首页与分组导航条。

数据全部读自真实 config 与运行态：需要 main.py 才有的指标（连接时长、弹幕速率、
下次定时任务）这里一律不显示，宁可少几行也不放原型式的假数。
"""
from nicegui import ui

from webui_app.helpers import AUDIO_SYNTHESIS_TYPE_OPTIONS
from webui_app.options import CHAT_TYPE_OPTIONS, VISUAL_BODY_OPTIONS, platform_options

# 分组顺序按「自部署新主播」的落地顺序排：先连上直播间，再给脑子、给声音。
# 页面清单与 webui_app/repage.py 的 PAGE_PLAN 对应（那边负责把区块搬进这些 tab）
NAV_GROUPS = [
    ('开播', ['平台接入', '播报与输出']),
    ('大脑', ['大语言模型', '本地问答', '图像识别', '翻译']),
    ('声音', ['文本转语音', '变声', '文案']),
    ('互动', ['过滤', '念弹幕与答谢', '点歌', '定时与闲时', '联网与动态文案', '聊天', '积分', '助播']),
    ('舞台', ['虚拟身体', '出图', '按键与命令', '外部软件对接', '串口']),
    ('后台', ['数据分析', '日志与数据库', '异常报警', '页面配置', '文档&教程', '关于']),
]

OVERVIEW = '总览'

INK = '#111827'
INK_MUT = '#4b5563'
OK = '#16a34a'
WARN = '#b45309'


def group_of(tab_name):
    """某个 tab 属于哪一组；总览自己一组。"""
    for name, members in NAV_GROUPS:
        if tab_name in members:
            return name
    return OVERVIEW


def build_nav_chips(select, accent, search=None):
    """分组导航条：点组名跳到该组第一页，当前所在组高亮。返回 mark(tab 名) 用来刷高亮。"""
    chips = {}
    with ui.row().style('gap:4px;flex-wrap:wrap;align-items:center;padding:2px 8px 0;width:100%;'):
        for name, members in [(OVERVIEW, None)] + NAV_GROUPS:
            first = OVERVIEW if members is None else members[0]
            chips[name] = ui.button(name, on_click=lambda target=first: select(target)).props(
                'flat dense no-caps size=sm').style('font-size:13px;font-weight:500;')
        if search is not None:
            ui.space()
            ui.button('搜索配置项', icon='search', on_click=search).props(
                'flat dense no-caps size=sm').style('font-size:13px;')

    def mark(tab_name):
        active = group_of(tab_name)
        for name, chip in chips.items():
            chip.style('background:' + (accent if name == active else 'transparent') +
                       ';color:' + ('#ffffff' if name == active else INK_MUT) + ';')

    return mark


def readiness(config):
    """开播前四项的真实状态：只读 config 里已经填了什么，不猜。"""
    platform = config.get('platform')
    room = config.get('room_display_id')
    chat_type = config.get('chat_type')
    tts_type = config.get('audio_synthesis_type')
    body = config.get('visual_body')

    plat_label = platform_options(platform).get(platform, platform or '未选择')
    return [{
        'title': '弹幕来源',
        'value': plat_label + (f' · 房间号 {room}' if room else ' · 未填房间号'),
        'ok': bool(platform) and platform != 'talk' and bool(room),
        'tab': '平台接入',
        'hint': '不接平台就只能按文案念，收不到任何弹幕',
    }, {
        'title': '大语言模型',
        'value': CHAT_TYPE_OPTIONS.get(chat_type, chat_type or '未选择'),
        'ok': bool(chat_type) and chat_type != 'none',
        'tab': '大语言模型',
        'hint': '不选则数字人不会回答，只会复读或只念文案',
    }, {
        'title': '文本转语音',
        'value': AUDIO_SYNTHESIS_TYPE_OPTIONS.get(tts_type, tts_type or '未选择'),
        'ok': bool(tts_type) and tts_type != 'none',
        'tab': '文本转语音',
        'hint': '不选就没有声音，弹幕回复只会出现在字幕页',
    }, {
        'title': '虚拟身体',
        'value': VISUAL_BODY_OPTIONS.get(body, body or '未选择'),
        'ok': bool(body),
        'tab': '虚拟身体',
        'hint': '只要画面的话，留「其他（外置）」由外部窗口显示',
    }]


def build_overview_tab(config, state, dirty_guard, select, save_config, card_css):
    """总览面板：运行态 + 未保存计数 + 开播就绪度，每行都能一键跳到对应配置页。"""
    with ui.card().style(card_css + 'width:100%;max-width:760px;'):
        ui.label('开播就绪度').style(f'font-size:17px;font-weight:600;color:{INK};')

        running_flag = ui.label().style(f'font-size:13px;color:{INK_MUT};margin-top:6px;')
        dirty_flag = ui.label().style(f'font-size:13px;color:{INK_MUT};')
        dirty_guard.bind_status(dirty_flag)

        # 运行态也可能被 /sys_cmd 接口改，不在 UI 按钮里，所以只能轮询而不是在回调里刷
        def refresh():
            on = state.running_flag
            running_flag.set_text('直播程序运行中' if on else '直播程序未运行 · 右下角「操作」→ 一键运行')
            running_flag.style(f'color:{OK if on else INK_MUT};')

        refresh()
        ui.timer(2.0, refresh)

        for row in readiness(config):
            with ui.row().style(
                    'align-items:center;gap:10px;width:100%;padding:8px 0;'
                    'border-top:1px solid rgba(17,24,39,0.10);'):
                ui.icon('check_circle' if row['ok'] else 'error_outline').style(
                    f'color:{OK if row["ok"] else WARN};font-size:20px;')
                with ui.column().style('gap:0;flex:1;min-width:0;'):
                    ui.label(row['title']).style(f'font-size:14px;font-weight:600;color:{INK};')
                    ui.label(row['value'] if row['ok'] else f"{row['value']} —— {row['hint']}").style(
                        f'font-size:13px;color:{INK_MUT};')
                ui.button('去配置', on_click=lambda name=row['tab']: select(name)).props(
                    'flat dense no-caps size=sm')

        ui.button('保存配置', on_click=save_config).props('outline no-caps dense').style(
            'margin-top:12px;')
