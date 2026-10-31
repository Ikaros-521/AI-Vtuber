"""总览首页与分组导航条。

数据全部读自真实 config 与运行态：需要 main.py 才有的指标（连接时长、弹幕速率、
下次定时任务）这里一律不显示，宁可少几行也不放原型式的假数。
"""

import json

from nicegui import context, ui

from webui_app.fields import jump_to
from webui_app.helpers import AUDIO_SYNTHESIS_TYPE_OPTIONS
from webui_app.options import CHAT_TYPE_OPTIONS, VISUAL_BODY_OPTIONS, platform_options
from webui_app.theme import LINK, readable_on

# 9 大核心工作区：总览 + 聊天 + 7 大业务配置域，单排平铺
PAGE_LIST = [
    "总览",
    "聊天",
    "直播接入",
    "人设与大脑",
    "声音与表现",
    "弹幕与礼仪",
    "互动与玩法",
    "外设与联动",
    "运维与系统",
]

NAV_GROUPS = [(p, [p]) for p in PAGE_LIST if p != "总览"]

OVERVIEW = "总览"


def page_order():
    """tab 条应有的顺序：总览打头，然后按 8 大工作区走。"""
    return list(PAGE_LIST)


INK = "#111827"
INK_MUT = "#4b5563"
OK = "#16a34a"
WARN = "#b45309"


def group_of(tab_name):
    """某个 tab 属于哪一组；8 大工作区自身即为顶层。"""
    if tab_name in PAGE_LIST:
        return tab_name
    return OVERVIEW


def build_nav_chips(select, accent, search=None, toggle=None):
    """单排平铺的 8 大核心工作区导航。

    彻底移除混杂在导航中间的不可点击一级文本标签，将 29 个碎片微 Tab 收敛为 8 个高内聚核心工作区。
    常驻单排，点击直达，无折行无视觉噪音。
    toggle 是个 callable，在搜索按钮后面就地建出「只看已启用」开关。
    """
    page_chips = {}
    with (
        ui.row()
        .classes("luna-nav")
        .style("gap:6px;row-gap:6px;flex-wrap:wrap;align-items:center;width:100%;padding:4px 8px;")
    ):
        for page in PAGE_LIST:
            page_chips[page] = (
                ui.button(page, on_click=lambda target=page: select(target))
                .props("flat dense no-caps size=md")
                .style("font-size:13px;font-weight:500;padding:2px 10px;border-radius:6px;")
            )
        if search is not None:
            ui.space()
            if toggle is not None:
                toggle()
            ui.button("搜索配置项", icon="search", on_click=search).props("flat dense no-caps size=sm").style(
                f"font-size:13px;color:{LINK} !important;"
            )

    def mark(tab_name):
        # 当前页整枚高亮，其余深灰，一眼看到自己在哪；组名标签只做路标不参与高亮。
        # 按钮文字色必须带 !important：不带的话被 Quasar 的 text-primary 顶成默认蓝（3.06:1），
        # 选中那枚的前景按主题色亮度挑——5 套主题里 3 套是高饱和亮色，白字压上去根本看不清。
        for page, chip in page_chips.items():
            on = page == tab_name
            chip.style(
                "background:"
                + (accent if on else "transparent")
                + ";color:"
                + (readable_on(accent) if on else INK)
                + " !important;"
            )
        # 地址栏 ?tab= 跟着真实页面名走（全量 tab 条隐藏后收不到点击，原先靠它同步的路径断了）。
        # 建页期的那次 mark 不写：深链 ?tab=聊天 这时还没被恢复脚本点回去，提前写会把地址栏冲成总览
        if context.client.has_socket_connection:
            context.client.run_javascript(
                'history.replaceState(null, "", "?tab=" + encodeURIComponent(%s));'
                % json.dumps(tab_name, ensure_ascii=False)
            )

    return mark


def readiness(config):
    """开播前四项的真实状态：只读 config 里已经填了什么，不猜。"""
    platform = config.get("platform")
    room = config.get("room_display_id")
    chat_type = config.get("chat_type")
    tts_type = config.get("audio_synthesis_type")
    body = config.get("visual_body")

    plat_label = platform_options(platform).get(platform, platform or "未选择")
    return [
        {
            "title": "弹幕来源",
            "value": plat_label + (f" · 房间号 {room}" if room else " · 未填房间号"),
            "ok": bool(platform) and platform != "talk" and bool(room),
            "tab": "直播接入",
            "field": "平台",
            "hint": "不接平台就只能按文案念，收不到任何弹幕",
        },
        {
            "title": "大语言模型",
            "value": CHAT_TYPE_OPTIONS.get(chat_type, chat_type or "未选择"),
            "ok": bool(chat_type) and chat_type != "none",
            "tab": "直播接入",
            "field": "大语言模型",
            "hint": "不选则数字人不会回答，只会复读或只念文案",
        },
        {
            "title": "文本转语音",
            "value": AUDIO_SYNTHESIS_TYPE_OPTIONS.get(tts_type, tts_type or "未选择"),
            "ok": bool(tts_type) and tts_type != "none",
            "tab": "直播接入",
            "field": "语音合成",
            "hint": "不选就没有声音，弹幕回复只会出现在字幕页",
        },
        {
            "title": "虚拟身体",
            "value": VISUAL_BODY_OPTIONS.get(body, body or "未选择"),
            "ok": bool(body),
            "tab": "直播接入",
            "field": "虚拟身体",
            "hint": "只要画面的话，留「其他（外置）」由外部窗口显示",
        },
    ]


def build_overview_tab(config, state, dirty_guard, select, save_config, card_css, accent):
    """总览面板：运行态 + 未保存计数 + 开播就绪度，每行都能一键跳到对应配置页。"""
    with ui.card().style(card_css + "width:100%;max-width:760px;margin:10px auto;"):
        ui.label("开播就绪度").style(f"font-size:17px;font-weight:600;color:{INK};")

        running_flag = ui.label().style(f"font-size:13px;color:{INK_MUT};margin-top:6px;")
        dirty_flag = ui.label().style(f"font-size:13px;color:{INK_MUT};")
        dirty_guard.bind_status(dirty_flag)

        # 运行态也可能被 /sys_cmd 接口改，不在 UI 按钮里，所以只能轮询而不是在回调里刷
        def refresh():
            on = state.running_flag
            running_flag.set_text("直播程序运行中" if on else "直播程序未运行 · 右下角「操作」→ 一键运行")
            running_flag.style(f"color:{OK if on else INK_MUT};")

        refresh()
        ui.timer(2.0, refresh)

        with ui.element("div").classes("tip-bar"):
            ui.label("第一次搭：按 1→4 填完就能开播。填好的会打勾，点某一行右边的「去配置」直接跳到那个框。")

        for step, row in enumerate(readiness(config), start=1):
            with ui.row().style(
                "align-items:center;gap:10px;width:100%;padding:8px 0;border-top:1px solid rgba(17,24,39,0.10);"
            ):
                # 没填的显示序号、填好的换成勾：既是一条有序路径，又一眼看出还差哪几步
                if row["ok"]:
                    ui.icon("check_circle").style(f"color:{OK};font-size:20px;")
                else:
                    ui.badge(str(step)).style(
                        f"background:{WARN};color:#ffffff;font-size:12px;min-width:20px;text-align:center;"
                    )
                with ui.column().style("gap:0;flex:1;min-width:0;"):
                    ui.label(row["title"]).style(f"font-size:14px;font-weight:600;color:{INK};")
                    ui.label(row["value"] if row["ok"] else f"{row['value']} —— {row['hint']}").style(
                        f"font-size:13px;color:{INK_MUT};"
                    )
                # 「去配置」不止切页，还要落到那个框上并描一下边（story-1 的验收标准）
                ui.button("去配置", on_click=lambda r=row: jump_to(r["field"], 0, accent, select, r["tab"])).props(
                    "flat dense no-caps size=sm"
                ).style(f"color:{LINK} !important;")

        ui.button("保存配置", on_click=save_config).props("outline no-caps dense").style("margin-top:12px;")
