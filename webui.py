from nicegui import ui, app
import sys, os, json
import traceback
from pathlib import Path

from utils.my_log import logger
from utils.config import Config
from utils.common import Common
from utils.audio import Audio

from webui_app.api import register_api
from webui_app.chat_log import chat_log
from webui_app.config_store import update_config
from webui_app.confirm import confirm
from webui_app.dirty_guard import DirtyGuard
from webui_app.errors import explain
from webui_app.fields import INVALID_RING, jump_to_element
from webui_app.helpers import AUDIO_SYNTHESIS_TYPE_OPTIONS
from webui_app.login import build_login, start_expiration_timer
from webui_app.overview import OVERVIEW, build_nav_chips, build_overview_tab
from webui_app.pages.assistant_anchor import build_assistant_anchor_tab
from webui_app.pages.common_config import build_common_config_tab, validate_config, write_local_qa_file
from webui_app.pages.copywriting import build_copywriting_tab
from webui_app.pages.data_analysis import build_data_analysis_tab
from webui_app.pages.image_recognition import build_image_recognition_tab
from webui_app.pages.interact_filter import build_interact_filter_tab
from webui_app.pages.integral import build_integral_tab
from webui_app.pages.llm import build_llm_tab
from webui_app.pages.serial import build_serial_tab
from webui_app.pages.static_pages import build_about_tab, build_docs_tab
from webui_app.pages.svc import build_svc_tab
from webui_app.pages.talk import build_talk_tab
from webui_app.pages.translate import build_translate_tab
from webui_app.pages.tts import build_tts_tab
from webui_app.pages.visual_body import build_visual_body_tab
from webui_app.pages.web_page import build_web_page_tab
from webui_app.repage import apply_page_plan
from webui_app.processes import (
    restart_application,
    run_external_program,
    scroll_to_top,
    stop_external_program,
)
from webui_app.search import ConfigSearch
from webui_app.undo import undo
from webui_app.sections import add_section_indexes
from webui_app.state import state

"""

@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@.:;;;++;;;;:,@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@:;+++++;;++++;;;.@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@:++++;;;;;;;;;;+++;,@@@@@@@@@@@@@@@@@
@@@@@@@@@@@.;+++;;;;;;;;;;;;;;++;:@@@@@@@@@@@@@@@@
@@@@@@@@@@;+++;;;;;;;;;;;;;;;;;;++;:@@@@@@@@@@@@@@
@@@@@@@@@:+++;;;;;;;;;;;;;;;;;;;;++;.@@@@@@@@@@@@@
@@@@@@@@;;+;;;;;;;;;;;;;;;;;;;;;;;++:@@@@@@@@@@@@@
@@@@@@@@;+;;;;:::;;;;;;;;;;;;;;;;:;+;,@@@@@@@@@@@@
@@@@@@@:+;;:;;:::;:;;:;;;;::;;:;:::;+;.@@@@@@@@@@@
@@@@@@.;+;::;:,:;:;;+:++:;:::+;:::::++:+@@@@@@@@@@
@@@@@@:+;;:;;:::;;;+%;*?;;:,:;*;;;;:;+;:@@@@@@@@@@
@@@@@@;;;+;;+;:;;;+??;*?++;,:;+++;;;:++:@@@@@@@@@@
@@@@@.++*+;;+;;;;+?;?**??+;:;;+.:+;;;;+;;@@@@@@@@@
@@@@@,+;;;;*++*;+?+;**;:?*;;;;*:,+;;;;+;,@@@@@@@@@
@@@@@,:,+;+?+?++?+;,?#%*??+;;;*;;:+;;;;+:@@@@@@@@@
@@@@@@@:+;*?+?#%;;,,?###@#+;;;*;;,+;;;;+:@@@@@@@@@
@@@@@@@;+;??+%#%;,,,;SSS#S*+++*;..:+;?;+;@@@@@@@@@
@@@@@@@:+**?*?SS,,,,,S#S#+***?*;..;?;**+;@@@@@@@@@
@@@@@@@:+*??*??S,,,,,*%SS+???%++;***;+;;;.@@@@@@@@
@@@@@@@:*?*;*+;%:,,,,;?S?+%%S?%+,:?;+:,,,@@@@@@@@
@@@@@@@,*?,;+;+S:,,,,%?+;S%S%++:+??+:,,,:@@@@@@@@
@@@@@@@,:,@;::;+,,,,,+?%*+S%#?*???*;,,,,,.@@@@@@@@
@@@@@@@@:;,::;;:,,,,,,,,,?SS#??*?+,.,,,:,@@@@@@@@@
@@@@@@;;+;;+:,:%?%*;,,,,SS#%*??%,.,,,,,:@@@@@@@@@
@@@@@.+++,++:;???%S?%;.+#####??;.,,,,,,:@@@@@@@@@
@@@@@:++::??+S#??%#??S%?#@#S*+?*,,,,,,:,@@@@@@@@@@
@@@@@:;;:*?;+%#%?S#??%SS%+#%..;+:,,,,,,@@@@@@@@@@@
@@@@@@,,*S*;?SS?%##%?S#?,.:#+,,+:,,,,,,@@@@@@@@@@@
@@@@@@@;%?%#%?*S##??##?,..*#,,+:,,;*;.@@@@@@@@@@@
@@@@@@.*%??#S*?S#@###%;:*,.:#:,+;:;*+:@@@@@@@@@@@@
@@@@@@,%S??SS%##@@#%S+..;;.,#*;???*?+++:@@@@@@@@@@
@@@@@@:S%??%####@@S,,*,.;*;+#*;+?%??#S%+.@@@@@@@@@
@@@@@@:%???%@###@@?,,:**S##S*;.,%S?;+*?+.,..@@@@@@
@@@@@@;%??%#@###@@#:.;@@#@%%,.,%S*;++*++++;.@@@@@
@@@@@@,%S?S@@###@@@%+#@@#@?;,.:?;??++?%?***+.@@@@@
@@@@@@.*S?S####@@####@@##@?..:*,+:??**%+;;;;..@@@@
@@@@@@:+%?%####@@####@@#@%;:.;;:,+;?**;++;,:;:,@@@
@@@@@@;;*%?%@##@@@###@#S#*:;*+,;.+***?******+:.@@@
@@@@@@:;:??%@###%##@#%++;+*:+;,:;+%?*;+++++;:.@@@@
@@@@@@.+;:?%@@#%;+S*;;,:::**+,;:%??*+.@....@@@@@@@
@@@@@@@;*::?#S#S+;,..,:,;:?+?++*%?+::@@@@@@@@@@@@@
@@@@@@@.+*+++?%S++...,;:***??+;++:.@@@@@@@@@@@@@@@
@@@@@@@@:::..,;+*+;;+*?**+;;;+;:.@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@,+*++;;:,..@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@::,.@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

"""


"""
全局变量
"""
common = None
config = None
audio = None
config_path = None


"""
初始化基本配置
"""
def init():
    """
    初始化基本配置
    """
    global config_path, config, common, audio

    common = Common()

    if getattr(sys, 'frozen', False):
        # 当前是打包后的可执行文件
        bundle_dir = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
        file_relative_path = bundle_dir.resolve()
    else:
        # 当前是源代码
        file_relative_path = Path(__file__).parent.resolve()

    # logger.info(file_relative_path)

    # 初始化文件夹
    def init_dir():
        # 创建日志文件夹
        log_dir = file_relative_path / 'log'
        # mkdir 方法的 parents=True 参数可以确保父目录的创建（如有必要），exist_ok=True 则避免在目录已存在时抛出异常。
        log_dir.mkdir(parents=True, exist_ok=True)

        # 创建音频输出文件夹
        audio_out_dir = file_relative_path / 'out'
        audio_out_dir.mkdir(parents=True, exist_ok=True)

    init_dir()
    logger.debug("项目相关文件夹初始化完成")

    # 配置文件路径（可用 LUNA_CONFIG_PATH 覆盖，便于多实例与自动化测试）
    config_path = os.environ.get("LUNA_CONFIG_PATH") or str(file_relative_path / 'config.json')

    logger.debug("配置文件路径=" + str(config_path))

    # 实例化音频类
    audio = Audio(config_path, type=2)
    # 实例化配置类
    config = Config(config_path)

# 初始化基本配置
init()

# 将本地目录中的静态文件（如 CSS、JavaScript、图片等）暴露给 web 服务器，以便用户可以通过特定的 URL 访问这些文件。
if config.get("webui", "local_dir_to_endpoint", "enable"):
    for tmp in config.get("webui", "local_dir_to_endpoint", "config"):
        app.add_static_files(tmp['url_path'], tmp['local_dir'])

# 对 main.py 暴露的 HTTP 接口，注册一次即可
register_api(config, common, audio)

# 暗夜模式
dark = ui.dark_mode()

"""
通用函数
"""
r"""
                                                                                                    
                                               .@@@@@                           @@@@@.              
                                               .@@@@@                           @@@@@.              
        ]]]]]   .]]]]`   .]]]]`   ,]@@@@@\`    .@@@@@,/@@@\`   .]]]]]   ]]]]]`  ]]]]].              
        =@@@@^  =@@@@@`  =@@@@. =@@@@@@@@@@@\  .@@@@@@@@@@@@@  *@@@@@   @@@@@^  @@@@@.              
         =@@@@ ,@@@@@@@ .@@@@` =@@@@^   =@@@@^ .@@@@@`  =@@@@^ *@@@@@   @@@@@^  @@@@@.              
          @@@@^@@@@\@@@^=@@@^  @@@@@@@@@@@@@@@ .@@@@@   =@@@@@ *@@@@@   @@@@@^  @@@@@.              
          ,@@@@@@@^ \@@@@@@@   =@@@@^          .@@@@@.  =@@@@^ *@@@@@  .@@@@@^  @@@@@.              
           =@@@@@@  .@@@@@@.    \@@@@@]/@@@@@` .@@@@@@]/@@@@@. .@@@@@@@@@@@@@^  @@@@@.              
            \@@@@`   =@@@@^      ,\@@@@@@@@[   .@@@@^\@@@@@[    .\@@@@@[=@@@@^  @@@@@.    
            
"""
# 配置
webui_ip = config.get("webui", "ip")
webui_port = config.get("webui", "port")
webui_title = config.get("webui", "title")

# CSS
theme_choose = config.get("webui", "theme", "choose")
tab_panel_css = config.get("webui", "theme", "list", theme_choose, "tab_panel")
card_css = config.get("webui", "theme", "list", theme_choose, "card")
button_bottom_css = config.get("webui", "theme", "list", theme_choose, "button_bottom")
button_bottom_color = config.get("webui", "theme", "list", theme_choose, "button_bottom_color")
button_internal_css = config.get("webui", "theme", "list", theme_choose, "button_internal")
button_internal_color = config.get("webui", "theme", "list", theme_choose, "button_internal_color")
switch_internal_css = config.get("webui", "theme", "list", theme_choose, "switch_internal")
echart_css = config.get("webui", "theme", "list", theme_choose, "echart")

# 未保存改动守卫：角标与浏览器关闭拦截，页面构建完成后在 goto_func_page 里接线
dirty_guard = DirtyGuard()

# 右下角两枚状态徽标的底样式。徽标是 ui.button，NiceGUI 会给它挂上 Quasar 的 text-primary，
# 那是条 !important 规则，普通内联色压不过，所以状态色一律要带 !important（实测踩过）。
PILL_CSS = ("font-size:12px;padding:4px 10px;border-radius:14px;background:#ffffff;"
            "box-shadow:0 1px 4px rgba(0,0,0,0.18);color:{} !important;")

"""
页面级脚本与样式

- .q-page 底部留白：右下角的操作条浮在页面上，留白由 ResizeObserver 跟着它的真实高度算
- <900px 的流式化：定宽控件/卡片改成整行、网格降单列（实测 390 下 16 个 tab 从 11 个横向溢出降到 0 个）
- .narrow-tip：窄屏提示条，默认不显示，窗口 <900px 才显
- ?tab= 深链：NiceGUI 是单页应用，16 个 tab 都挂在同一个 URL 上，
  不写进地址栏就没法把「哪个配置页」发给别人，刷新也回不到原来那一页
"""
PAGE_SCRIPTS = """
<style>
.q-page{padding-bottom:100px;}
</style>
<script>
// 底部留白跟着操作条的真实高度走。写死一个数迟早被超：这条栏会随展开/收起、
// 窗口换行改高度（390 展开后实测 225px，把「密码」那个框压到了栏底下点不到）。
(function () {
    const apply = function () {
        const bar = document.querySelector('.q-page-sticky');
        const page = document.querySelector('.q-page');
        if (!bar || !page) return;
        page.style.paddingBottom = (Math.round(bar.getBoundingClientRect().height) + 24) + 'px';
    };
    if (!window.ResizeObserver) return;
    const poll = setInterval(function () {
        const bar = document.querySelector('.q-page-sticky');
        if (!bar) return;
        clearInterval(poll);
        new ResizeObserver(apply).observe(bar);
        apply();
    }, 300);
})();
</script>
<style>
.narrow-tip{display:none !important;}
/* 提示条：原先三处写死 Tailwind 的 bg-blue-100，换深色主题就成了一块突兀的浅蓝。
   半透明白底 + 左侧色条，在渐变背景和卡片上都读得清 */
.tip-bar{padding:8px 12px;border-radius:8px;background:rgba(255,255,255,0.72);
         border-left:3px solid #2f6fad;box-shadow:0 1px 3px rgba(0,0,0,0.10);
         font-size:13px;line-height:1.6;color:#1f3552;}
/* 聊天记录面板浮在右侧，500px 宽：窗口不够宽就会压住配置项（1024 实测遮 1 个，
   640 遮 7 个）。不够宽时改成正常流，代价是要滚到页面上方才看得到日志 */
@media (max-width:1279px){.chat-log-float{position:static !important;}}
@media (max-width:899px){
  .narrow-tip{display:flex !important;}
  /* 页面里 850 多处 .style('width:XXXpx') 不可能逐个改，窄屏用样式表的 !important
     覆盖内联宽度，是代价最小的流式化做法：定宽控件降成整行，卡片和按钮最多撑满一行 */
  .q-tab-panel .q-field,
  .q-tab-panel .q-img,
  .q-tab-panel img,
  .q-tab-panel video,
  .q-tab-panel audio,
  .q-tab-panel .q-table{width:100% !important;max-width:100% !important;}
  .q-tab-panel .q-card{width:100% !important;max-width:100% !important;}
  .q-tab-panel .q-btn{max-width:100%;}
  /* flex 子项默认 min-width:auto，里面只要有一个定宽控件就会把整行顶出视口；
     NiceGUI 的 row/column 落到 DOM 是 .nicegui-row / .nicegui-column，不是 q-row */
  .q-tab-panel .nicegui-row > *,
  .q-tab-panel .nicegui-column > *{min-width:0;}
  .q-tab-panel .nicegui-grid{grid-template-columns:1fr !important;}
  /* 开关/勾选框被挤窄时「启用」会竖排成两行，这类控件保持自身宽度、标签不折行 */
  .q-tab-panel .q-toggle,
  .q-tab-panel .q-checkbox,
  .q-tab-panel .q-radio{flex:none;}
  .q-tab-panel .q-q-item__label{white-space:nowrap;}
  .q-tab-panel pre{overflow-x:auto;max-width:100%;}
  /* 区块索引在窄屏收成一行横向滑，21 个芯片竖着排能占掉半屏；
     必须同时压住宽度，否则 nowrap 会让这一行自己把面板顶宽 */
  .section-index{flex-wrap:nowrap !important;overflow-x:auto;
                 width:100% !important;max-width:100% !important;min-width:0;}
  /* 芯片本身不能被压缩，否则一行 21 个会被挤成一列一个字 */
  .section-index > *{flex:none;}
  /* 图表容器的 height:600px 写在主题里（width:100%;height:600px），390 下饼图被裁、
     图例挤出卡片：改成按宽度等比，ECharts 自己有 ResizeObserver 会重排 */
  .nicegui-echart{height:auto !important;aspect-ratio:1/1;max-height:70vh;}
}
</style>
<script>
(function () {
    function tabByName(name) {
        return Array.prototype.find.call(document.querySelectorAll('.q-tab'),
                                        function (el) { return el.textContent.trim() === name; });
    }

    var want = new URLSearchParams(location.search).get('tab');
    if (want) {
        var tries = 0;
        var timer = setInterval(function () {
            var el = tabByName(want);
            if (el) { clearInterval(timer); el.click(); }
            else if (++tries > 40) { clearInterval(timer); }
        }, 100);
    }

    document.addEventListener('click', function (ev) {
        var el = ev.target.closest ? ev.target.closest('.q-tab') : null;
        if (!el) { return; }
        history.replaceState(null, '', '?tab=' + encodeURIComponent(el.textContent.trim()));
    }, true);
})();
</script>
"""

def goto_func_page():
    """
    跳转到功能页
    """
    if config.get("login", "enable"):
        # 十分钟一次的检测
        start_expiration_timer(config, common)

    # 开关灯
    def change_light_status(type="webui"):
        if dark.value:
            button_light.set_text("关灯")
        else:
            button_light.set_text("开灯")
        dark.toggle()

    # 读取webui配置到dict变量
    def webui_config_to_dict(config_data):
        """读取webui配置到dict变量

        Args:
            config_data (dict): 从本地配置文件读取的dict数据
        """

        # 类型处理函数
        try:
            for page_config in page_config_mappings:
                if page_config is None:
                    continue
                if page_config.mapping:
                    config_data = update_config(page_config.mapping, config, config_data, None)
                if page_config.on_save:
                    page_config.on_save(config_data)

            return config_data
        except Exception as e:
            logger.error(f"无法读取webui配置到变量！\n{e}")
            ui.notify(position="top", type="negative",
                        message=f"读取界面上的值失败：{explain(e)}（完整错误见服务端日志）")
            logger.error(traceback.format_exc())

            return None

    # 保存配置
    def save_config():
        """
        保存配置到本地配置文件中
        """
        # 配置检查：拦下来时不只弹一条 toast，还要把用户带到那个框上描一圈红
        error = validate_config()
        if error:
            message, field = error
            ui.notify(position="top", type="negative",
                      message=message if field is None else f'{message} · 已跳到那个框')
            if field is not None:
                jump_to_element(field, button_bottom_color, select_tab, color=INVALID_RING)
            return False

        try:
            with open(config_path, 'r', encoding="utf-8") as config_file:
                config_data = json.load(config_file)
        except Exception as e:
            logger.error(f"无法读取配置文件！\n{e}")
            ui.notify(position="top", type="negative",
                message=f"配置文件读不出来：{explain(e)}（路径 {config_path}）")
            return False

        # 读取webui配置到dict变量
        config_data = webui_config_to_dict(config_data)
        if config_data is None:
            return False

        # 写入本地问答json数据到文件（控件在通用配置页模块里）
        if not write_local_qa_file():
            return False

        # 写入配置到配置文件
        try:
            with open(config_path, 'w', encoding="utf-8") as config_file:
                json.dump(config_data, config_file, indent=2, ensure_ascii=False)
                config_file.flush()  # 刷新缓冲区，确保写入立即生效

            logger.info("配置数据已成功写入文件！")
            ui.notify(position="top", type="positive", message="配置数据已成功写入文件！")

            # 写盘成功后才清脏状态：放在最后是因为 on_save 回调里还会回写控件值，
            # 提前清会让守卫把「自己写的值」重新记成未保存
            dirty_guard.mark_saved()
            # 已经写盘了，再让撤销把控件恢复回去只会和文件对不上
            undo.forget()

            return True
        except Exception as e:
            logger.error(f"无法写入配置文件！\n{str(e)}")
            ui.notify(position="top", type="negative",
                    message=f"配置文件写不进去：{explain(e)}（路径 {config_path}）")
            return False
        


    r"""

    ..............................................................................................................
    ..............................................................................................................
    ..........................,]].................................................................................
    .........................O@@@@^...............................................................................
    .....=@@@@@`.....O@@@....,\@@[.....................................,@@@@@@@@@@]....O@@@^......=@@@@....O@@@^..
    .....=@@@@@@.....O@@@............................................=@@@@/`..,[@@/....O@@@^......=@@@@....O@@@^..
    .....=@@@@@@@....O@@@....,]]]].......]@@@@@]`.....,/@@@@\`....../@@@@..............O@@@^......=@@@@....O@@@^..
    .....=@@@/@@@\...O@@@....=@@@@....,@@@@@@@@@@^..,@@@@@@@@@@\...=@@@@...............O@@@^......=@@@@....O@@@^..
    .....=@@@^,@@@\..O@@@....=@@@@...,@@@@`........=@@@/....=@@@\..=@@@@....]]]]]]]]...O@@@^......=@@@@....O@@@^..
    .....=@@@^.=@@@^.O@@@....=@@@@...O@@@^.........@@@@......@@@@..=@@@@....=@@@@@@@...O@@@^......=@@@@....O@@@^..
    .....=@@@^..\@@@^=@@@....=@@@@...@@@@^........,@@@@@@@@@@@@@@..=@@@@.......=@@@@...O@@@^......=@@@@....O@@@^..
    .....=@@@^...\@@@/@@@....=@@@@...O@@@^.........@@@@`...........,@@@@`......=@@@@...O@@@^......=@@@@....O@@@^..
    .....=@@@^....@@@@@@@....=@@@@...,@@@@`........=@@@@......,.....=@@@@`.....=@@@@...=@@@@`.....@@@@^....O@@@^..
    .....=@@@^....,@@@@@@....=@@@@....,@@@@@@@@@@`..=@@@@@@@@@@@`....,@@@@@@@@@@@@@@....,@@@@@@@@@@@@`.....O@@@^..
    .....,[[[`.....,[[[[[....,[[[[.......[@@@@@[`.....,[@@@@@[`.........,\@@@@@@[`.........[@@@@@@[........[[[[`..
    ..............................................................................................................
    ..............................................................................................................

    """

    # 语音合成所有配置项
    audio_synthesis_type_options = AUDIO_SYNTHESIS_TYPE_OPTIONS

    # 聊天类型所有配置项
    page_config_mappings = []

    # 窄屏提示：定宽控件在 <900px 已被上面那段样式表改成单列，不再裁；
    # 这条只说明「窄屏能看到的东西少」，别再写会被裁掉那种已经不实的话
    with ui.row().style(
            'background:#fef3c7;color:#78350f;padding:8px 14px;border-radius:8px;'
            'justify-content:center;align-items:center;margin:0 10px 6px;').classes('narrow-tip'):
        ui.label('窄屏已自动改成单列，配置项多时要滚很久；能放宽窗口就放宽，一屏能看到更多。') \
            .style('font-size:13px;')

    # 分组导航条：16 个平铺 tab 归到「总览 + 6 组」，点组名跳到该组第一页。
    # 这里不重建面板，只是给既有 tab 加一层可读的外壳
    def select_tab(name):
        tabs.set_value(name)

    config_search = ConfigSearch(select_tab, button_bottom_color)
    mark_group = build_nav_chips(select_tab, button_bottom_color.rstrip(';'), config_search.open)

    with ui.tabs().classes('w-full') as tabs:
        overview_page = ui.tab('总览')
        common_config_page = ui.tab('平台接入')
        llm_page = ui.tab('大语言模型')
        tts_page = ui.tab('文本转语音')
        svc_page = ui.tab('变声')
        visual_body_page = ui.tab('虚拟身体')
        copywriting_page = ui.tab('文案')
        interact_filter_page = ui.tab('过滤')
        talk_page = ui.tab('聊天')
        image_recognition_page = ui.tab('图像识别')
        integral_page = ui.tab('积分')
        assistant_anchor_page = ui.tab('助播')
        translate_page = ui.tab('翻译')
        serial_page = ui.tab('串口')
        data_analysis_page = ui.tab('数据分析')
        web_page = ui.tab('页面配置')
        docs_page = ui.tab('文档&教程')
        about_page = ui.tab('关于')

    tabs.on_value_change(lambda e: mark_group(e.value))
    mark_group(OVERVIEW)

    with ui.tab_panels(tabs, value=overview_page).classes('w-full') as tab_panels:
        with ui.tab_panel(overview_page).style(tab_panel_css):
            build_overview_tab(config, state, dirty_guard, select_tab, save_config, card_css,
                               button_bottom_color)

        with ui.tab_panel(common_config_page).style(tab_panel_css) as common_config_panel:
            page_config_mappings.append(build_common_config_tab(
                config, common, card_css, switch_internal_css, button_internal_color, button_internal_css))

        with ui.tab_panel(llm_page).style(tab_panel_css):
            page_config_mappings.append(build_llm_tab(
                config, common, card_css, switch_internal_css, button_bottom_color, button_bottom_css, button_internal_color, button_internal_css))

        with ui.tab_panel(tts_page).style(tab_panel_css):
            page_config_mappings.append(build_tts_tab(
                config, common, audio, card_css, switch_internal_css, button_internal_color, button_internal_css))

        with ui.tab_panel(svc_page).style(tab_panel_css):
            page_config_mappings.append(build_svc_tab(config, common, card_css, switch_internal_css))

        with ui.tab_panel(visual_body_page).style(tab_panel_css):
            page_config_mappings.append(build_visual_body_tab(config, common, card_css, switch_internal_css))

        with ui.tab_panel(copywriting_page).style(tab_panel_css):
            page_config_mappings.append(build_copywriting_tab(
                config, common, audio, card_css, switch_internal_css, button_internal_color, button_internal_css))

        with ui.tab_panel(integral_page).style(tab_panel_css):
            page_config_mappings.append(build_integral_tab(config, card_css, switch_internal_css))

        with ui.tab_panel(interact_filter_page).style(tab_panel_css):
            page_config_mappings.append(build_interact_filter_tab(config, card_css, switch_internal_css))

        with ui.tab_panel(talk_page).style(tab_panel_css):
            page_config_mappings.append(build_talk_tab(
                config, common, state, chat_log, card_css, switch_internal_css, button_internal_color, button_internal_css))

        with ui.tab_panel(image_recognition_page).style(tab_panel_css):
            page_config_mappings.append(build_image_recognition_tab(
                config, common, state, card_css, switch_internal_css, button_internal_color, button_internal_css))

        with ui.tab_panel(assistant_anchor_page).style(tab_panel_css):
            page_config_mappings.append(build_assistant_anchor_tab(
                config, common, audio_synthesis_type_options, card_css, switch_internal_css))

        with ui.tab_panel(translate_page).style(tab_panel_css):
            page_config_mappings.append(build_translate_tab(config, card_css, switch_internal_css))

        with ui.tab_panel(serial_page).style(tab_panel_css):
            page_config_mappings.append(build_serial_tab(
                config, card_css, switch_internal_css, button_internal_color, button_internal_css))

        with ui.tab_panel(data_analysis_page).style(tab_panel_css):
            page_config_mappings.append(build_data_analysis_tab(config, config_path, echart_css))

        with ui.tab_panel(web_page).style(tab_panel_css):
            page_config_mappings.append(build_web_page_tab(
                config, common, config_path, webui_config_to_dict, card_css, switch_internal_css, button_internal_color, button_internal_css))

        with ui.tab_panel(docs_page).style(tab_panel_css):
            build_docs_tab()

        with ui.tab_panel(about_page).style(tab_panel_css):
            build_about_tab(card_css)

    # 底部操作条：原来是一张 position:fixed 的定宽 grid，永久压住内容——1440 宽遮 46px 一条，
    # 390 宽换行成 114px 高（占视口 15%）还有一半按钮掉出视口。改成右下角可折叠的一条，
    # 平时只留「未保存」角标和一个按钮，要用了再展开。
    def ask_stop():
        confirm.ask('确认停止正在运行的直播程序？', lambda: stop_external_program(config),
                    '弹幕监听、文案播报和虚拟身体会一起停下；正在直播的话，这一下就是断播。')

    def ask_restart():
        confirm.ask('确认重启 webui？', lambda: restart_application(config),
                    '会先停掉正在运行的直播程序，再用当前配置重新拉起 webui；'
                    '没点「保存配置」的改动会全部丢失。')

    ops_open = False

    def switch_ops():
        nonlocal ops_open
        ops_open = not ops_open
        ops_row.set_visibility(ops_open)
        button_ops.set_text('收起' if ops_open else '操作')

    run_badge = None
    run_state_shown = None

    def paint_run_state():
        """底栏常驻一枚运行态徽标：原先点完「一键运行」只有条会自己消失的 toast，按钮形态不变。

        运行态也会被 /sys_cmd 接口从别处改掉，所以只能轮询，不能在按钮回调里刷。
        这里刻意只报状态、不禁用按钮：main.py 自己崩掉时 running_flag 会留在 True，
        禁用「一键运行」就等于把人锁在重启不了的状态。
        """
        nonlocal run_state_shown
        on = bool(state.running_flag)
        if on == run_state_shown:
            return
        run_state_shown = on
        run_badge.set_text('● 直播程序运行中' if on else '○ 直播程序未运行')
        run_badge.style(PILL_CSS.format('#16a34a' if on else '#4b5563'))

    with ui.page_sticky(position="bottom-right", x_offset=12, y_offset=12):
        with ui.column().style("align-items:flex-end;gap:8px;"):
            # 角标做成真按钮：点开「哪些项还没保存、现在是什么值」的清单（story-2 验收标准）
            dirty_badge = ui.button('● 配置已保存', on_click=dirty_guard.open_list).props(
                'flat no-caps dense').style(PILL_CSS.format('#16a34a')).tooltip('点开看哪些项还没保存')
            run_badge = ui.button('○ 直播程序未运行', on_click=lambda: select_tab(OVERVIEW)).props(
                'flat no-caps dense').style(PILL_CSS.format('#4b5563')).tooltip('到总览页看开播就绪度')

            with ui.row().style("flex-wrap:wrap;justify-content:flex-end;gap:6px;") as ops_row:
                button_save = ui.button('保存配置', on_click=lambda: save_config(), color=button_bottom_color).style(button_bottom_css).tooltip("保存webui的配置到本地文件，有些配置保存后需要重启生效")
                button_run = ui.button('一键运行', on_click=lambda: run_external_program(config), color=button_bottom_color).style(button_bottom_css).tooltip("运行main.py")
                # 创建一个按钮，用于停止正在运行的程序
                button_stop = ui.button("停止运行", on_click=ask_stop, color=button_bottom_color).style(button_bottom_css).tooltip("停止运行main.py")
                button_light = ui.button('关灯', on_click=lambda: change_light_status(), color=button_bottom_color).style(button_bottom_css)
                button_restart = ui.button('重启', on_click=ask_restart, color=button_bottom_color).style(button_bottom_css).tooltip("停止运行main.py并重启webui")
                ui.button('回到顶部', icon='keyboard_arrow_up', on_click=lambda: scroll_to_top(), color=button_bottom_color).style(button_bottom_css)
            ops_row.set_visibility(False)

            button_ops = ui.button('操作', icon='settings', on_click=switch_ops, color=button_bottom_color).style(button_bottom_css)

    ui.timer(1.0, paint_run_state)

    # 24 页拆分：把 通用配置 的区块按 sitemap 的分组改挂到各自的新 tab 上。
    # 只搬 DOM 归属，控件与 save_common 留在原文件，保存链路不动
    apply_page_plan(tabs, tab_panels, common_config_panel, tab_panel_css, card_css)

    # 危险操作确认框：NiceGUI 3 没有 ui.confirm，对话框又是元素（关闭只是隐藏），
    # 所以全站建一次放在布局里，各页面调用 confirm.ask 复用同一个
    confirm.build()

    # 全局搜索：索引在每次打开时现建，所以这里只是把对话框和 Ctrl+K 挂上
    config_search.build()

    # 长 tab 的区块索引（大语言模型 那种一二十块的一页，先让人看得见这页有什么）
    add_section_indexes(button_bottom_color)

    # 未保存改动守卫接线：注入拦截脚本 + 角标 + 给页面上的输入控件挂变更记录
    dirty_guard.install()
    dirty_guard.bind_nav(select_tab, button_bottom_color)
    dirty_guard.build_list()
    # 删除的 5 秒撤销托盘：和确认框同理，必须在构建期建好再显隐
    undo.build()
    ui.add_head_html(PAGE_SCRIPTS)
    dirty_guard.bind_label(dirty_badge)
    dirty_guard.watch(force=True)
    # 「增加配置组」这类按钮是运行期现建控件的，定时补挂一次，别漏掉新加的组
    ui.timer(3.0, dirty_guard.watch)

    # 是否启用自动运行功能
    if config.get("webui", "auto_run"):
        logger.info("自动运行 已启用")
        run_external_program(config, type="api")

# 发送心跳包
ui.timer(9 * 60, lambda: common.send_heartbeat())


# 是否启用登录功能（暂不合理）
login_card_css = config.get("webui", "theme", "list", theme_choose, "login_card")
if config.get("login", "enable"):
    build_login(config, common, login_card_css, goto_func_page)
else:
    # 这里原先还建了一张空的 ui.card().style(login_card_css)：login_card 是
    # position:fixed 的全屏渐变，关掉登录后它就变成一张 0 字符的幽灵层，跟 tab_panel 的
    # 渐变重复、还是个随时跟新浮层抢层级的定位元素（走查 audit-17）
    # 这层 column 只是给功能页一个容器。原先带 text-align:center，它会一路继承到
    # Quasar 的折叠区标题上，把「功能管理 / 互动功能」那几条大标题推到条带正中（audit-21）
    with ui.column().style("width:100%;"):
        # 跳转到功能页
        goto_func_page()



ui.run(host=webui_ip, port=webui_port, title=webui_title, favicon="./ui/favicon-64.ico", language="zh-CN", dark=False, reload=False)
# ui.run(host=webui_ip, port=webui_port, title=webui_title, favicon="./ui/favicon-64.ico", language="zh-CN", dark=False, reload=False,
#        ssl_certfile="F:\\FunASR_WS\\cert.pem", ssl_keyfile="F:\\FunASR_WS\\key.pem")