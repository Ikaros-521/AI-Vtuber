"""WebUI 的资源页与关于页：纯展示，不参与配置读写。"""
from nicegui import ui


def build_docs_tab():
    with ui.row():
        ui.label('在线文档：')
        ui.link('https://ikaros521.eu.org/site/', 'https://ikaros521.eu.org/site/', new_tab=True)
        ui.link('gitee备份文档', 'https://ikaros-521.gitee.io/luna-docs/site/index.html', new_tab=True)

        ui.label('NiceGUI官方文档：')
        ui.link('nicegui.io/documentation', 'https://nicegui.io/documentation', new_tab=True)

        ui.label('视频教程合集：')
        ui.link('点我跳转', 'https://space.bilibili.com/3709626/channel/collectiondetail?sid=1422512', new_tab=True)

        ui.label('GitHub仓库：')
        ui.link('Ikaros-521/AI-Vtuber', 'https://github.com/Ikaros-521/AI-Vtuber', new_tab=True)

    with ui.expansion('视频教程', icon='movie_filter', value=True).classes('w-full'):
        ui.html('<iframe src="https://space.bilibili.com/3709626/channel/collectiondetail?sid=1422512" allowfullscreen="true" width="1800" height="800"> </iframe>').style("width:100%")

    with ui.expansion('文档', icon='article', value=True).classes('w-full'):
        ui.html('<iframe src="https://ikaros521.eu.org/site/" width="1800" height="800"></iframe>').style("width:100%")


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
    ui.image('./docs/xmind.png').style("width:1000px;")
