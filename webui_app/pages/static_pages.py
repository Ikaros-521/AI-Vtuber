"""WebUI 的资源页与关于页：纯展示，不参与配置读写。

文档页原先是 4 条裸 URL 文字链 + 两个写死 1800×800 的内嵌窗口：1440 宽下整页约 600px 空白，
链接看不出"点进去是什么、什么时候该点"，两个 iframe 还跟着建页一起加载。
现在改成卡片式目录（标题 + 一句用途 + 标签），内嵌预览收起来，要看再展开。
"""
from nicegui import ui

from webui_app.theme import INK, INK_MUT

DOCS_URL = 'https://ikaros521.eu.org/site/'
DOCS_BACKUP_URL = 'https://ikaros-521.gitee.io/luna-docs/site/index.html'
NICEGUI_URL = 'https://nicegui.io/documentation'
VIDEO_URL = 'https://space.bilibili.com/3709626/channel/collectiondetail?sid=1422512'
REPO_URL = 'https://github.com/Ikaros-521/AI-Vtuber'

# 摘要写的是「这页能解决什么」，不是复述标题——第一次搭环境的人按这个决定点哪个
RESOURCES = (
    {'title': '在线文档（主站）', 'url': DOCS_URL, 'tags': ('入门', '配置项', '部署'),
     'summary': '部署步骤、每个配置项的含义、常见问题都在这里。第一次搭环境从这页开始。'},
    {'title': 'gitee 备份文档', 'url': DOCS_BACKUP_URL, 'tags': ('镜像',),
     'summary': '主站打不开时用这个，内容与在线文档一致。'},
    {'title': 'NiceGUI 官方文档', 'url': NICEGUI_URL, 'tags': ('二次开发',),
     'summary': '想改本管理界面的布局、加控件时查这里——webui 就是 NiceGUI 写的。'},
    {'title': '视频教程合集', 'url': VIDEO_URL, 'tags': ('视频', 'B 站'),
     'summary': '作者整理的系列视频，适合不想读文档、跟着做一遍的人。'},
    {'title': 'GitHub 仓库', 'url': REPO_URL, 'tags': ('源码', 'Issue'),
     'summary': '源码、更新日志与提 Bug 的地方；本地文件缺失时也可以重新 clone。'},
)


def _card(item, card_css):
    with ui.card().style(card_css):
        ui.label(item['title']).style(f'font-size:16px;font-weight:600;color:{INK};')
        ui.label(item['summary']).style(f'font-size:13px;line-height:1.6;color:{INK_MUT};')
        with ui.row().classes('items-center').style('gap:8px;flex-wrap:wrap;'):
            ui.link('打开', item['url'], new_tab=True).props('no-caps dense').style(
                f'color:#2b5d9b !important;font-size:13px;')
            for tag in item['tags']:
                ui.label(tag).style(
                    'font-size:12px;padding:1px 8px;border-radius:9px;background:rgba(0,0,0,0.06);'
                    f'color:{INK_MUT};')


def _preview(title, icon, url, note):
    """内嵌预览默认收起：这两个站点都很重，原先每次建页都会加载一遍。"""
    with ui.expansion(title, icon=icon, value=False).classes('w-full'):
        # 1800×800 写死会把卡片撑出横向滚动条，改成随宽度缩放的 16:9（最高不超过 68vh，
        # 不然 1440 宽下预览本身就比一屏还高）。ui.html 外面那层 div 是 flex 子项，
        # 不给 w-full 它只按内容宽（实测 569px），预览就缩在左边一条。
        # ui.html 默认走 DOMPurify 客户端净化，iframe 会被整条抹掉（升级 nicegui 3 之后
        # 这两个预览就一直点开是空白），url 是本模块常量、不来自用户输入，才敢关净化。
        ui.html(f'<iframe src="{url}" loading="lazy" allowfullscreen '
                'style="width:100%;aspect-ratio:16/9;min-height:320px;max-height:68vh;border:0;'
                'border-radius:8px;background:#ffffff;"></iframe>', sanitize=False).classes('w-full')
        with ui.element('div').classes('tip-bar'):
            ui.label(note)


def build_docs_tab(card_css):
    with ui.grid(columns='repeat(auto-fill, minmax(320px, 1fr))').style('gap:12px;width:100%;'):
        for item in RESOURCES:
            _card(item, card_css)

    with ui.element('div').classes('tip-bar'):
        ui.label('要找某个配置项？按 Ctrl+K（或 Cmd+K）全站搜索，输入关键词直接跳到那个框，'
                 '不用先想它在哪个页签。')

    _preview('在线文档预览', 'article', DOCS_URL,
             '内嵌窗口如果是一片空白，是对方站点禁止被内嵌（X-Frame-Options），'
             '点上面「打开」在新标签页看即可。')
    _preview('视频教程预览', 'movie_filter', VIDEO_URL,
             'B 站页面较重，默认不加载；展开后再等一会儿。视频也可以直接在新标签页打开。')


def build_about_tab(card_css):
    with ui.card().style(card_css):
        ui.label('介绍').style("font-size:24px;")
        ui.label('AI Vtuber 是一款结合了最先进技术的虚拟AI主播。它的核心是一系列高效的人工智能模型，包括 ChatterBot、GPT、Claude、langchain、chatglm、text-generation-webui、讯飞星火、智谱AI、谷歌Bard、文心一言 和 通义星尘。这些模型既可以在本地运行，也可以通过云端服务提供支持。')
        ui.label('AI Vtuber 的外观由 Live2D、Vtube Studio、xuniren 和 UE5 结合 Audio2Face 技术打造，为用户提供了一个生动、互动的虚拟形象。这使得 AI Vtuber 能够在各大直播平台，如 Bilibili、抖音、快手、斗鱼、YouTube 和 Twitch，进行实时互动直播。当然，它也可以在本地环境中与您进行个性化对话。')
        ui.label('为了使交流更加自然，AI Vtuber 使用了先进的自然语言处理技术，结合文本转语音系统，如 Edge-TTS、VITS-Fast、elevenlabs、VALL-E-X、睿声AI、 tts.ai-lab.top和GPT-SoVITS。这不仅让它能够生成流畅的回答，还可以通过 so-vits-svc 和 DDSP-SVC 实现声音的变化，以适应不同的场景和角色。')
        ui.label('此外，AI Vtuber 还能够通过特定指令与 Stable Diffusion 协作，展示画作。用户还可以自定义文案，让 AI Vtuber 循环播放，以满足不同场合的需求。')
    with ui.card().style(card_css):
        ui.label('许可证').style("font-size:24px;")
        ui.label('这个项目采用 GNU通用公共许可证（GPL） 进行许可。有关详细信息，请参阅 LICENSE 文件。')
    with ui.card().style(card_css):
        ui.label('注意').style("font-size:24px;")
        ui.label('严禁将此项目用于一切违反《中华人民共和国宪法》，《中华人民共和国刑法》，《中华人民共和国治安管理处罚法》和《中华人民共和国民法典》之用途。')
        ui.label('严禁用于任何政治相关用途。')
    ui.image('./docs/xmind.png').style("width:1000px;max-width:100%;")
