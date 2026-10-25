"""总览首页与分组导航条。

数据全部读自真实 config 与运行态：需要 main.py 才有的指标（连接时长、弹幕速率、
下次定时任务）这里一律不显示，宁可少几行也不放原型式的假数。
"""
from nicegui import ui

from webui_app.fields import jump_to
from webui_app.helpers import AUDIO_SYNTHESIS_TYPE_OPTIONS
from webui_app.options import CHAT_TYPE_OPTIONS, VISUAL_BODY_OPTIONS, platform_options
from webui_app.theme import LINK, readable_on

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


def page_order():
    """tab 条应有的顺序：总览打头，然后按分组走。"""
    return [OVERVIEW] + [name for _group, pages in NAV_GROUPS for name in pages]

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


def build_nav_chips(select, accent, search=None, toggle=None):
    """分组导航条：点组名跳到该组第一页，当前所在组高亮。返回 mark(tab 名) 用来刷高亮。

    toggle 是个 callable，在搜索按钮后面就地建出「只看已启用」开关（走查 audit-9）。
    """
    chips = {}
    with ui.row().style('gap:8px;flex-wrap:wrap;align-items:center;padding:2px 8px 0;width:100%;'):
        for name, members in [(OVERVIEW, None)] + NAV_GROUPS:
            first = OVERVIEW if members is None else members[0]
            chips[name] = ui.button(name, on_click=lambda target=first: select(target)).props(
                'flat dense no-caps size=sm').style('font-size:13px;font-weight:500;')
        if search is not None:
            ui.space()
            if toggle is not None:
                toggle()
            ui.button('搜索配置项', icon='search', on_click=search).props(
                'flat dense no-caps size=sm').style(f'font-size:13px;color:{LINK} !important;')

    def mark(tab_name):
        active = group_of(tab_name)
        for name, chip in chips.items():
            on = accent if name == active else 'transparent'
            # 按钮文字色必须带 !important：不带的话被 Quasar 的 text-primary 顶成默认蓝（3.06:1）。
            # 选中那枚的前景按主题色亮度挑——5 套主题里 3 套是高饱和亮色，白字压上去根本看不清。
            chip.style('background:' + on + ';color:' +
                       (readable_on(on) if name == active else INK_MUT) + ' !important;')

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
        'tab': '平台接入', 'field': '平台',
        'hint': '不接平台就只能按文案念，收不到任何弹幕',
    }, {
        'title': '大语言模型',
        'value': CHAT_TYPE_OPTIONS.get(chat_type, chat_type or '未选择'),
        'ok': bool(chat_type) and chat_type != 'none',
        'tab': '平台接入', 'field': '大语言模型',
        'hint': '不选则数字人不会回答，只会复读或只念文案',
    }, {
        'title': '文本转语音',
        'value': AUDIO_SYNTHESIS_TYPE_OPTIONS.get(tts_type, tts_type or '未选择'),
        'ok': bool(tts_type) and tts_type != 'none',
        'tab': '平台接入', 'field': '语音合成',
        'hint': '不选就没有声音，弹幕回复只会出现在字幕页',
    }, {
        'title': '虚拟身体',
        'value': VISUAL_BODY_OPTIONS.get(body, body or '未选择'),
        'ok': bool(body),
        'tab': '平台接入', 'field': '虚拟身体',
        'hint': '只要画面的话，留「其他（外置）」由外部窗口显示',
    }]


def build_overview_tab(config, state, dirty_guard, select, save_config, card_css, accent):
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

        with ui.element('div').classes('tip-bar'):
            ui.label('第一次搭：按 1→4 填完就能开播。填好的会打勾，点某一行右边的「去配置」直接跳到那个框。')

        for step, row in enumerate(readiness(config), start=1):
            with ui.row().style(
                    'align-items:center;gap:10px;width:100%;padding:8px 0;'
                    'border-top:1px solid rgba(17,24,39,0.10);'):
                # 没填的显示序号、填好的换成勾：既是一条有序路径，又一眼看出还差哪几步
                if row['ok']:
                    ui.icon('check_circle').style(f'color:{OK};font-size:20px;')
                else:
                    ui.badge(str(step)).style(
                        f'background:{WARN};color:#ffffff;font-size:12px;min-width:20px;text-align:center;')
                with ui.column().style('gap:0;flex:1;min-width:0;'):
                    ui.label(row['title']).style(f'font-size:14px;font-weight:600;color:{INK};')
                    ui.label(row['value'] if row['ok'] else f"{row['value']} —— {row['hint']}").style(
                        f'font-size:13px;color:{INK_MUT};')
                # 「去配置」不止切页，还要落到那个框上并描一下边（story-1 的验收标准）
                ui.button('去配置', on_click=lambda r=row: jump_to(
                    r['field'], 0, accent, select, r['tab'])).props(
                    'flat dense no-caps size=sm').style(f'color:{LINK} !important;')

        ui.button('保存配置', on_click=save_config).props('outline no-caps dense').style(
            'margin-top:12px;')
