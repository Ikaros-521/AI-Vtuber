"""长 tab 的区块索引。

长页面（拆分前的 通用配置 有 17,000px、二十来个区块）光靠滚动看不出「这页到底有什么」。
这里把每个 tab 顶层的卡片/折叠区标题列成一排，点一下滚过去并描一下边。
搜索解决「知道名字找得到」，这条解决「不知道有什么」。
"""

import json

from nicegui import context, ui
from nicegui.elements.card import Card
from nicegui.elements.expansion import Expansion
from nicegui.elements.label import Label
from nicegui.elements.tabs import TabPanel

# 区块少于这个数的页面不值得加索引，免得白占一行；再多就截断，索引条不该比内容还长
MIN_SECTIONS = 3
MAX_CHIPS = 36

INK_MUT = "#4b5563"
INK = "#111827"

# 8 大核心工作区的区块子分类规则：把扎堆散落的同类卡片精准收拢到对应业务小分类下
PAGE_SUBGROUPS = {
    "人设与大脑": [
        (
            "模型引擎 (LLM)",
            [
                "openai",
                "ollama",
                "chatglm",
                "langchain",
                "智谱",
                "千帆",
                "gemini",
                "anythingllm",
                "通义千问",
                "dify",
                "百川",
                "自定义llm",
                "火山引擎",
                "volcengine",
            ],
        ),
        ("人设与知识", ["对话与回复模板", "本地问答"]),
        ("多模态与翻译", ["图像识别", "百度翻译", "谷歌翻译", "翻译设置", "翻译"]),
    ],
    "声音与表现": [
        (
            "形象驱动 (Avatar)",
            [
                "live2d_tts_llm_gpt_sovits_vtuber",
                "metahuman_stream",
                "xuniren",
                "unity",
                "数字人视频播放器",
                "easyaivtuber",
                "live2d",
                "虚拟身体",
            ],
        ),
        ("变声后期 (SVC)", ["so-vits-svc", "so_vits_svc", "ddsp-svc", "ddsp_svc", "变声"]),
        (
            "语音合成 (TTS)",
            [
                "tts 语音合成调试",
                "合成测试",
                "edge-tts",
                "vits-simple-api",
                "bert_vits2",
                "elevenlabs",
                "openai tts",
                "gradio",
                "gpt-sovits",
                "azure_tts",
                "cosyvoice",
                "f5-tts",
                "multitts",
                "melotts",
                "index-tts",
            ],
        ),
        (
            "语音识别 (STT)",
            [
                "语音对话与拾音",
                "基本",
                "清除类型",
                "语音唤醒与睡眠",
                "对话打断",
                "谷歌",
                "百度",
                "faster_whisper",
                "sensevoice",
                "stt",
            ],
        ),
    ],
    "互动与玩法": [
        (
            "直播间互动",
            ["点歌", "积分", "签到", "礼物", "入场", "增删改查", "文案音频", "播放控制", "stable diffusion"],
        ),
        ("运营与保活", ["定时任务", "闲时任务", "动态配置", "联网搜索", "动态文案"]),
    ],
    "外设与联动": [
        ("软件联动", ["按键/文案/音频/串口/图片 映射", "自定义命令", "洛曦 直播弹幕助手", "联动程序"]),
        ("助播联动", ["串口", "基本", "触发类型", "文本匹配", "音频匹配", "助播"]),
    ],
    "运维与系统": [
        ("监控与数据", ["数据分析", "日志", "数据库", "异常报警"]),
        (
            "系统与设置",
            ["webui配置", "本地路径指定url路径访问", "css", "配置模板", "板块显示/隐藏", "账号管理", "板块开关"],
        ),
        ("文档与关于", ["在线文档", "gitee", "nicegui", "视频教程", "github", "文档预览", "介绍", "许可证", "注意"]),
    ],
    "直播接入": [
        ("连接配置", ["平台与模型", "平台相关", "哔哩哔哩", "twitch", "监听"]),
        ("音视频输出", ["音频播放", "web字幕"]),
    ],
    "弹幕与礼仪": [
        ("安全风控", ["过滤"]),
        ("弹幕响应", ["念弹幕", "答谢"]),
    ],
}


def _group_sections(panel_name, sections):
    """把平铺的区块标题按预设的业务子类归类。未预设或未命中的归入通用列表。"""
    if panel_name not in PAGE_SUBGROUPS:
        return [(None, sections)]

    subgroups_def = PAGE_SUBGROUPS[panel_name]
    used = set()
    result = []

    for group_name, patterns in subgroups_def:
        matched = []
        for s in sections:
            if s in used:
                continue
            s_clean = s.lower().replace(" ", "").replace("_", "").replace("-", "")
            for p in patterns:
                p_clean = p.lower().replace(" ", "").replace("_", "").replace("-", "")
                if p_clean in s_clean:
                    matched.append(s)
                    used.add(s)
                    break
        if matched:
            result.append((group_name, matched))

    remaining = [s for s in sections if s not in used]
    if remaining:
        result.append(("其它", remaining))

    return result or [(None, sections)]


# 用 %-格式而不是 str.format：这段脚本里全是花括号。
# DOM 里没有可用的 id（NiceGUI 3.18 不给普通元素渲染 id），所以按「区块第一行文字」认；
# 折叠区（.q-expansion-item）标题的连字图标文本会混进 textContent，因此除了精确相等
# 还留了 startsWith / includes 兜底。注意 Quasar 渲染出来的类名是 q-expansion-item，
# 写 .q-expansion 一个都匹配不到，指向折叠区的芯片就会点了没反应。
JS_SCROLL_TO = """(function () {
    const want = %s;
    const titleOf = (e) => {
        const h = e.querySelector(':scope > .q-expansion-item__container > .q-item')
                  || e.querySelector('.q-item');
        const src = h ? h.textContent : (e.innerText || '');
        const first = (src.split('\\n').find(s => s.trim()) || '').trim();
        return first.replace(/\\s+/g, ' ');
    };
    const cards = [...document.querySelectorAll('.q-tab-panel .q-card,.q-tab-panel .q-expansion-item')];
    let hit = cards.find(e => titleOf(e) === want);
    if (!hit) hit = cards.find(e => (e.innerText || '').trim().startsWith(want));
    if (!hit) hit = cards.find(e => (e.innerText || '').includes(want));
    if (!hit) return;
    window.__sectionHit = true;
    hit.scrollIntoView({block: 'start', behavior: 'smooth'});
    hit.style.outline = '2px solid %s';
    hit.style.outlineOffset = '2px';
    setTimeout(function () { hit.style.outline = ''; hit.style.outlineOffset = ''; }, 1800);
})()"""


def _title_of(section):
    if isinstance(section, Expansion):
        return str(section._props.get("label") or "").strip()
    for child in section:
        if isinstance(child, Label) and (child.text or "").strip():
            return child.text.strip()
    return ""


def _sections_of(container, depth=0):
    """顶层区块。

    卡片里再套卡片的不重复列；但折叠区要钻进去——一个页面可能就只摆三四个大折叠区，
    不钻进去就没有什么可索引的。
    """
    out = []
    for child in container:
        if isinstance(child, Expansion):
            inner = _sections_of(child, depth + 1) if depth == 0 else []
            if inner:
                out.extend(inner)
                continue
            title = _title_of(child)
            if title:
                out.append(title)
            continue
        if isinstance(child, Card):
            title = _title_of(child)
            if title:
                out.append(title)
            continue
        out.extend(_sections_of(child, depth))
    return out


def _scroll_to(title, accent):
    context.client.run_javascript(JS_SCROLL_TO % (json.dumps(title, ensure_ascii=False), accent))


def add_section_indexes(accent):
    """给所有区块够多的 tab 面板，在开头插一条结构化区块索引。返回 {tab 名: [区块名]} 便于测试与排查。"""
    accent = accent.rstrip(";")
    panels = [e for e in context.client.elements.values() if isinstance(e, TabPanel)]
    result = {}
    for panel in panels:
        sections = _sections_of(panel)[:MAX_CHIPS]
        if len(sections) < MIN_SECTIONS:
            continue
        panel_name = str(panel._props.get("name") or "")
        result[panel_name] = sections
        grouped = _group_sections(panel_name, sections)

        with (
            ui.row()
            .classes("section-index")
            .style(
                "position:sticky;top:0;z-index:30;"
                "gap:5px;row-gap:6px;flex-wrap:wrap;align-items:center;padding:6px 10px;"
                "background:rgba(255,255,255,0.92);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);"
                "border-radius:10px;margin-bottom:12px;"
                "border:1px solid rgba(229,231,235,0.85);box-shadow:0 2px 8px rgba(0,0,0,0.06);"
            ) as row
        ):
            ui.label("本页区块").style(
                f"font-size:12px;font-weight:600;color:{INK_MUT};align-self:center;margin-right:2px;"
            )
            for group_name, group_sections in grouped:
                if group_name:
                    ui.badge(group_name).props("outline rounded size=sm").style(
                        f"font-size:11px;font-weight:600;color:{INK};border-color:#d1d5db;"
                        "background:#ffffff;margin:0 2px 0 6px;padding:2px 8px;"
                    )
                for name in group_sections:
                    # flat 按钮在渐变面板上就是一串灰字，看不出能点：给个白药丸底
                    ui.button(name, on_click=lambda target=name, a=accent: _scroll_to(target, a)).props(
                        "flat dense no-caps size=xs"
                    ).style(
                        f"font-size:12px;color:{INK_MUT} !important;padding:2px 8px;"
                        "background:rgba(255,255,255,0.88);border-radius:10px;"
                        "box-shadow:0 1px 2px rgba(0,0,0,0.06);"
                    )
        row.move(panel, 0)
    return result
