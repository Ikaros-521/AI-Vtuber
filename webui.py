from nicegui import ui, app
import sys, os, json, subprocess, importlib, re, threading, signal
import traceback
import time
import asyncio
from urllib.parse import urljoin
from pathlib import Path

# from functools import partial

from utils.my_log import logger
from utils.config import Config
from utils.common import Common
from utils.audio import Audio

from webui_app.chat_log import chat_log
from webui_app.helpers import AUDIO_SYNTHESIS_TYPE_OPTIONS, common_textarea_handle, textarea_data_change
from webui_app.pages.assistant_anchor import build_assistant_anchor_tab
from webui_app.pages.copywriting import build_copywriting_tab
from webui_app.pages.data_analysis import build_data_analysis_tab
from webui_app.pages.image_recognition import build_image_recognition_tab
from webui_app.pages.llm import build_llm_tab
from webui_app.pages.integral import build_integral_tab
from webui_app.pages.serial import build_serial_tab
from webui_app.pages.static_pages import build_about_tab, build_docs_tab
from webui_app.pages.svc import build_svc_tab
from webui_app.pages.tts import build_tts_tab
from webui_app.pages.talk import build_talk_tab
from webui_app.pages.visual_body import build_visual_body_tab
from webui_app.pages.translate import build_translate_tab
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
user_info = None

# 创建一个全局变量，用于表示程序是否正在运行

# 定义一个标志变量，用来追踪定时器的运行状态

common = None
config = None
audio = None
my_handle = None
config_path = None

# 存储运行的子进程
my_subprocesses = {}

# 本地启动的web服务，用来加载本地的live2d
web_server_port = 12345



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

# 暗夜模式
dark = ui.dark_mode()

"""
通用函数
"""
"""
                                                                                                    
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

def goto_func_page():
    """
    跳转到功能页
    """
    global audio, my_subprocesses, config

    # 过期时间
    expiration_ts = None

    def start_programs():
        """根据配置启动所有程序。
        """
        global config

        for program in config.get("coordination_program"):
            if not program["enable"]:
                continue

            name = program["name"]
            executable = program["executable"]  # Python 解释器的路径
            app_path = program["parameters"][0]  # 假设第一个参数总是 app.py 的路径
            
            # 从 app.py 的路径中提取目录
            app_dir = os.path.dirname(app_path)
            
            # 使用 Python 解释器路径和 app.py 路径构建命令
            cmd = [executable, app_path]

            logger.info(f"运行程序: {name} 位于: {app_dir}")
            
            # 在 app.py 文件所在的目录中启动程序
            process = subprocess.Popen(cmd, cwd=app_dir, shell=True)
            my_subprocesses[name] = process

        name = "main"
        # 用当前解释器启动 main.py，避免走上 PATH 里的 python（可能与 webui 所在的虚拟环境不是同一个）
        process = subprocess.Popen([sys.executable, "main.py"])
        my_subprocesses[name] = process

        logger.info(f"运行程序: {name}")


    def stop_program(name):
        """停止一个正在运行的程序及其所有子进程，兼容 Windows、Linux 和 macOS。

        Args:
            name (str): 要停止的程序的名称。
        """
        if name in my_subprocesses:
            pid = my_subprocesses[name].pid  # 获取进程ID
            logger.info(f"停止程序和它所有的子进程: {name} with PID {pid}")

            try:
                if os.name == 'nt':  # Windows
                    command = ["taskkill", "/F", "/T", "/PID", str(pid)]
                    subprocess.run(command, check=True)
                else:  # POSIX系统，如Linux和macOS
                    os.killpg(os.getpgid(pid), signal.SIGKILL)

                logger.info(f"程序 {name} 和 它所有的子进程都被终止.")
            except Exception as e:
                logger.error(f"终止程序 {name} 失败: {e}")

            del my_subprocesses[name]  # 从进程字典中移除
        else:
            logger.warning(f"程序 {name} 没有在运行.")

    def stop_programs():
        """根据配置停止所有程序。
        """
        global config

        for program in config.get("coordination_program"):
            if not program["enable"]:
                continue
            
            stop_program(program["name"])

        stop_program("main")

    def check_expiration():
        try:
            import requests

            API_URL = urljoin(config.get("login", "ums_api"), '/auth/check_expiration')

            if user_info is None:
                ui.notify(position="top", type="negative", message=f"账号登录信息失效，请重新登录")
                stop_programs()
                return False

            if "accessToken" not in user_info:
                ui.notify(position="top", type="negative", message=f"账号登录信息失效，请重新登录")
                stop_programs()
                return False

            headers = {
                "Authorization": "Bearer " + user_info["accessToken"]
            }

            # 发送 POST 请求
            response = requests.post(API_URL, headers=headers)

            # 判断状态码
            if response.status_code == 200:
                resp_json = response.json()
                if resp_json["code"] == 0 and resp_json["success"]:
                    remainder = common.time_difference_in_seconds(resp_json["data"]["expiration_ts"])
                    logger.info(f'账号可用，过期时间：{resp_json["data"]["expiration_ts"]}')
                    return True
                else:
                    remainder = common.time_difference_in_seconds(resp_json["data"]["expiration_ts"])
                    ui.notify(position="top", type="negative", message=f'账号过期时间：{resp_json["data"]["expiration_ts"]}，已过期：{remainder}秒，请联系管理员续费')
                    logger.error(f'账号过期时间：{resp_json["data"]["expiration_ts"]}，已过期：{remainder}秒，请联系管理员续费')
                    stop_programs()
                    return False
            # elif response.status_code == 401:
            #     ui.notify(position="top", type="negative", message=f"账号已到期，请联系管理员续费")
            #     logger.error(f"账号已到期，请联系管理员续费")
            #     stop_programs()

            #     return False
            else:
                logger.error(f"自检异常！")
                return False
        except Exception as e:
            ui.notify(position="top", type="negative", message=f"错误：{e}")
            logger.error(traceback.format_exc())

            return False

    if config.get("login", "enable"):
        # 十分钟一次的检测
        ui.timer(600.0, lambda: check_expiration())


    """

      =@@^      ,@@@^        .@@@. .....   =@@.      ]@\  ,]]]]]]]]]]]]]]].  .]]]]]]]]]]]]]]]]]]]]    ,]]]]]]]]]]]]]]]]]`    ,/. @@@^ /]  ,@@@.               
      =@@^ .@@@@@@@@@@@@@@^  /@@\]]@@@@@=@@@@@@@@@.  \@@@`=@@@@@@@@@@@@@@@.  .@@@@@@@@@@@@@@@@@@@@    =@@@@@@@@@@@@@@@@@^   .\@@^@@@\@@@`.@@@^                
    @@@@@@@^@@@@@@@@@@@@@@^ =@@@@@^ =@@\]]]/@@]]@@].  =@/`=@@^  .@@@  .@@@.  .@@@^    @@@^    =@@@             ,/@@@@/`     =@@@@@@@@@@@^=@@@@@@@@@.          
    @@@@@@@^@@@^@@\`   =@@^.@@@]]]`=@@^=@@@@@@@@@@@.]]]]` =@@^=@@@@@@@^@@@.  .@@@\]]]]@@@\]]]]/@@@   @@@\/@\..@@@@[./@/@@@. ,[[\@@@@/[[[\@@@`..@@@`           
      =@@^ ,]]]/@@@]]]]]]]].\@@@@@^@@@OO=@@@@@@@@@..@@@@^ =@@^]]]@@@]]`@@@.  .@@@@@@@@@@@@@@@@@@@@   @@@^=@@@^@@@^/@@@\@@@..]@@@@@@@@@@]@@@@^ .@@@.           
      =@@@@=@@@@@@@@@@@@@@@. =@@^ .OO@@@.[[\@@[[[[.  =@@^ =@@^@@@@@@@@^@@@.  .@@@^    @@@^    =@@@   @@@^ .`,]@@@^`,` =@@@. \@/.]@@@^,@@@@@@\ =@@^            
   .@@@@@@@. .@@@`   /@@/  .@@@@@@@,.=@@=@@@@@@@@@^  =@@^,=@@^=@@@@@@@.@@@.  .@@@\]]]]@@@\]]]]/@@@   @@@^]@@@@@@@@@@@]=@@@. ]]]@@@\]]]]] .=@@\@@@.            
    @@\@@^  .@@@\.  /@@@.    =@@^ =@\@@^.../@@.....  =@@@@=@@^=@@[[\@@.@@@.  .@@@@@@@@@@@@@@@@@@@@   @@@@@@/..@@@^,@@@@@@@. O@@@@@@@@@@@  .@@@@@^             
      =@@^   ,\@@@@@@@@.     =@@^/^\@@@`@@@@@@@@@@^  /@@@/@@@`=@@OO@@@.@@@.  =@@@`    @@@^    =@@@   @@@^  \@@@@@^   .=@@@. .@@@@\`/@@/    /@@@\.             
      =@@^    ,/@@@@@@@@]    =@@@@^/@@@@]` =@@.     .\@/.=@@@ =@@[[[[[.@@@.  /@@@     @@@^   ./@@@   @@@^.............=@@@.    O@@@@@@\`,/@@@@@@@@`           
    @@@@@^.@@@@@@@/..[@@@@/. ,@@`/@@@`[@@@@@@@@@@@@.    /@@@^      =@@@@@@. /@@@^     @@@^,@@@@@@^   @@@@@@@@@@@@@@@@@@@@@..\@@@@@[,\@@\@@@@` ,@@@^           
    ,[[[.  .O[[.        [`        ,/         ......       ,^       .[[[[`     ,`      .... [[[[`                      ,[[[. .[.         ,/.     .`

    """
    # 创建一个函数，用于运行外部程序
    def run_external_program(config_path="config.json", type="webui"):

        if state.running_flag:
            if type == "webui":
                ui.notify(position="top", type="warning", message="运行中，请勿重复运行")
            return

        try:
            state.running_flag = True

            # 启动协同程序和主程序
            start_programs()

            if type == "webui":
                ui.notify(position="top", type="positive", message="程序开始运行")
            logger.info("程序开始运行")

            return {"code": 200, "msg": "程序开始运行"}
        except Exception as e:
            if type == "webui":
                ui.notify(position="top", type="negative", message=f"错误：{e}")
            logger.error(traceback.format_exc())
            state.running_flag = False

            return {"code": -1, "msg": f"运行失败！{e}"}


    # 定义一个函数，用于停止正在运行的程序
    def stop_external_program(type="webui"):

        if state.running_flag:
            try:
                # 停止协同程序
                stop_programs()

                state.running_flag = False
                if type == "webui":
                    ui.notify(position="top", type="positive", message="程序已停止")
                logger.info("程序已停止")
            except Exception as e:
                if type == "webui":
                    ui.notify(position="top", type="negative", message=f"停止错误：{e}")
                logger.error(f"停止错误：{e}")

                return {"code": -1, "msg": f"重启失败！{e}"}


    # 开关灯
    def change_light_status(type="webui"):
        if dark.value:
            button_light.set_text("关灯")
        else:
            button_light.set_text("开灯")
        dark.toggle()

    # 重启
    def restart_application(type="webui"):
        try:
            # 先停止运行
            stop_external_program(type)

            logger.info(f"重启webui")
            if type == "webui":
                ui.notify(position="top", type="ongoing", message=f"重启中...")
            python = sys.executable
            os.execl(python, python, *sys.argv)  # Start a new instance of the application
        except Exception as e:
            logger.error(traceback.format_exc())
            return {"code": -1, "msg": f"重启失败！{e}"}
        
    # 恢复出厂配置
    def factory(src_path='config.json.bak', dst_path='config.json', type="webui"):
        # src_path = 'config.json.bak'
        # dst_path = 'config.json'

        try:
            with open(src_path, 'r', encoding="utf-8") as source:
                with open(dst_path, 'w', encoding="utf-8") as destination:
                    destination.write(source.read())
            logger.info("恢复出厂配置成功！")
            if type == "webui":
                ui.notify(position="top", type="positive", message=f"恢复出厂配置成功！")
            
            # 重启
            restart_application()

            return {"code": 200, "msg": "恢复出厂配置成功！"}
        except Exception as e:
            logger.error(f"恢复出厂配置失败！\n{e}")
            if type == "webui":
                ui.notify(position="top", type="negative", message=f"恢复出厂配置失败！\n{e}")
            
            return {"code": -1, "msg": f"恢复出厂配置失败！\n{e}"}
    
    
        
    # GPT-SoVITS加载模型
    # 页面滑到顶部
    def scroll_to_top():
        # 这段JavaScript代码将页面滚动到顶部
        ui.run_javascript("window.scrollTo(0, 0);")   

    """

                  /@@@@@@@@          @@@@@@@@@@@@@@@].      =@@@@@@@       
                 =@@@@@@@@@^         @@@@@@@@@@@@@@@@@@`    =@@@@@@@       
                ,@@@@@@@@@@@`        @@@@@@@@@@@@@@@@@@@^   =@@@@@@@       
               .@@@@@@\@@@@@@.       @@@@@@@^   .\@@@@@@\   =@@@@@@@       
               /@@@@@/ \@@@@@\       @@@@@@@^    =@@@@@@@   =@@@@@@@       
              =@@@@@@. .@@@@@@^      @@@@@@@\]]]@@@@@@@@^   =@@@@@@@       
             ,@@@@@@^   =@@@@@@`     @@@@@@@@@@@@@@@@@@/    =@@@@@@@       
            .@@@@@@@@@@@@@@@@@@@.    @@@@@@@@@@@@@@@@/`     =@@@@@@@       
            /@@@@@@@@@@@@@@@@@@@\    @@@@@@@^               =@@@@@@@       
           =@@@@@@@@@@@@@@@@@@@@@^   @@@@@@@^               =@@@@@@@       
          ,@@@@@@@.       ,@@@@@@@`  @@@@@@@^               =@@@@@@@       
          @@@@@@@^         =@@@@@@@. @@@@@@@^               =@@@@@@@   

    """
    
    

    from starlette.requests import Request
    from utils.models import SendMessage, CommonResult, SysCmdMessage, SetConfigMessage

    """
    配置config

        config_path (str): 配置文件路径
        data (dict): 传入的json

    return:
        {"code": 200, "message": "成功"}
    """
    @app.post('/set_config')
    async def set_config(msg: SetConfigMessage):
        global config

        try:
            data_json = msg.dict()
            logger.info(f'set_config接口 收到数据：{data_json}')

            config_data = None

            try:
                with open(data_json["config_path"], 'r', encoding="utf-8") as config_file:
                    config_data = json.load(config_file)
            except Exception as e:
                logger.error(f"无法读取配置文件！\n{e}")
                return CommonResult(code=-1, message=f"无法读取配置文件！{e}")
            
            # 合并字典
            config_data.update(data_json["data"])

            # 写入配置到配置文件
            try:
                with open(data_json["config_path"], 'w', encoding="utf-8") as config_file:
                    json.dump(config_data, config_file, indent=2, ensure_ascii=False)
                    config_file.flush()  # 刷新缓冲区，确保写入立即生效

                logger.info("配置数据已成功写入文件！")

                return CommonResult(code=200, message="配置数据已成功写入文件！")
            except Exception as e:
                logger.error(f"无法写入配置文件！\n{str(e)}")
                return CommonResult(code=-1, message=f"无法写入配置文件！{e}")
        except Exception as e:
            logger.error(traceback.format_exc())
            return CommonResult(code=-1, message=f"{data_json['type']}执行失败！{e}")

    """
    系统命令
        type 命令类型（run/stop/restart/factory）
        data 传入的json

    data_json = {
        "type": "命令名",
        "data": {
            "key": "value"
        }
    }

    return:
        {"code": 200, "message": "成功"}
        {"code": -1, "message": "失败"}
    """
    @app.post('/sys_cmd')
    async def sys_cmd(msg: SysCmdMessage):
        try:
            data_json = msg.dict()
            logger.info(f'sys_cmd接口 收到数据：{data_json}')
            logger.info(f"开始执行 {data_json['type']}命令...")

            resp_json = {}

            if data_json['type'] == 'run':
                """
                {
                    "type": "run",
                    "data": {
                        "config_path": "config.json"
                    }
                }
                """
                # 运行
                resp_json = run_external_program(data_json['data']['config_path'], type="api")
            elif data_json['type'] =='stop':
                """
                {
                    "type": "stop",
                    "data": {
                        "config_path": "config.json"
                    }
                }
                """
                # 停止
                resp_json = stop_external_program(type="api")
            elif data_json['type'] =='restart':
                """
                {
                    "type": "restart",
                    "api_type": "webui",
                    "data": {
                        "config_path": "config.json"
                    }
                }
                """
                # 重启
                resp_json = restart_application(type=data_json['api_type'])
            elif data_json['type'] =='factory':
                """
                {
                    "type": "factory",
                    "api_type": "webui",
                    "data": {
                        "src_path": "config.json.bak",
                        "dst_path": "config.json"
                    }
                }
                """
                # 恢复出厂
                resp_json = factory(data_json['data']['src_path'], data_json['data']['dst_path'], type="api")

            return resp_json
        except Exception as e:
            logger.error(traceback.format_exc())
            return CommonResult(code=-1, message=f"{data_json['type']}执行失败！{e}")

    """
    发送数据
        type 数据类型（comment/gift/entrance/reread/tuning/...）
        key  根据数据类型自行适配

    data_json = {
        "type": "数据类型",
        "key": "value"
    }

    return:
        {"code": 200, "message": "成功"}
        {"code": -1, "message": "失败"}
    """
    @app.post('/send')
    async def send(msg: SendMessage):
        global config

        try:
            data_json = msg.dict()
            logger.info(f'WEBUI API send接口收到数据：{data_json}')

            main_api_ip = "127.0.0.1" if config.get("api_ip") == "0.0.0.0" else config.get("api_ip")
            resp_json = await common.send_async_request(f'http://{main_api_ip}:{config.get("api_port")}/send', "POST", data_json)

            return resp_json
        except Exception as e:
            logger.error(traceback.format_exc())
            return CommonResult(code=-1, message=f"发送数据失败！{e}")



    """
    数据回调
        data 传入的json

    data_json = {
        "type": "数据类型（llm）",
        "data": {
            "type": "LLM类型",
            "username": "用户名",
            "content_type": "内容的类型（question/answer）",
            "content": "回复内容",
            "timestamp": "时间戳"
        }
    }

    return:
        {"code": 200, "message": "成功"}
        {"code": -1, "message": "失败"}
    """
    @app.post('/callback')
    async def callback(request: Request):
        try:
            data_json = await request.json()
            logger.info(f'WEBUI API callback接口收到数据：{data_json}')

            chat_log.add(data_json)

            return {"code": 200, "message": "成功"}
        except Exception as e:
            logger.error(traceback.format_exc())
            return CommonResult(code=-1, message=f"失败！{e}")


    """
    TTS合成，获取合成的音频文件路径
        data 传入的json

    例如：
    data_json = {
        "type": "reread",
        "tts_type": "gpt_sovits",
        "data": {
            "type": "api",
            "api_ip_port": "http://127.0.0.1:9880",
            "ref_audio_path": "F:\\GPT-SoVITS\\raws\\ikaros\\21.wav",
            "prompt_text": "マスター、どうりょくろか、いいえ、なんでもありません",
            "prompt_language": "日文",
            "language": "自动识别",
            "cut": "凑四句一切",
            "gpt_model_path": "F:\\GPT-SoVITS\\GPT_weights\\ikaros-e15.ckpt",
            "sovits_model_path": "F:\\GPT-SoVITS\\SoVITS_weights\\ikaros_e8_s280.pth",
            "webtts": {
                "api_ip_port": "http://127.0.0.1:8080",
                "spk": "sanyueqi",
                "lang": "zh",
                "speed": "1.0",
                "emotion": "正常"
            }
        },
        "username": "主人",
        "content": "你好，这就是需要合成的文本内容"
    }

    return:
        {
            "code": 200,
            "message": "成功",
            "data": {
                "type": "reread",
                "tts_type": "gpt_sovits",
                "data": {
                    "type": "api",
                    "api_ip_port": "http://127.0.0.1:9880",
                    "ref_audio_path": "F:\\\\GPT-SoVITS\\\\raws\\\\ikaros\\\\21.wav",
                    "prompt_text": "マスター、どうりょくろか、いいえ、なんでもありません",
                    "prompt_language": "日文",
                    "language": "自动识别",
                    "cut": "凑四句一切",
                    "gpt_model_path": "F:\\GPT-SoVITS\\GPT_weights\\ikaros-e15.ckpt",
                    "sovits_model_path": "F:\\GPT-SoVITS\\SoVITS_weights\\ikaros_e8_s280.pth",
                    "webtts": {
                        "api_ip_port": "http://127.0.0.1:8080",
                        "spk": "sanyueqi",
                        "lang": "zh",
                        "speed": "1.0",
                        "emotion": "正常"
                    }
                },
                "username": "主人",
                "content": "你好，这就是需要合成的文本内容",
                "result": {
                    "code": 200,
                    "msg": "合成成功",
                    "audio_path": "E:\\GitHub_pro\\AI-Vtuber\\out\\gpt_sovits_4.wav"
                }
            }
        }

        {"code": -1, "message": "失败"}
    """
    @app.post('/tts')
    async def tts(request: Request):
        try:
            data_json = await request.json()
            logger.info(f'WEBUI API tts接口收到数据：{data_json}')

            resp_json = await audio.tts_handle(data_json)

            return {"code": 200, "message": "成功", "data": resp_json}
        except Exception as e:
            logger.error(traceback.format_exc())
            return CommonResult(code=-1, message=f"失败！{e}")


    """
    LLM推理，获取推理结果
        data 传入的json

    例如：type就是聊天类型实际对应的值
    data_json = {
        "type": "chatgpt",
        "username": "用户名",
        "content": "你好"
    }

    return:
        {
            "code": 200,
            "message": "成功",
            "data": {
                "content": "你好，这是LLM回复的内容"
            }
        }

        {"code": -1, "message": "失败"}
    """
    @app.post('/llm')
    async def llm(request: Request):
        try:
            data_json = await request.json()
            logger.info(f'WEBUI API llm接口 收到数据：{data_json}')

            main_api_ip = "127.0.0.1" if config.get("api_ip") == "0.0.0.0" else config.get("api_ip")
            resp_json = await common.send_async_request(f'http://{main_api_ip}:{config.get("api_port")}/llm', "POST", data_json, "json", timeout=60)
            if resp_json:
                return resp_json
            
            return CommonResult(code=-1, message="失败！")
        except Exception as e:
            logger.error(traceback.format_exc())
            return CommonResult(code=-1, message=f"失败！{e}")

    # 获取系统信息接口
    @app.get("/get_sys_info")
    async def get_sys_info():
        try:
            # logger.info(f'WEBUI API get_sys_info接口 收到请求')

            main_api_ip = "127.0.0.1" if config.get("api_ip") == "0.0.0.0" else config.get("api_ip")
            resp_json = await common.send_async_request(f'http://{main_api_ip}:{config.get("api_port")}/get_sys_info', "GET", None, "json", timeout=60)
            if resp_json:
                return resp_json
            return CommonResult(code=-1, message="失败！")
        except Exception as e:
            logger.error(f"get_sys_info处理失败！{e}")
            return CommonResult(code=-1, message=f"get_sys_info处理失败！{e}")


    
        
    """
                                                     ./@\]                    
                   ,@@@@\*                             \@@^ ,]]]              
                      [[[*                      /@@]@@@@@/[[\@@@@/            
                        ]]@@@@@@\              /@@^  @@@^]]`[[                
                ]]@@@@@@@[[*                   ,[`  /@@\@@@@@@@@@@@@@@^       
             [[[[[`   @@@/                 \@@@@[[[\@@^ =@@/                  
              .\@@\* *@@@`                           [\@@@@@@\`               
                 ,@@\=@@@                         ,]@@@/`  ,\@@@@*            
                   ,@@@@`                     ,[[[[`  =@@@   ]]/O             
                   /@@@@@`                    ]]]@@@@@@@@@/[[[[[`             
                ,@@@@[ \@@@\`                      ./@@@@@@@]                 
          ,]/@@@@/`      \@@@@@\]]               ,@@@/,@@^ \@@@\]             
                           ,@@@@@@@@/[*       ,/@@/*  /@@^   [@@@@@@@\*       
                                                      ,@@^                    
                                                              
    """

    # -增加
    def schedule_add():
        data_len = len(schedule_var)
        tmp_config = {
            "enable": False,
            "time_min": 60,
            "time_max": 120,
            "copy": []
        }

        with schedule_config_card.style(card_css):
            with ui.row():
                schedule_var[str(data_len)] = ui.switch(text=f"启用任务#{int(data_len / 4) + 1}", value=tmp_config["enable"]).style(switch_internal_css)
                schedule_var[str(data_len + 1)] = ui.input(label=f"最小循环周期#{int(data_len / 4) + 1}", value=tmp_config["time_min"], placeholder='定时任务循环的周期最小时长（秒），即每间隔这个周期就会执行一次').style("width:100px;")
                schedule_var[str(data_len + 2)] = ui.input(label=f"最大循环周期#{int(data_len / 4) + 1}", value=tmp_config["time_max"], placeholder='定时任务循环的周期最大时长（秒），即每间隔这个周期就会执行一次').style("width:100px;")
                schedule_var[str(data_len + 3)] = ui.textarea(label=f"文案列表#{int(data_len / 4) + 1}", value=textarea_data_change(tmp_config["copy"]), placeholder='存放文案的列表，通过空格或换行分割，通过{变量}来替换关键数据，可修改源码自定义功能').style("width:500px;")


    # -删除
    def schedule_del(index):
        try:
            schedule_config_card.remove(int(index) - 1)
            # 删除操作
            keys_to_delete = [str(4 * (int(index) - 1) + i) for i in range(4)]
            for key in keys_to_delete:
                if key in schedule_var:
                    del schedule_var[key]

            # 重新编号剩余的键
            updates = {}
            for key in sorted(schedule_var.keys(), key=int):
                new_key = str(int(key) - 4 if int(key) > int(keys_to_delete[-1]) else key)
                updates[new_key] = schedule_var[key]

            # 应用更新
            schedule_var.clear()
            schedule_var.update(updates)
        except Exception as e:
            ui.notify(position="top", type="negative", message=f"错误，索引值配置有误：{e}")
            logger.error(traceback.format_exc())



    """
    动态文案
    """
    # 动态文案-增加
    def trends_copywriting_add():
        data_len = len(trends_copywriting_copywriting_var)
        tmp_config = {
            "folder_path": "",
            "prompt_change_enable": False,
            "prompt_change_content": ""
        }

        with trends_copywriting_config_card.style(card_css):
            with ui.row():
                trends_copywriting_copywriting_var[str(data_len)] = ui.input(label=f"文案路径#{int(data_len / 3) + 1}", value=tmp_config["folder_path"], placeholder='文案文件存储的文件夹路径').style("width:200px;")
                trends_copywriting_copywriting_var[str(data_len + 1)] = ui.switch(text=f"提示词转换#{int(data_len / 3) + 1}", value=tmp_config["prompt_change_enable"])
                trends_copywriting_copywriting_var[str(data_len + 2)] = ui.input(label=f"提示词转换内容#{int(data_len / 3) + 1}", value=tmp_config["prompt_change_content"], placeholder='使用此提示词内容对文案内容进行转换后再进行合成，使用的LLM为聊天类型配置').style("width:500px;")


    # 动态文案-删除
    def trends_copywriting_del(index):
        try:
            trends_copywriting_config_card.remove(int(index) - 1)
            # 删除操作
            keys_to_delete = [str(3 * (int(index) - 1) + i) for i in range(3)]
            for key in keys_to_delete:
                if key in trends_copywriting_copywriting_var:
                    del trends_copywriting_copywriting_var[key]

            # 重新编号剩余的键
            updates = {}
            for key in sorted(trends_copywriting_copywriting_var.keys(), key=int):
                new_key = str(int(key) - 3 if int(key) > int(keys_to_delete[-1]) else key)
                updates[new_key] = trends_copywriting_copywriting_var[key]

            # 应用更新
            trends_copywriting_copywriting_var.clear()
            trends_copywriting_copywriting_var.update(updates)
        except Exception as e:
            ui.notify(position="top", type="negative", message=f"错误，索引值配置有误：{e}")
            logger.error(traceback.format_exc())

    
    """
    联动程序
    """
    # 联动程序-增加
    def coordination_program_add():
        data_len = len(coordination_program_var)
        tmp_config = {
            "enable": True,
            "name": "",
            "executable": "",
            "parameters": []
        }

        with coordination_program_config_card.style(card_css):
            with ui.row():
                coordination_program_var[str(data_len)] = ui.switch(f'启用#{int(data_len / 4) + 1}', value=tmp_config["enable"]).style(switch_internal_css)
                coordination_program_var[str(data_len + 1)] = ui.input(label=f"程序名#{int(data_len / 4) + 1}", value=tmp_config["name"], placeholder='给你的程序取个名字，别整特殊符号！').style("width:200px;")
                coordination_program_var[str(data_len + 2)] = ui.input(label=f"可执行程序#{int(data_len / 4) + 1}", value=tmp_config["executable"], placeholder='可执行程序的路径，最好是绝对路径，如python的程序').style("width:400px;")
                coordination_program_var[str(data_len + 3)] = ui.textarea(label=f'参数#{int(data_len / 4) + 1}', value=textarea_data_change(tmp_config["parameters"]), placeholder='参数，可以传入多个参数，换行分隔。如启动的程序的路径，命令携带的传参等').style("width:500px;")


    # 联动程序-删除
    def coordination_program_del(index):
        try:
            coordination_program_config_card.remove(int(index) - 1)
            # 删除操作
            keys_to_delete = [str(4 * (int(index) - 1) + i) for i in range(4)]
            for key in keys_to_delete:
                if key in coordination_program_var:
                    del coordination_program_var[key]

            # 重新编号剩余的键
            updates = {}
            for key in sorted(coordination_program_var.keys(), key=int):
                new_key = str(int(key) - 4 if int(key) > int(keys_to_delete[-1]) else key)
                updates[new_key] = coordination_program_var[key]

            # 应用更新
            coordination_program_var.clear()
            coordination_program_var.update(updates)
        except Exception as e:
            ui.notify(position="top", type="negative", message=f"错误，索引值配置有误：{e}")
            logger.error(traceback.format_exc())


    """
    按键/文案映射
    """
    def key_mapping_add():
        data_len = len(key_mapping_config_var)
        tmp_config = {
            "keywords": [],
            "gift": [],
            "keys": [],
            "similarity": 1,
            "copywriting": [],
            "local_audio": [],
            "img_path": []
        }

        with key_mapping_config_card.style(card_css):
            with ui.row():
                num = int(data_len / 9) + 1
                key_mapping_config_var[str(data_len)] = ui.textarea(label=f"关键词#{num}", value=textarea_data_change(tmp_config["keywords"]), placeholder='此处输入触发的关键词，多个请以换行分隔').style("width:100px;")
                key_mapping_config_var[str(data_len + 1)] = ui.textarea(label=f"礼物#{num}", value=textarea_data_change(tmp_config["gift"]), placeholder='此处输入触发的礼物名，多个请以换行分隔').style("width:100px;")
                key_mapping_config_var[str(data_len + 2)] = ui.textarea(label=f"按键#{num}", value=textarea_data_change(tmp_config["keys"]), placeholder='此处输入你要映射的按键，多个按键请以换行分隔（按键名参考pyautogui规则）').style("width:100px;")
                key_mapping_config_var[str(data_len + 3)] = ui.input(label=f"相似度#{num}", value=tmp_config["similarity"], placeholder='关键词与用户输入的相似度，默认1即100%').style("width:50px;")
                key_mapping_config_var[str(data_len + 4)] = ui.textarea(label=f"文案#{num}", value=textarea_data_change(tmp_config["copywriting"]), placeholder='此处输入触发后合成的文案内容，多个请以换行分隔').style("width:300px;")
                key_mapping_config_var[str(data_len + 5)] = ui.textarea(label=f"文案#{num}", value=textarea_data_change(tmp_config["copywriting"]), placeholder='此处输入触发后合成的文案内容，多个请以换行分隔').style("width:300px;")
                key_mapping_config_var[str(data_len + 6)] = ui.input(label=f"串口名#{num}", value=tmp_config["serial_name"], placeholder='例如：COM1').style("width:100px;").tooltip('串口页配置的串口名，例如：COM1')
                key_mapping_config_var[str(data_len + 7)] = ui.textarea(label=f"串口发送内容#{num}", value=textarea_data_change(tmp_config["serial_send_data"]), placeholder='多个请以换行分隔，ASCII例如：open led\nHEX例如（2个字符的十六进制字符）：313233').style("width:300px;").tooltip('此处输入发送到串口的数据内容，数据类型根据串口页设置决定，多个请以换行分隔')
                key_mapping_config_var[str(data_len + 8)] = ui.textarea(label=f"串口发送内容#{num}", value=textarea_data_change(tmp_config["serial_send_data"]), placeholder='多个请以换行分隔，ASCII例如：open led\nHEX例如（2个字符的十六进制字符）：313233').style("width:300px;").tooltip('此处输入发送到串口的数据内容，数据类型根据串口页设置决定，多个请以换行分隔')
                          
    
    def key_mapping_del(index):
        try:
            num = 9
            key_mapping_config_card.remove(int(index) - 1)
            # 删除操作
            keys_to_delete = [str(num * (int(index) - 1) + i) for i in range(num)]
            for key in keys_to_delete:
                if key in key_mapping_config_var:
                    del key_mapping_config_var[key]

            # 重新编号剩余的键
            updates = {}
            for key in sorted(key_mapping_config_var.keys(), key=int):
                new_key = str(int(key) - num if int(key) > int(keys_to_delete[-1]) else key)
                updates[new_key] = key_mapping_config_var[key]

            # 应用更新
            key_mapping_config_var.clear()
            key_mapping_config_var.update(updates)
        except Exception as e:
            ui.notify(position="top", type="negative", message=f"错误，索引值配置有误：{e}")
            logger.error(traceback.format_exc())


    """
    自定义命令
    """
    
    # 自定义命令-增加
    def custom_cmd_add():
        data_len = len(custom_cmd_config_var)

        tmp_config = {
            "keywords": [],
            "similarity": 1,
            "api_url": "",
            "api_type": "",
            "resp_data_type": "",
            "data_analysis": "",
            "resp_template": ""
        }

        with custom_cmd_config_card.style(card_css):
            with ui.row():
                custom_cmd_config_var[str(data_len)] = ui.textarea(label=f"关键词#{int(data_len / 7) + 1}", value=textarea_data_change(tmp_config["keywords"]), placeholder='此处输入触发的关键词，多个请以换行分隔').style("width:200px;")
                custom_cmd_config_var[str(data_len + 1)] = ui.input(label=f"相似度#{int(data_len / 7) + 1}", value=tmp_config["similarity"], placeholder='关键词与用户输入的相似度，默认1即100%').style("width:100px;")
                custom_cmd_config_var[str(data_len + 2)] = ui.textarea(label=f"API URL#{int(data_len / 7) + 1}", value=tmp_config["api_url"], placeholder='发送HTTP请求的API链接', validation={'请输入正确格式的URL': lambda value: common.is_url_check(value),}).style("width:300px;")
                custom_cmd_config_var[str(data_len + 3)] = ui.select(label=f"API类型#{int(data_len / 7) + 1}", value=tmp_config["api_type"], options={"GET": "GET"}).style("width:100px;")
                custom_cmd_config_var[str(data_len + 4)] = ui.select(label=f"请求返回数据类型#{int(data_len / 7) + 1}", value=tmp_config["resp_data_type"], options={"json": "json", "content": "content"}).style("width:150px;")
                custom_cmd_config_var[str(data_len + 5)] = ui.textarea(label=f"数据解析（eval执行）#{int(data_len / 7) + 1}", value=tmp_config["data_analysis"], placeholder='数据解析，请不要随意修改resp变量，会被用于最后返回数据内容的解析').style("width:200px;")
                custom_cmd_config_var[str(data_len + 6)] = ui.textarea(label=f"返回内容模板#{int(data_len / 7) + 1}", value=tmp_config["resp_template"], placeholder='请不要随意删除data变量，支持动态变量，最终会合并成完成内容进行音频合成').style("width:300px;")


    # 自定义命令-删除
    def custom_cmd_del(index):
        try:
            custom_cmd_config_card.remove(int(index) - 1)
            # 删除操作
            keys_to_delete = [str(7 * (int(index) - 1) + i) for i in range(7)]
            for key in keys_to_delete:
                if key in custom_cmd_config_var:
                    del custom_cmd_config_var[key]

            # 重新编号剩余的键
            updates = {}
            for key in sorted(custom_cmd_config_var.keys(), key=int):
                new_key = str(int(key) - 7 if int(key) > int(keys_to_delete[-1]) else key)
                updates[new_key] = custom_cmd_config_var[key]

            # 应用更新
            custom_cmd_config_var.clear()
            custom_cmd_config_var.update(updates)
        except Exception as e:
            ui.notify(position="top", type="negative", message=f"错误，索引值配置有误：{e}")
            logger.error(traceback.format_exc())

    # -增加
    def webui_local_dir_to_endpoint_add():
        data_len = len(webui_local_dir_to_endpoint_config_var)
        tmp_config = {
            "url_path": "",
            "local_dir": "",
        }

        with webui_local_dir_to_endpoint_config_card.style(card_css):
            with ui.row():
                webui_local_dir_to_endpoint_config_var[str(data_len)] = ui.input(label=f"URL路径#{int(data_len / 2) + 1}", value=tmp_config["url_path"], placeholder='以斜杠（"/"）开始的字符串，它标识了应该为客户端提供文件的URL路径').style("width:300px;")
                webui_local_dir_to_endpoint_config_var[str(data_len + 1)] = ui.input(label=f"本地文件夹路径#{int(data_len / 2) + 1}", value=tmp_config["local_dir"], placeholder='本地文件夹路径，建议相对路径，最好是项目内部的路径').style("width:300px;")


    # -删除
    def webui_local_dir_to_endpoint_del(index):
        try:
            webui_local_dir_to_endpoint_config_card.remove(int(index) - 1)
            # 删除操作
            keys_to_delete = [str(2 * (int(index) - 1) + i) for i in range(2)]
            for key in keys_to_delete:
                if key in webui_local_dir_to_endpoint_config_var:
                    del webui_local_dir_to_endpoint_config_var[key]

            # 重新编号剩余的键
            updates = {}
            for key in sorted(webui_local_dir_to_endpoint_config_var.keys(), key=int):
                new_key = str(int(key) - 2 if int(key) > int(keys_to_delete[-1]) else key)
                updates[new_key] = webui_local_dir_to_endpoint_config_var[key]

            # 应用更新
            webui_local_dir_to_endpoint_config_var.clear()
            webui_local_dir_to_endpoint_config_var.update(updates)
        except Exception as e:
            ui.notify(position="top", type="negative", message=f"错误，索引值配置有误：{e}")
            logger.error(traceback.format_exc())


    # 配置模板保存
    def config_template_save(file_path: str):
        try:
            with open(config_path, 'r', encoding="utf-8") as config_file:
                config_data = json.load(config_file)

            config_data = webui_config_to_dict(config_data)

            # 将JSON数据保存到文件中
            with open(file_path, "w", encoding="utf-8") as file:
                json.dump(config_data, file, indent=2, ensure_ascii=False)
                file.flush()  # 刷新缓冲区，确保写入立即生效

            logger.info("配置模板保存成功！")
            ui.notify(position="top", type="positive", message=f"配置模板保存成功！")

            return True
        except Exception as e:
            logger.error(f"配置模板保存失败！\n{e}")
            ui.notify(position="top", type="negative", message=f"配置模板保存失败！{e}")
            return False


    # 配置模板加载
    def config_template_load(file_path: str):
        try:
            with open(file_path, 'r', encoding="utf-8") as config_file:
                config_data = json.load(config_file)

            # 将JSON数据保存到文件中
            with open(config_path, "w", encoding="utf-8") as file:
                json.dump(config_data, file, indent=2, ensure_ascii=False)
                file.flush()  # 刷新缓冲区，确保写入立即生效

            logger.info("配置模板加载成功！重启后读取！想反悔就直接保存下当前配置，然后再重启！！！")
            ui.notify(position="top", type="positive", message=f"配置模板加载成功！重启后读取！想反悔就直接保存下当前配置，然后再重启！！！")
            
            return True
        except Exception as e:
            logger.error(f"配置模板读取失败！\n{e}")
            ui.notify(position="top", type="negative", message=f"配置模板读取失败！{e}")
            return False


    """
    配置操作
    """
    # 配置检查
    def check_config():
        try:
            # 通用配置 页面 配置正确性校验
            if select_platform.value == 'bilibili2' and select_bilibili_login_type.value == 'cookie' and input_bilibili_cookie.value == '':
                ui.notify(position="top", type="warning", message="请先前往 通用配置-哔哩哔哩，填写B站cookie")
                return False
            elif select_platform.value == 'bilibili2' and select_bilibili_login_type.value == 'open_live' and \
                (input_bilibili_open_live_ACCESS_KEY_ID.value == '' or input_bilibili_open_live_ACCESS_KEY_SECRET.value == '' or \
                input_bilibili_open_live_APP_ID.value == '' or input_bilibili_open_live_ROOM_OWNER_AUTH_CODE.value == ''):
                ui.notify(position="top", type="warning", message="请先前往 通用配置-哔哩哔哩，填写开放平台配置")
                return False


            """
            针对配置情况进行提示
            """
            tip_config = f'平台：{platform_options[select_platform.value]} | ' +\
                f'大语言模型：{chat_type_options[select_chat_type.value]} | ' +\
                f'语音合成：{audio_synthesis_type_options[select_audio_synthesis_type.value]} | ' +\
                f'虚拟身体：{visual_body_options[select_visual_body.value]}'
            ui.notify(position="top", type="info", message=tip_config)

            # 检测平台配置，进行提示
            if select_platform.value == "dy":
                ui.notify(position="top", type="warning", message="对接抖音平台时，请先开启抖音弹幕监听程序！直播间号不需要填写")
            elif select_platform.value == "bilibili":
                ui.notify(position="top", type="info", message="哔哩哔哩1 监听不是很稳定，推荐使用 哔哩哔哩2")
            elif select_platform.value == "bilibili2":
                if select_bilibili_login_type.value == "不登录":
                    ui.notify(position="top", type="warning", message="哔哩哔哩2 在不登录的情况下，无法获取用户完整的用户名")

            if select_visual_body.value == "metahuman_stream":
                ui.notify(position="top", type="warning", message="对接metahuman_stream时，语音合成由metahuman_stream托管，不受AI Vtuber控制，请自行参考官方文档对接TTS")

            if config.get("webui", "show_card", "common_config", "local_qa"):
                if not common.is_json_convertible(textarea_local_qa_text_json_file_content.value):
                    ui.notify(position="top", type="negative", message="本地问答json数据格式不正确，请检查JSON语法！")
                    return False

            return True
        except Exception as e:
            ui.notify(position="top", type="negative", message=f"配置错误：{e}")
            return False

    """
    
.................................................................................................................................................................
.................................................................................................................................................................
.................................................................................................................................................................
.................................................................................................................................................................
.............................................................................................................:**.................................................
........+++..........-++:....:++:...*##############:%%%%%%%%%#.....%%%%%%%%%%%%%%%%%%%%%%%.....%@#...........-@%..........+%%%%%%%%%%%%%+-----------:............
........%@#..........=@@=....-@@=....::::%#:=@+::::.........%%.....%%.....%%.....%#.....%%......+@@*..#%%%%%%%@@%%%%%%%%....=@#.....%@-.*%@#######%@=............
........%@#..........=@@=....-@@=........%*.-@+.............%%.....%@%%%%%@@%%%%%@@%%%%%@%........%%:........-@%............=@#.....%@-..#@-......#@-............
........%@#..........=@@=....-@@=....%%%%@@%%@%%%%=.........%%.....::........#%=........::...................=@%:...........=@%#####%@-..=@=.....-%%.............
........%@#..........=@@=....-@@=....%%..%*.-@+.=@=.........%%...%%%%%%%%%%%%@@%%%%%%%%%%%%*.:-----..#%%%%%%%%%%%%%%%%%@-...=@#-----%@-..:%#.....*@=.............
........%@#..........=@@=....-@@=....%%.:%*.-@+.=@=.-%@@@@@@@%...............%@=.............+##%@%.....=%%+:..=@#....#%:...=@#.....%@-...#@-....%%..............
........%@#..........=@@=....-@@=....%%.+@=.-@+.=@=.=@+.....##.......@%***************#@+.......=@%....-..:*%#.=@#....+*....=@#-----%@-...-%#...#@=..............
........%@#..........=@@=....-@@=....%%+@#...*%%%@=.=@+..............@#===============*@+.......=@%...-#@%*:...+@*..........=@%*****%@-....*@=.=%*...............
........#@%..........+@@:....-@@=....%%-*.......=@=.=@+..............@#-::::::::::::::+@+.......=@%......:**...*@+..........=@#.....%@-.....%@#%%................
........*@@=........:%@#.....-@@=....%@%%%%%%%%%%@=.=@+......-*:.....@%%%%%%%%%%%%%%%%%@+.......=@%.:%@@@@@@@@@@@@@@@@@@%...=@#.....%@++*=...%@#.................
.........*@@%-.....*%@%......-@@=....%%.........=@=.-@+......+@=.....@*...............=@+.......=@%..:........%@*.........+#%@%%%@@@@@#+-..:%@%@%................
..........:%%@@@@@@%%-.......-@@=....%%.........=@=.-@+......%@-.....@%%%%%%%%%%%%%%%%%@+.......=@%#@%:....:#@%*%@%*......+*=:......%@-...#@%..:%@*..............
.....................................%@@@@@@@@@@@@=.:%@#+==+%@%.....:@#...............=@*.......#@@#-..:+%@@%-....=#@@#-............%@--%@%-.....+%@%=...........
.....................................%%.........=%=...=*****+:..-***************************-...-+...#@%#+:..........-#%:...........%@=%#:.........+#............
.................................................................................................................................................................
.................................................................................................................................................................
.................................................................................................................................................................
.................................................................................................................................................................

    """

    # 读取webui配置到dict变量
    def webui_config_to_dict(config_data):
        """读取webui配置到dict变量

        Args:
            config_data (dict): 从本地配置文件读取的dict数据
        """

        # 类型处理函数
        def handle_int(value):
            if value.value == '' or value.value is None:
                return 0
            return int(value.value)

        def handle_float(value):
            if value.value == '' or value.value is None:
                return 0
            return round(float(value.value), 2)

        def handle_string(value):
            return str(value.value)

        def handle_bool(value):
            return bool(value.value)

        def handle_textarea(value):
            return common_textarea_handle(value.value)

        # 处理器映射
        type_handlers = {
            'int': handle_int,
            'float': handle_float,
            'str': handle_string,
            'bool': handle_bool,
            'textarea': handle_textarea,
        }

        def update_nested_dict(target, keys, value):
            """递归更新嵌套字典"""
            if len(keys) == 1:
                target[keys[0]] = value
                return
            if keys[0] not in target:
                target[keys[0]] = {}
            update_nested_dict(target[keys[0]], keys[1:], value)

        def process_config_mapping(config_data, mapping, show_card_check=None):
            """处理配置映射，支持不同层级的嵌套"""
            def recurse_mapping(current_mapping, current_path=[]):
                for key, value in current_mapping.items():
                    new_path = current_path + [key]
                    if isinstance(value, dict):
                        recurse_mapping(value, new_path)
                    else:
                        component, type_name = value
                        handler = type_handlers[type_name]
                        processed_value = handler(component)
                        update_nested_dict(config_data, new_path, processed_value)

            recurse_mapping(mapping)
            return config_data


        def update_config(config_mapping, config, config_data, type="common_config"):
            # 处理常规配置
            for section, section_mapping in config_mapping.items():
                if type is not None:
                    if config.get("webui", "show_card", type, section):
                        if section not in config_data:
                            config_data[section] = {}
                        
                        process_config_mapping(config_data[section], section_mapping)
                else:
                    if section not in config_data:
                        config_data[section] = {}
                    
                    process_config_mapping(config_data[section], section_mapping)

            return config_data



        try:
            """
            通用配置
            """
            if True:
                config_data["platform"] = select_platform.value
                config_data["room_display_id"] = input_room_display_id.value
                config_data["chat_type"] = select_chat_type.value
                config_data["visual_body"] = select_visual_body.value
                config_data["need_lang"] = select_need_lang.value
                config_data["before_prompt"] = input_before_prompt.value
                config_data["after_prompt"] = input_after_prompt.value
                config_data["audio_synthesis_type"] = select_audio_synthesis_type.value

                config_mapping = {
                    "comment_template": {
                        "enable": (switch_comment_template_enable, 'bool'),
                        "copywriting": (input_comment_template_copywriting, 'str'),
                    },
                    "reply_template": {
                        "enable": (switch_reply_template_enable, 'bool'),
                        "username_max_len": (input_reply_template_username_max_len, 'int'),
                        "copywriting": (textarea_reply_template_copywriting, 'textarea'),
                    },
                    "bilibili": {
                        "login_type": (select_bilibili_login_type, 'str'),
                        "cookie": (input_bilibili_cookie, 'str'),
                        "ac_time_value": (input_bilibili_ac_time_value, 'str'),
                        "open_live": {
                            "ACCESS_KEY_ID": (input_bilibili_open_live_ACCESS_KEY_ID, 'str'),
                            "ACCESS_KEY_SECRET": (input_bilibili_open_live_ACCESS_KEY_SECRET, 'str'),
                            "APP_ID": (input_bilibili_open_live_APP_ID, 'int'),
                            "ROOM_OWNER_AUTH_CODE": (input_bilibili_open_live_ROOM_OWNER_AUTH_CODE, 'str'),
                        },
                    },
                    "ordinaryroad_barrage_fly": {
                        "ws_ip_port": (input_ordinaryroad_barrage_fly_ws_ip_port, 'str'),
                        "taskIds": (textarea_ordinaryroad_barrage_fly_taskIds, 'textarea'),
                    },
                    "twitch": {
                        "token": (input_twitch_token, 'str'),
                        "user": (input_twitch_user, 'str'),
                        "proxy_server": (input_twitch_proxy_server, 'str'),
                        "proxy_port": (input_twitch_proxy_port, 'str'),
                    },
                }
                config_data = update_config(config_mapping, config, config_data, None)
                
                config_mapping = {}
                # 日志
                if config.get("webui", "show_card", "common_config", "log"):
                    config_data["comment_log_type"] = select_comment_log_type.value
                    config_data["captions"]["enable"] = switch_captions_enable.value
                    config_data["captions"]["file_path"] = input_captions_file_path.value
                    config_data["captions"]["raw_file_path"] = input_captions_raw_file_path.value

            
                # 音频播放
                if config.get("webui", "show_card", "common_config", "play_audio"):
                    # audio_player
                    config_data["audio_player"]["api_ip_port"] = input_audio_player_api_ip_port.value

                    config_mapping = {
                        "play_audio": {
                            "enable": (switch_play_audio_enable, 'bool'),
                            "text_split_enable": (switch_play_audio_text_split_enable, 'bool'),
                            "info_to_callback": (switch_play_audio_info_to_callback, 'bool'),
                            "interval_num_min": (input_play_audio_interval_num_min, 'int'),
                            "interval_num_max": (input_play_audio_interval_num_max, 'int'),
                            "normal_interval_min": (input_play_audio_normal_interval_min, 'float'),
                            "normal_interval_max": (input_play_audio_normal_interval_max, 'float'),
                            "out_path": (input_play_audio_out_path,'str'),
                            "player": (select_play_audio_player,'str'),
                        }
                    }

                if config.get("webui", "show_card", "common_config", "read_comment"):
                    config_mapping["read_comment"] = {
                        "enable": (switch_read_comment_enable, 'bool'),
                        "read_username_enable": (switch_read_comment_read_username_enable, 'bool'),
                        "username_max_len": (input_read_comment_username_max_len, 'int'),
                        "voice_change": (switch_read_comment_voice_change, 'bool'),
                        "read_username_copywriting": (textarea_read_comment_read_username_copywriting, 'textarea'),
                        "periodic_trigger": {
                            "enable": (switch_read_comment_periodic_trigger_enable, 'bool'),
                            "periodic_time_min": (input_read_comment_periodic_trigger_periodic_time_min, 'int'),
                            "periodic_time_max": (input_read_comment_periodic_trigger_periodic_time_max, 'int'),
                            "trigger_num_min": (input_read_comment_periodic_trigger_trigger_num_min, 'int'),
                            "trigger_num_max": (input_read_comment_periodic_trigger_trigger_num_max, 'int'),
                        },
                    }

                if config.get("webui", "show_card", "common_config", "local_qa"):
                    config_mapping["local_qa"] = {
                        "periodic_trigger": {
                            "enable": (switch_local_qa_periodic_trigger_enable, 'bool'),
                            "periodic_time_min": (input_local_qa_periodic_trigger_periodic_time_min, 'int'),
                            "periodic_time_max": (input_local_qa_periodic_trigger_periodic_time_max, 'int'),
                            "trigger_num_min": (input_local_qa_periodic_trigger_trigger_num_min, 'int'),
                            "trigger_num_max": (input_local_qa_periodic_trigger_trigger_num_max, 'int'),
                        },
                        "text": {
                            "enable": (switch_local_qa_text_enable, 'bool'),
                            "type": (select_local_qa_text_type, 'str'),
                            "file_path": (input_local_qa_text_file_path, 'str'),
                            "similarity": (input_local_qa_text_similarity, 'float'),
                            "username_max_len": (input_local_qa_text_username_max_len, 'int'),
                        },
                        "audio": {
                            "enable": (switch_local_qa_audio_enable, 'bool'),
                            "file_path": (input_local_qa_audio_file_path, 'str'),
                            "similarity": (input_local_qa_audio_similarity, 'float'),
                        },
                    }

                if config.get("webui", "show_card", "common_config", "filter"):
                    config_mapping["filter"] = {
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

                if config.get("webui", "show_card", "common_config", "thanks"):
                    config_mapping["thanks"] = {
                        "username_max_len": (input_thanks_username_max_len, 'int'),
                        "entrance_enable": (switch_thanks_entrance_enable, 'bool'),
                        "entrance_random": (switch_thanks_entrance_random, 'bool'),
                        "entrance_copy": (textarea_thanks_entrance_copy, 'textarea'),
                        "entrance": {
                            "periodic_trigger": {
                                "enable": (switch_thanks_entrance_periodic_trigger_enable, 'bool'),
                                "periodic_time_min": (input_thanks_entrance_periodic_trigger_periodic_time_min, 'int'),
                                "periodic_time_max": (input_thanks_entrance_periodic_trigger_periodic_time_max, 'int'),
                                "trigger_num_min": (input_thanks_entrance_periodic_trigger_trigger_num_min, 'int'),
                                "trigger_num_max": (input_thanks_entrance_periodic_trigger_trigger_num_max, 'int'),
                            }
                        },
                        "gift_enable": (switch_thanks_gift_enable, 'bool'),
                        "gift_random": (switch_thanks_gift_random, 'bool'),
                        "gift_copy": (textarea_thanks_gift_copy, 'textarea'),
                        "gift": {
                            "periodic_trigger": {
                                "enable": (switch_thanks_gift_periodic_trigger_enable, 'bool'),
                                "periodic_time_min": (input_thanks_gift_periodic_trigger_periodic_time_min, 'int'),
                                "periodic_time_max": (input_thanks_gift_periodic_trigger_periodic_time_max, 'int'),
                                "trigger_num_min": (input_thanks_gift_periodic_trigger_trigger_num_min, 'int'),
                                "trigger_num_max": (input_thanks_gift_periodic_trigger_trigger_num_max, 'int'),
                            }
                        },
                        "follow_enable": (switch_thanks_follow_enable, 'bool'),
                        "follow_random": (switch_thanks_follow_random, 'bool'),
                        "follow_copy": (textarea_thanks_follow_copy, 'textarea'),
                        "follow": {
                            "periodic_trigger": {
                                "enable": (switch_thanks_follow_periodic_trigger_enable, 'bool'),
                                "periodic_time_min": (input_thanks_follow_periodic_trigger_periodic_time_min, 'int'),
                                "periodic_time_max": (input_thanks_follow_periodic_trigger_periodic_time_max, 'int'),
                                "trigger_num_min": (input_thanks_follow_periodic_trigger_trigger_num_min, 'int'),
                                "trigger_num_max": (input_thanks_follow_periodic_trigger_trigger_num_max, 'int'),
                            }
                        },
                        "lowest_price": (input_thanks_lowest_price, 'float')
                    }

                if config.get("webui", "show_card", "common_config", "audio_random_speed"):
                    config_mapping["audio_random_speed"] = {
                        "normal": {
                            "enable": (switch_audio_random_speed_normal_enable, 'bool'),
                            "speed_min": (input_audio_random_speed_normal_speed_min, 'float'),
                            "speed_max": (input_audio_random_speed_normal_speed_max, 'float'),
                        },
                        "copywriting": {
                            "enable": (switch_audio_random_speed_copywriting_enable, 'bool'),
                            "speed_min": (input_audio_random_speed_copywriting_speed_min, 'float'),
                            "speed_max": (input_audio_random_speed_copywriting_speed_max, 'float'),
                        },
                    }
                if config.get("webui", "show_card", "common_config", "choose_song"):
                    config_mapping["choose_song"] = {
                        "enable": (switch_choose_song_enable, 'bool'),
                        "start_cmd": (textarea_choose_song_start_cmd,'textarea'),
                        "stop_cmd": (textarea_choose_song_stop_cmd,'textarea'),
                        "random_cmd": (textarea_choose_song_random_cmd,'textarea'),
                        "song_path": (input_choose_song_song_path,'str'),
                        "match_fail_copy": (input_choose_song_match_fail_copy,'str'),
                        "similarity": (input_choose_song_similarity,'float'),
                    }
                if config.get("webui", "show_card", "common_config", "sd"):
                    config_mapping["sd"] = {
                        "enable": (switch_sd_enable, 'bool'),
                        "translate_type": (select_sd_translate_type, 'str'),
                        "prompt_llm": {
                            "type": (select_sd_prompt_llm_type, 'str'),
                            "before_prompt": (input_sd_prompt_llm_before_prompt, 'str'),
                            "after_prompt": (input_sd_prompt_llm_after_prompt, 'str'),
                        },
                        "trigger": (input_sd_trigger, 'str'),
                        "ip": (input_sd_ip, 'str'),
                        "port": (input_sd_port, 'int'),
                        "negative_prompt": (input_sd_negative_prompt, 'str'),
                        "seed": (input_sd_seed, 'float'),
                        "styles": (textarea_sd_styles, 'textarea'),
                        "cfg_scale": (input_sd_cfg_scale, 'int'),
                        "steps": (input_sd_steps, 'int'),
                        "hr_resize_x": (input_sd_hr_resize_x, 'int'),
                        "hr_resize_y": (input_sd_hr_resize_y, 'int'),
                        "enable_hr": (switch_sd_enable_hr, 'bool'),
                        "hr_scale": (input_sd_hr_scale, 'int'),
                        "hr_second_pass_steps": (input_sd_hr_second_pass_steps, 'int'),
                        "denoising_strength": (input_sd_denoising_strength, 'float'),
                        "save_enable": (switch_sd_save_enable, 'bool'),
                        "loop_cover": (switch_sd_loop_cover, 'bool'),
                        "save_path": (input_sd_save_path, 'str'),
                    }
                if config.get("webui", "show_card", "common_config", "search_online"):
                    config_mapping["search_online"] = {
                        "enable": (switch_search_online_enable, 'bool'),
                        "keyword_enable": (switch_search_online_keyword_enable, 'bool'),
                        "before_keyword": (textarea_search_online_before_keyword, 'textarea'),
                        "engine": (select_search_online_engine, 'str'),
                        "engine_id": (input_search_online_engine_id, 'int'),
                        "count": (input_search_online_count, 'int'),
                        "resp_template": (input_search_online_resp_template, 'str'),
                        "http_proxy": (input_search_online_http_proxy, 'str'),
                        "https_proxy": (input_search_online_https_proxy, 'str'),
                    }
                if config.get("webui", "show_card", "common_config", "web_captions_printer"):
                    config_mapping["web_captions_printer"] = {
                        "enable": (switch_web_captions_printer_enable, 'bool'),
                        "api_ip_port": (input_web_captions_printer_api_ip_port, 'str'),
                    }
                if config.get("webui", "show_card", "common_config", "database"):
                    config_mapping["database"] = {
                        "path": (input_database_path, 'str'),
                        "comment_enable": (switch_database_comment_enable, 'bool'),
                        "entrance_enable": (switch_database_entrance_enable, 'bool'),
                        "gift_enable": (switch_database_gift_enable, 'bool'),
                    }
                if config.get("webui", "show_card", "common_config", "abnormal_alarm"):
                    config_mapping["abnormal_alarm"] = {
                        "platform": {
                            "enable": (switch_abnormal_alarm_platform_enable, 'bool'),
                            "type": (select_abnormal_alarm_platform_type, 'str'),
                            "start_alarm_error_num": (input_abnormal_alarm_platform_start_alarm_error_num, 'int'),
                            "auto_restart_error_num": (input_abnormal_alarm_platform_auto_restart_error_num, 'int'),
                            "local_audio_path": (input_abnormal_alarm_platform_local_audio_path, 'str'),
                        },
                        "llm": {
                            "enable": (switch_abnormal_alarm_llm_enable, 'bool'),
                            "type": (select_abnormal_alarm_llm_type, 'str'),
                            "start_alarm_error_num": (input_abnormal_alarm_llm_start_alarm_error_num, 'int'),
                            "auto_restart_error_num": (input_abnormal_alarm_llm_auto_restart_error_num, 'int'),
                            "local_audio_path": (input_abnormal_alarm_llm_local_audio_path, 'str'),
                        },
                        "tts": {
                            "enable": (switch_abnormal_alarm_tts_enable, 'bool'),
                            "type": (select_abnormal_alarm_tts_type, 'str'),
                            "start_alarm_error_num": (input_abnormal_alarm_tts_start_alarm_error_num, 'int'),
                            "auto_restart_error_num": (input_abnormal_alarm_tts_auto_restart_error_num, 'int'),
                            "local_audio_path": (input_abnormal_alarm_tts_local_audio_path, 'str'),
                        },
                        "svc": {
                            "enable": (switch_abnormal_alarm_svc_enable, 'bool'),
                            "type": (select_abnormal_alarm_svc_type, 'str'),
                            "start_alarm_error_num": (input_abnormal_alarm_svc_start_alarm_error_num, 'int'),
                            "auto_restart_error_num": (input_abnormal_alarm_svc_auto_restart_error_num, 'int'),
                            "local_audio_path": (input_abnormal_alarm_svc_local_audio_path, 'str'),
                        },
                        "visual_body": {
                            "enable": (switch_abnormal_alarm_visual_body_enable, 'bool'),
                            "type": (select_abnormal_alarm_visual_body_type, 'str'),
                            "start_alarm_error_num": (input_abnormal_alarm_visual_body_start_alarm_error_num, 'int'),
                            "auto_restart_error_num": (input_abnormal_alarm_visual_body_auto_restart_error_num, 'int'),
                            "local_audio_path": (input_abnormal_alarm_visual_body_local_audio_path, 'str'),
                        },
                        "other": {
                            "enable": (switch_abnormal_alarm_other_enable, 'bool'),
                            "type": (select_abnormal_alarm_other_type, 'str'),
                            "start_alarm_error_num": (input_abnormal_alarm_other_start_alarm_error_num, 'int'),
                            "auto_restart_error_num": (input_abnormal_alarm_other_auto_restart_error_num, 'int'),
                            "local_audio_path": (input_abnormal_alarm_other_local_audio_path, 'str'),
                        },
                    }

                config_data = update_config(config_mapping, config, config_data, "common_config")
                
                # 定时任务
                if config.get("webui", "show_card", "common_config", "schedule"):
                    tmp_arr = []
                    # logger.info(schedule_var)
                    for index in range(len(schedule_var) // 4):
                        tmp_json = {
                            "enable": False,
                            "time_min": 60,
                            "time_max": 120,
                            "copy": []
                        }
                        tmp_json["enable"] = schedule_var[str(4 * index)].value
                        tmp_json["time_min"] = round(float(schedule_var[str(4 * index + 1)].value), 1)
                        tmp_json["time_max"] = round(float(schedule_var[str(4 * index + 2)].value), 1)
                        tmp_json["copy"] = common_textarea_handle(schedule_var[str(4 * index + 3)].value)

                        tmp_arr.append(tmp_json)
                    # logger.info(tmp_arr)
                    config_data["schedule"] = tmp_arr

                # 闲时任务
                if config.get("webui", "show_card", "common_config", "idle_time_task"):
                    config_data["idle_time_task"]["enable"] = switch_idle_time_task_enable.value
                    config_data["idle_time_task"]["type"] = select_idle_time_task_type.value

                    config_data["idle_time_task"]["min_msg_queue_len_to_trigger"] = int(input_idle_time_task_idle_min_msg_queue_len_to_trigger.value)
                    config_data["idle_time_task"]["min_audio_queue_len_to_trigger"] = int(input_idle_time_task_idle_min_audio_queue_len_to_trigger.value)

                    config_data["idle_time_task"]["idle_time_min"] = int(input_idle_time_task_idle_time_min.value)
                    config_data["idle_time_task"]["idle_time_max"] = int(input_idle_time_task_idle_time_max.value)
                    config_data["idle_time_task"]["wait_play_audio_num_threshold"] = int(input_idle_time_task_wait_play_audio_num_threshold.value)
                    config_data["idle_time_task"]["idle_time_reduce_to"] = int(input_idle_time_task_idle_time_reduce_to.value)

                    tmp_arr = []
                    for index in range(len(idle_time_task_trigger_type_var)):
                        if idle_time_task_trigger_type_var[str(index)].value:
                            tmp_arr.append(common.find_keys_by_value(idle_time_task_trigger_type_mapping, idle_time_task_trigger_type_var[str(index)].text)[0])
                    # logger.info(tmp_arr)
                    config_data["idle_time_task"]["trigger_type"] = tmp_arr

                    config_data["idle_time_task"]["comment"]["enable"] = switch_idle_time_task_comment_enable.value
                    config_data["idle_time_task"]["comment"]["random"] = switch_idle_time_task_comment_random.value
                    config_data["idle_time_task"]["copywriting"]["copy"] = common_textarea_handle(textarea_idle_time_task_copywriting_copy.value)
                    config_data["idle_time_task"]["copywriting"]["enable"] = switch_idle_time_task_copywriting_enable.value
                    config_data["idle_time_task"]["copywriting"]["random"] = switch_idle_time_task_copywriting_random.value
                    config_data["idle_time_task"]["comment"]["copy"] = common_textarea_handle(textarea_idle_time_task_comment_copy.value)
                    config_data["idle_time_task"]["local_audio"]["enable"] = switch_idle_time_task_local_audio_enable.value
                    config_data["idle_time_task"]["local_audio"]["random"] = switch_idle_time_task_local_audio_random.value
                    config_data["idle_time_task"]["local_audio"]["path"] = common_textarea_handle(textarea_idle_time_task_local_audio_path.value)


                # 动态文案
                if config.get("webui", "show_card", "common_config", "trends_copywriting"):
                    config_data["trends_copywriting"]["enable"] = switch_trends_copywriting_enable.value
                    config_data["trends_copywriting"]["llm_type"] = select_trends_copywriting_llm_type.value
                    config_data["trends_copywriting"]["random_play"] = switch_trends_copywriting_random_play.value
                    config_data["trends_copywriting"]["play_interval"] = int(input_trends_copywriting_play_interval.value)
                    tmp_arr = []
                    for index in range(len(trends_copywriting_copywriting_var) // 3):
                        tmp_json = {
                            "folder_path": "",
                            "prompt_change_enable": False,
                            "prompt_change_content": ""
                        }
                        tmp_json["folder_path"] = trends_copywriting_copywriting_var[str(3 * index)].value
                        tmp_json["prompt_change_enable"] = trends_copywriting_copywriting_var[str(3 * index + 1)].value
                        tmp_json["prompt_change_content"] = trends_copywriting_copywriting_var[str(3 * index + 2)].value

                        tmp_arr.append(tmp_json)
                    # logger.info(tmp_arr)
                    config_data["trends_copywriting"]["copywriting"] = tmp_arr

                
                # 按键映射
                if config.get("webui", "show_card", "common_config", "key_mapping"):
                    config_data["key_mapping"]["enable"] = switch_key_mapping_enable.value
                    config_data["key_mapping"]["type"] = select_key_mapping_type.value
                    config_data["key_mapping"]["key_trigger_type"] = select_key_mapping_key_trigger_type.value
                    config_data["key_mapping"]["key_single_sentence_trigger_once"] = switch_key_mapping_key_single_sentence_trigger_once_enable.value
                    config_data["key_mapping"]["copywriting_trigger_type"] = select_key_mapping_copywriting_trigger_type.value
                    config_data["key_mapping"]["copywriting_single_sentence_trigger_once"] = switch_key_mapping_copywriting_single_sentence_trigger_once_enable.value
                    config_data["key_mapping"]["local_audio_trigger_type"] = select_key_mapping_local_audio_trigger_type.value
                    config_data["key_mapping"]["local_audio_single_sentence_trigger_once"] = switch_key_mapping_local_audio_single_sentence_trigger_once_enable.value
                    config_data["key_mapping"]["serial_trigger_type"] = select_key_mapping_serial_trigger_type.value
                    config_data["key_mapping"]["serial_single_sentence_trigger_once"] = switch_key_mapping_serial_single_sentence_trigger_once_enable.value
                    config_data["key_mapping"]["img_path_trigger_type"] = select_key_mapping_img_path_trigger_type.value
                    config_data["key_mapping"]["img_path_single_sentence_trigger_once"] = switch_key_mapping_img_path_single_sentence_trigger_once_enable.value
                    

                    config_data["key_mapping"]["start_cmd"] = input_key_mapping_start_cmd.value
                    tmp_arr = []
                    # logger.info(key_mapping_config_var)

                    num = 9

                    for index in range(len(key_mapping_config_var) // num):
                        tmp_json = {
                            "keywords": [],
                            "gift": [],
                            "keys": [],
                            "similarity": 0.8,
                            "copywriting": [],
                            "serial_name": "",
                            "serial_send_data": [],
                            "img_path": []
                        }
                        tmp_json["keywords"] = common_textarea_handle(key_mapping_config_var[str(num * index)].value)
                        tmp_json["gift"] = common_textarea_handle(key_mapping_config_var[str(num * index + 1)].value)
                        tmp_json["keys"] = common_textarea_handle(key_mapping_config_var[str(num * index + 2)].value)
                        tmp_json["similarity"] = key_mapping_config_var[str(num * index + 3)].value
                        tmp_json["copywriting"] = common_textarea_handle(key_mapping_config_var[str(num * index + 4)].value)
                        tmp_json["local_audio"] = common_textarea_handle(key_mapping_config_var[str(num * index + 5)].value)
                        tmp_json["serial_name"] = key_mapping_config_var[str(num * index + 6)].value
                        tmp_json["serial_send_data"] = common_textarea_handle(key_mapping_config_var[str(num * index + 7)].value)
                        tmp_json["img_path"] = common_textarea_handle(key_mapping_config_var[str(num * index + 8)].value)

                        tmp_arr.append(tmp_json)
                    # logger.info(tmp_arr)
                    config_data["key_mapping"]["config"] = tmp_arr

                # 自定义命令
                if config.get("webui", "show_card", "common_config", "custom_cmd"):
                    config_data["custom_cmd"]["enable"] = switch_custom_cmd_enable.value
                    config_data["custom_cmd"]["type"] = select_custom_cmd_type.value
                    tmp_arr = []
                    # logger.info(custom_cmd_config_var)
                    for index in range(len(custom_cmd_config_var) // 7):
                        tmp_json = {
                            "keywords": [],
                            "similarity": 1,
                            "api_url": "",
                            "api_type": "",
                            "resp_data_type": "",
                            "data_analysis": "",
                            "resp_template": ""
                        }
                        tmp_json["keywords"] = common_textarea_handle(custom_cmd_config_var[str(7 * index)].value)
                        tmp_json["similarity"] = float(custom_cmd_config_var[str(7 * index + 1)].value)
                        tmp_json["api_url"] = custom_cmd_config_var[str(7 * index + 2)].value
                        tmp_json["api_type"] = custom_cmd_config_var[str(7 * index + 3)].value
                        tmp_json["resp_data_type"] = custom_cmd_config_var[str(7 * index + 4)].value
                        tmp_json["data_analysis"] = custom_cmd_config_var[str(7 * index + 5)].value
                        tmp_json["resp_template"] = custom_cmd_config_var[str(7 * index + 6)].value

                        tmp_arr.append(tmp_json)
                    # logger.info(tmp_arr)
                    config_data["custom_cmd"]["config"] = tmp_arr

                # 动态配置
                if config.get("webui", "show_card", "common_config", "trends_config"):
                    config_data["trends_config"]["enable"] = switch_trends_config_enable.value
                    tmp_arr = []
                    # logger.info(trends_config_path_var)
                    for index in range(len(trends_config_path_var) // 2):
                        tmp_json = {
                            "online_num": "0-999999999",
                            "path": "config.json"
                        }
                        tmp_json["online_num"] = trends_config_path_var[str(2 * index)].value
                        tmp_json["path"] = trends_config_path_var[str(2 * index + 1)].value

                        tmp_arr.append(tmp_json)
                    # logger.info(tmp_arr)
                    config_data["trends_config"]["path"] = tmp_arr

                
                # 联动程序
                if config.get("webui", "show_card", "common_config", "coordination_program"):
                    tmp_arr = []
                    for index in range(len(coordination_program_var) // 4):
                        tmp_json = {
                            "enable": True,
                            "name": "",
                            "executable": "",
                            "parameters": []
                        }
                        tmp_json["enable"] = coordination_program_var[str(4 * index)].value
                        tmp_json["name"] = coordination_program_var[str(4 * index + 1)].value
                        tmp_json["executable"] = coordination_program_var[str(4 * index + 2)].value
                        tmp_json["parameters"] = common_textarea_handle(coordination_program_var[str(4 * index + 3)].value)

                        tmp_arr.append(tmp_json)
                    # logger.info(tmp_arr)
                    config_data["coordination_program"] = tmp_arr
                
                tmp_arr = []
                for index in range(len(luoxi_project_Live_Comment_Assistant_type_var)):
                    if luoxi_project_Live_Comment_Assistant_type_var[str(index)].value:
                        tmp_arr.append(
                            common.find_keys_by_value(
                                luoxi_project_Live_Comment_Assistant_type_mapping, 
                                luoxi_project_Live_Comment_Assistant_type_var[str(index)].text
                            )[0]
                        )
                # logger.info(tmp_arr)
                config_data["luoxi_project"]["Live_Comment_Assistant"]["type"] = tmp_arr

                tmp_arr = []
                for index in range(len(luoxi_project_Live_Comment_Assistant_trigger_position_var)):
                    if luoxi_project_Live_Comment_Assistant_trigger_position_var[str(index)].value:
                        tmp_arr.append(
                            common.find_keys_by_value(
                                luoxi_project_Live_Comment_Assistant_trigger_position_mapping, 
                                luoxi_project_Live_Comment_Assistant_trigger_position_var[str(index)].text
                            )[0]
                        )
                # logger.info(tmp_arr)
                config_data["luoxi_project"]["Live_Comment_Assistant"]["trigger_position"] = tmp_arr

                config_mapping = {
                    "luoxi_project": {
                        "Live_Comment_Assistant": {
                            "enable": (switch_luoxi_project_Live_Comment_Assistant_enable, 'bool'),
                            "version": (select_luoxi_project_Live_Comment_Assistant_version, 'str'),
                            "api_ip_port": (input_luoxi_project_Live_Comment_Assistant_api_ip_port, 'str'),
                        }
                    }
                }

                config_data = update_config(config_mapping, config, config_data, None)

            """
            UI配置
            """
            if True:
                config_mapping = {
                    "webui": {
                        "title": (input_webui_title, 'str'),
                        "ip": (input_webui_ip, 'str'),
                        "port": (input_webui_port, 'int'),
                        "auto_run": (switch_webui_auto_run, 'bool'),
                        "local_dir_to_endpoint": {
                            "enable": (switch_webui_local_dir_to_endpoint_enable, 'bool'),
                        },
                        "show_card": {
                            "common_config": {
                                "read_comment": (switch_webui_show_card_common_config_read_comment, 'bool'),
                                "filter": (switch_webui_show_card_common_config_filter, 'bool'),
                                "thanks": (switch_webui_show_card_common_config_thanks, 'bool'),
                                "local_qa": (switch_webui_show_card_common_config_local_qa, 'bool'),
                                "choose_song": (switch_webui_show_card_common_config_choose_song, 'bool'),
                                "sd": (switch_webui_show_card_common_config_sd, 'bool'),
                                "log": (switch_webui_show_card_common_config_log, 'bool'),
                                "schedule": (switch_webui_show_card_common_config_schedule, 'bool'),
                                "idle_time_task": (switch_webui_show_card_common_config_idle_time_task, 'bool'),
                                "trends_copywriting": (switch_webui_show_card_common_config_trends_copywriting, 'bool'),
                                "database": (switch_webui_show_card_common_config_database, 'bool'),
                                "play_audio": (switch_webui_show_card_common_config_play_audio, 'bool'),
                                "web_captions_printer": (switch_webui_show_card_common_config_web_captions_printer, 'bool'),
                                "key_mapping": (switch_webui_show_card_common_config_key_mapping, 'bool'),
                                "custom_cmd": (switch_webui_show_card_common_config_custom_cmd, 'bool'),
                                "trends_config": (switch_webui_show_card_common_config_trends_config, 'bool'),
                                "abnormal_alarm": (switch_webui_show_card_common_config_abnormal_alarm, 'bool'),
                                "coordination_program": (switch_webui_show_card_common_config_coordination_program, 'bool'),
                            },
                            "llm": {
                                "chatgpt": (switch_webui_show_card_llm_chatgpt, 'bool'),
                                "zhipu": (switch_webui_show_card_llm_zhipu, 'bool'),
                                "chat_with_file": (switch_webui_show_card_llm_chat_with_file, 'bool'),
                                "langchain_chatchat": (switch_webui_show_card_llm_langchain_chatchat, 'bool'),
                                "chatterbot": (switch_webui_show_card_llm_chatterbot, 'bool'),
                                "text_generation_webui": (switch_webui_show_card_llm_text_generation_webui, 'bool'),
                                "sparkdesk": (switch_webui_show_card_llm_sparkdesk, 'bool'),
                                "bard": (switch_webui_show_card_llm_bard, 'bool'),
                                "tongyi": (switch_webui_show_card_llm_tongyi, 'bool'),
                                "tongyixingchen": (switch_webui_show_card_llm_tongyixingchen, 'bool'),
                                "my_wenxinworkshop": (switch_webui_show_card_llm_my_wenxinworkshop, 'bool'),
                                "gemini": (switch_webui_show_card_llm_gemini, 'bool'),
                                "koboldcpp": (switch_webui_show_card_llm_koboldcpp, 'bool'),
                                "anythingllm": (switch_webui_show_card_llm_anythingllm, 'bool'),
                                "gpt4free": (switch_webui_show_card_llm_gpt4free, 'bool'),
                                "custom_llm": (switch_webui_show_card_llm_custom_llm, 'bool'),
                                "llm_tpu": (switch_webui_show_card_llm_llm_tpu, 'bool'),
                                "dify": (switch_webui_show_card_llm_dify, 'bool'),
                                "volcengine": (switch_webui_show_card_llm_volcengine, 'bool'),
                            },
                            "tts": {
                                "edge-tts": (switch_webui_show_card_tts_edge_tts, 'bool'),
                                "vits": (switch_webui_show_card_tts_vits, 'bool'),
                                "bert_vits2": (switch_webui_show_card_tts_bert_vits2, 'bool'),
                                "vits_fast": (switch_webui_show_card_tts_vits_fast, 'bool'),
                                "elevenlabs": (switch_webui_show_card_tts_elevenlabs, 'bool'),
                                "openai_tts": (switch_webui_show_card_tts_openai_tts, 'bool'),
                                "gradio_tts": (switch_webui_show_card_tts_gradio_tts, 'bool'),
                                "gpt_sovits": (switch_webui_show_card_tts_gpt_sovits, 'bool'),
                                "azure_tts": (switch_webui_show_card_tts_azure_tts, 'bool'),
                                "cosyvoice": (switch_webui_show_card_tts_cosyvoice, 'bool'),
                                "f5_tts": (switch_webui_show_card_tts_f5_tts, 'bool'),
                                "multitts": (switch_webui_show_card_tts_multitts, 'bool'),
                                "melotts": (switch_webui_show_card_tts_melotts, 'bool'),
                                "index_tts": (switch_webui_show_card_tts_index_tts, 'bool'),
                            },
                            "svc": {
                                "ddsp_svc": (switch_webui_show_card_svc_ddsp_svc, 'bool'),
                                "so_vits_svc": (switch_webui_show_card_svc_so_vits_svc, 'bool'),
                            },
                            "visual_body": {
                                "live2d": (switch_webui_show_card_visual_body_live2d, 'bool'),
                                "xuniren": (switch_webui_show_card_visual_body_xuniren, 'bool'),
                                "metahuman_stream": (switch_webui_show_card_visual_body_metahuman_stream, 'bool'),
                                "unity": (switch_webui_show_card_visual_body_unity, 'bool'),
                                "EasyAIVtuber": (switch_webui_show_card_visual_body_EasyAIVtuber, 'bool'),
                                "digital_human_video_player": (switch_webui_show_card_visual_body_digital_human_video_player, 'bool'),
                                "live2d_TTS_LLM_GPT_SoVITS_Vtuber": (switch_webui_show_card_visual_body_live2d_TTS_LLM_GPT_SoVITS_Vtuber, 'bool'),
                            },
                        },
                        "theme": {
                            "choose": (select_webui_theme_choose, 'str'),
                        },
                    },
                    "login": {
                        "enable": (switch_login_enable, 'bool'),
                        "username": (input_login_username, 'str'),
                        "password": (input_login_password, 'str'),
                    }
                }

                config_data = update_config(config_mapping, config, config_data, None)

                tmp_arr = []
                for index in range(len(webui_local_dir_to_endpoint_config_var) // 2):
                    tmp_json = {
                        "url_path": "",
                        "local_dir": ""
                    }
                    tmp_json["url_path"] = webui_local_dir_to_endpoint_config_var[str(2 * index)].value
                    tmp_json["local_dir"] = webui_local_dir_to_endpoint_config_var[str(2 * index + 1)].value

                    tmp_arr.append(tmp_json)
                # logger.info(tmp_arr)
                config_data["webui"]["local_dir_to_endpoint"]["config"] = tmp_arr

                
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
            ui.notify(position="top", type="negative", message=f"无法读取webui配置到变量！\n{e}")
            logger.error(traceback.format_exc())

            return None

    # 保存配置
    def save_config():
        """
        保存配置到本地配置文件中
        """
        global config, config_path

        # 配置检查
        if not check_config():
            return False

        try:
            with open(config_path, 'r', encoding="utf-8") as config_file:
                config_data = json.load(config_file)
        except Exception as e:
            logger.error(f"无法读取配置文件！\n{e}")
            ui.notify(position="top", type="negative", message=f"无法读取配置文件！{e}")
            return False

        # 读取webui配置到dict变量
        config_data = webui_config_to_dict(config_data)
        if config_data is None:
            return False

        # 写入本地问答json数据到文件
        if config.get("webui", "show_card", "common_config", "local_qa"):
            try:
                ret = common.write_content_to_file(input_local_qa_text_json_file_path.value, textarea_local_qa_text_json_file_content.value, write_log=False)
                if not ret:
                    ui.notify(position="top", type="negative", message="无法写入本地问答json数据到文件！\n详细报错见日志")
                    return False
            except Exception as e:
                logger.error(f"无法写入本地问答json数据到文件！\n{str(e)}")
                ui.notify(position="top", type="negative", message=f"无法写入本地问答json数据到文件！\n{str(e)}")
                return False   

        # 写入配置到配置文件
        try:
            with open(config_path, 'w', encoding="utf-8") as config_file:
                json.dump(config_data, config_file, indent=2, ensure_ascii=False)
                config_file.flush()  # 刷新缓冲区，确保写入立即生效

            logger.info("配置数据已成功写入文件！")
            ui.notify(position="top", type="positive", message="配置数据已成功写入文件！")

            return True
        except Exception as e:
            logger.error(f"无法写入配置文件！\n{str(e)}")
            ui.notify(position="top", type="negative", message=f"无法写入配置文件！\n{str(e)}")
            return False
        


    """

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
    chat_type_options = {
        'none': '不启用', 
        'reread': '复读机', 
        'chatgpt': 'ChatGPT/闻达', 
        'chat_with_file': 'chat_with_file',
        'chatterbot': 'Chatterbot',
        'text_generation_webui': 'text_generation_webui',
        'sparkdesk': '讯飞星火',
        'langchain_chatchat': 'langchain_chatchat',
        'zhipu': '智谱AI',
        'bard': 'Bard',
        'tongyixingchen': '通义星尘',
        'my_wenxinworkshop': '千帆大模型',
        'gemini': 'Gemini',
        'koboldcpp': 'koboldcpp',
        'anythingllm': 'AnythingLLM',
        'tongyi': '通义千问/阿里云百炼',
        'gpt4free': 'GPT4Free',
        'dify': 'Dify',
        'volcengine': '火山引擎',
        'llm_tpu': 'LLM_TPU',
        'custom_llm': '自定义LLM',
    }

    platform_options = {
        'talk': '聊天模式', 
        'bilibili': '哔哩哔哩', 
        'bilibili2': '哔哩哔哩2', 
        'dy': '抖音', 
        'dy2': '抖音2', 
        'ks': '快手',
        'ks2': '快手2',
        'pdd': '拼多多',
        'wxlive': '微信视频号',
        'taobao': '淘宝',
        '1688': '1688',
        'douyu': '斗鱼',
        'ordinaryroad_barrage_fly': '让弹幕飞',
        'youtube': 'YouTube', 
        'twitch': 'twitch', 
        'tiktok': 'tiktok',
    }

    visual_body_options = {
        '其他': '其他（外置）',
        'metahuman_stream': 'metahuman_stream', 
        'EasyAIVtuber': 'EasyAIVtuber', 
        'digital_human_video_player': '数字人视频播放器', 
        'live2d_TTS_LLM_GPT_SoVITS_Vtuber': 'live2d-TTS-LLM-GPT-SoVITS-Vtuber',
        'xuniren': 'xuniren', 
    }

    page_config_mappings = []

    with ui.tabs().classes('w-full') as tabs:
        common_config_page = ui.tab('通用配置')
        llm_page = ui.tab('大语言模型')
        tts_page = ui.tab('文本转语音')
        svc_page = ui.tab('变声')
        visual_body_page = ui.tab('虚拟身体')
        copywriting_page = ui.tab('文案')
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

    with ui.tab_panels(tabs, value=common_config_page).classes('w-full'):
        with ui.tab_panel(common_config_page).style(tab_panel_css):
            with ui.row():
                
                select_platform = ui.select(
                    label='平台', 
                    options=platform_options, 
                    value=config.get("platform")
                ).style("width:200px;")

                input_room_display_id = ui.input(label='直播间号', placeholder='一般为直播间URL最后/后面的字母或数字', value=config.get("room_display_id")).style("width:200px;").tooltip('一般为直播间URL最后/后面的字母或数字')

                select_chat_type = ui.select(
                    label='大语言模型', 
                    options=chat_type_options, 
                    value=config.get("chat_type")
                ).style("width:200px;").tooltip('选用的LLM类型。相关的弹幕信息等会传递给此LLM进行推理，获取回答')

                select_visual_body = ui.select(
                    label='虚拟身体', 
                    options=visual_body_options, 
                    value=config.get("visual_body")
                ).style("width:200px;").tooltip('选用的虚拟身体类型。如果使用VTS对接，就选其他，用什么展示身体就选什么，大部分对接的选项需要单独启动对应的服务端程序，请勿随便选择。')

                select_audio_synthesis_type = ui.select(
                    label='语音合成', 
                    options=audio_synthesis_type_options, 
                    value=config.get("audio_synthesis_type")
                ).style("width:200px;").tooltip('选用的TTS类型，所有的文本内容最终都将通过此TTS进行语音合成')

            with ui.row():
                select_need_lang = ui.select(
                    label='回复语言', 
                    options={'none': '所有', 'zh': '中文', 'en': '英文', 'jp': '日文'}, 
                    value=config.get("need_lang")
                ).style("width:200px;").tooltip('限制回复的语言，如：选中中文，则只会回复中文提问，其他语言将被跳过')

                input_before_prompt = ui.input(label='提示词前缀', placeholder='此配置会追加在弹幕前，再发送给LLM处理', value=config.get("before_prompt")).style("width:200px;").tooltip('此配置会追加在弹幕前，再发送给LLM处理')
                input_after_prompt = ui.input(label='提示词后缀', placeholder='此配置会追加在弹幕后，再发送给LLM处理', value=config.get("after_prompt")).style("width:200px;").tooltip('此配置会追加在弹幕后，再发送给LLM处理')
                switch_comment_template_enable = ui.switch('启用弹幕模板', value=config.get("comment_template", "enable")).style(switch_internal_css).tooltip('此配置会追加在弹幕后，再发送给LLM处理')
                input_comment_template_copywriting = ui.input(label='弹幕模板', value=config.get("comment_template", "copywriting"), placeholder='此配置会对弹幕内容进行修改，{}内为变量，会被替换为指定内容，请勿随意删除变量').style("width:200px;").tooltip('此配置会对弹幕内容进行修改，{}内为变量，会被替换为指定内容，请勿随意删除变量')
                switch_reply_template_enable = ui.switch('启用回复模板', value=config.get("reply_template", "enable")).style(switch_internal_css).tooltip('此配置会在LLM输出的答案中进行回复内容的重新构建')
                input_reply_template_username_max_len = ui.input(label='回复用户名的最大长度', value=config.get("reply_template", "username_max_len"), placeholder='回复用户名的最大长度').style("width:200px;").tooltip('回复用户名的最大长度')
                textarea_reply_template_copywriting = ui.textarea(
                    label='回复模板', 
                    placeholder='此配置会对LLM回复内容进行修改，{}内为变量，会被替换为指定内容，请勿随意删除变量', 
                    value=textarea_data_change(config.get("reply_template", "copywriting"))
                ).style("width:500px;").tooltip('此配置会对LLM回复内容进行修改，{}内为变量，会被替换为指定内容，请勿随意删除变量')

            with ui.expansion('功能管理', icon="settings", value=True).classes('w-full'):

                with ui.card().style(card_css):
                    ui.label('平台相关')
                    with ui.card().style(card_css):
                        ui.label('哔哩哔哩')
                        with ui.row():
                            select_bilibili_login_type = ui.select(
                                label='登录方式',
                                options={'cookie': 'cookie', '手机扫码': '手机扫码', '手机扫码-终端': '手机扫码-终端', 'open_live': '开放平台', '不登录': '不登录'},
                                value=config.get("bilibili", "login_type")
                            ).style("width:100px")
                            input_bilibili_cookie = ui.input(label='cookie', placeholder='b站登录后F12抓网络包获取cookie，强烈建议使用小号！有封号风险，虽然实际上没听说有人被封过', value=config.get("bilibili", "cookie")).style("width:500px;").tooltip('b站登录后F12抓网络包获取cookie，强烈建议使用小号！有封号风险，虽然实际上没听说有人被封过')
                            input_bilibili_ac_time_value = ui.input(label='ac_time_value', placeholder='b站登录后，F12控制台，输入window.localStorage.ac_time_value获取(如果没有，请重新登录)', value=config.get("bilibili", "ac_time_value")).style("width:500px;").tooltip('仅在平台：哔哩哔哩，情况下可选填写。b站登录后，F12控制台，输入window.localStorage.ac_time_value获取(如果没有，请重新登录)')
                        with ui.row():
                            with ui.card().style(card_css):
                                ui.label('开放平台')
                                with ui.row():
                                    input_bilibili_open_live_ACCESS_KEY_ID = ui.input(label='ACCESS_KEY_ID', value=config.get("bilibili", "open_live", "ACCESS_KEY_ID"), placeholder='开放平台ACCESS_KEY_ID').style("width:160px;").tooltip('仅在平台：哔哩哔哩2，登录方式：开放平台，情况下填写。开放平台ACCESS_KEY_ID')
                                    input_bilibili_open_live_ACCESS_KEY_SECRET = ui.input(label='ACCESS_KEY_SECRET', value=config.get("bilibili", "open_live", "ACCESS_KEY_SECRET"), placeholder='开放平台ACCESS_KEY_SECRET').style("width:200px;").tooltip('仅在平台：哔哩哔哩2，登录方式：开放平台，情况下填写。开放平台ACCESS_KEY_SECRET')
                                    input_bilibili_open_live_APP_ID = ui.input(label='项目ID', value=config.get("bilibili", "open_live", "APP_ID"), placeholder='开放平台 创作者服务中心 项目ID').style("width:100px;").tooltip('仅在平台：哔哩哔哩2，登录方式：开放平台，情况下填写。开放平台 创作者服务中心 项目ID')
                                    input_bilibili_open_live_ROOM_OWNER_AUTH_CODE = ui.input(label='身份码', value=config.get("bilibili", "open_live", "ROOM_OWNER_AUTH_CODE"), placeholder='直播中心用户 身份码').style("width:100px;").tooltip('仅在平台：哔哩哔哩2，登录方式：开放平台，情况下填写。直播中心用户 身份码')
                    with ui.card().style(card_css):
                        ui.label('让弹幕飞')
                        with ui.row():
                            input_ordinaryroad_barrage_fly_ws_ip_port = ui.input(label='WebSocket地址', value=config.get("ordinaryroad_barrage_fly", "ws_ip_port"), placeholder='默认：ws://127.0.0.1:9898').style("width:300px;").tooltip('根据实际服务配置，填写WebSocket地址')
                            textarea_ordinaryroad_barrage_fly_taskIds = ui.textarea(
                                label='任务ID', 
                                placeholder='成功监听的任务在页面中可以复制对应的任务ID，可以自定义编辑多个（换行分隔）', 
                                value=textarea_data_change(config.get("ordinaryroad_barrage_fly", "taskIds"))
                            ).style("width:500px;").tooltip('成功监听的任务在页面中可以复制对应的任务ID，可以自定义编辑多个（换行分隔）')
                    with ui.card().style(card_css):
                        ui.label('twitch')
                        with ui.row():
                            input_twitch_token = ui.input(label='token', value=config.get("twitch", "token"), placeholder='访问 https://twitchapps.com/tmi/ 获取，格式为：oauth:xxx').style("width:300px;")
                            input_twitch_user = ui.input(label='用户名', value=config.get("twitch", "user"), placeholder='你的twitch账号用户名').style("width:300px;")
                            input_twitch_proxy_server = ui.input(label='HTTP代理IP地址', value=config.get("twitch", "proxy_server"), placeholder='代理软件，http协议监听的ip地址，一般为：127.0.0.1').style("width:200px;")
                            input_twitch_proxy_port = ui.input(label='HTTP代理端口', value=config.get("twitch", "proxy_port"), placeholder='代理软件，http协议监听的端口，一般为：1080').style("width:200px;")
                            
                if config.get("webui", "show_card", "common_config", "play_audio"):
                    with ui.card().style(card_css):
                        ui.label('音频播放')
                        with ui.row():
                            switch_play_audio_enable = ui.switch('启用', value=config.get("play_audio", "enable")).style(switch_internal_css)
                            switch_play_audio_text_split_enable = ui.switch('启用文本切分', value=config.get("play_audio", "text_split_enable")).style(switch_internal_css).tooltip('启用后会将LLM等待合成音频的消息根据内部切分算法切分成多个短句，以便TTS快速合成')
                            switch_play_audio_info_to_callback = ui.switch('音频信息回传给内部接口', value=config.get("play_audio", "info_to_callback")).style(switch_internal_css).tooltip('启用后，会在当前音频播放完毕后，将程序中等待播放的音频信息传递给内部接口，用于闲时任务的闲时清零功能。\n不过这个功能会一定程度的拖慢程序运行，如果你不需要闲时清零，可以关闭此功能来提高响应速度')
                            
                        with ui.row():
                            input_play_audio_interval_num_min = ui.input(label='间隔时间重复次数最小值', value=config.get("play_audio", "interval_num_min"), placeholder='普通音频播放间隔时间，重复睡眠次数最小值。会在最大最小值之间随机生成一个重复次数，就是 次数 x 时间 = 最终间隔时间').tooltip('普通音频播放间隔时间重复睡眠次数最小值。会在最大最小值之间随机生成一个重复次数，就是 次数 x 时间 = 最终间隔时间')
                            input_play_audio_interval_num_max = ui.input(label='间隔时间重复次数最大值', value=config.get("play_audio", "interval_num_max"), placeholder='普通音频播放间隔时间，重复睡眠次数最大值。会在最大最小值之间随机生成一个重复次数，就是 次数 x 时间 = 最终间隔时间').tooltip('普通音频播放间隔时间重复睡眠次数最大值。会在最大最小值之间随机生成一个重复次数，就是 次数 x 时间 = 最终间隔时间')
                            input_play_audio_normal_interval_min = ui.input(label='普通音频播放间隔最小值', value=config.get("play_audio", "normal_interval_min"), placeholder='就是弹幕回复、唱歌等音频播放结束后到播放下一个音频之间的一个间隔时间，单位：秒').tooltip('就是弹幕回复、唱歌等音频播放结束后到播放下一个音频之间的一个间隔时间，单位：秒。次数 x 时间 = 最终间隔时间')
                            input_play_audio_normal_interval_max = ui.input(label='普通音频播放间隔最大值', value=config.get("play_audio", "normal_interval_max"), placeholder='就是弹幕回复、唱歌等音频播放结束后到播放下一个音频之间的一个间隔时间，单位：秒').tooltip('就是弹幕回复、唱歌等音频播放结束后到播放下一个音频之间的一个间隔时间，单位：秒。次数 x 时间 = 最终间隔时间')
                            
                            input_play_audio_out_path = ui.input(label='音频输出路径', placeholder='音频文件合成后存储的路径，支持相对路径或绝对路径', value=config.get("play_audio", "out_path")).tooltip('音频文件合成后存储的路径，支持相对路径或绝对路径')
                            select_play_audio_player = ui.select(
                                label='音频播放器',
                                options={'pygame': 'pygame', 'audio_player_v2': 'audio_player_v2', 'audio_player': 'audio_player'},
                                value=config.get("play_audio", "player")
                            ).style("width:200px").tooltip('选用的音频播放器，默认pygame不需要再安装其他程序。audio player需要单独安装对接，详情看视频教程')
                    
                        with ui.card().style(card_css):
                            ui.label('audio_player')
                            with ui.row():
                                input_audio_player_api_ip_port = ui.input(
                                    label='API地址', 
                                    value=config.get("audio_player", "api_ip_port"), 
                                    placeholder='audio_player的API地址，只需要 http://ip:端口 即可',
                                    validation={
                                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                                    }
                                ).style("width:200px;").tooltip('仅在 音频播放器：audio_player等，情况下填写。audio_player的API地址，只需要 http://ip:端口 即可')

                        with ui.card().style(card_css):
                            ui.label('音频随机变速')     
                            with ui.grid(columns=3):
                                switch_audio_random_speed_normal_enable = ui.switch('普通音频变速', value=config.get("audio_random_speed", "normal", "enable")).style(switch_internal_css).tooltip('是否启用 针对 普通音频的音频变速功能。此功能需要安装配置ffmpeg才能使用')
                                input_audio_random_speed_normal_speed_min = ui.input(label='速度下限', value=config.get("audio_random_speed", "normal", "speed_min")).style("width:200px;").tooltip('音频变速的下限，最终速度会在上下限之间随机一个值进行变速')
                                input_audio_random_speed_normal_speed_max = ui.input(label='速度上限', value=config.get("audio_random_speed", "normal", "speed_max")).style("width:200px;").tooltip('音频变速的上限，最终速度会在上下限之间随机一个值进行变速')
                            with ui.grid(columns=3):
                                switch_audio_random_speed_copywriting_enable = ui.switch('文案音频变速', value=config.get("audio_random_speed", "copywriting", "enable")).style(switch_internal_css).tooltip('是否启用 针对 文案页音频的音频变速功能。此功能需要安装配置ffmpeg才能使用')
                                input_audio_random_speed_copywriting_speed_min = ui.input(label='速度下限', value=config.get("audio_random_speed", "copywriting", "speed_min")).style("width:200px;").tooltip('音频变速的下限，最终速度会在上下限之间随机一个值进行变速')
                                input_audio_random_speed_copywriting_speed_max = ui.input(label='速度上限', value=config.get("audio_random_speed", "copywriting", "speed_max")).style("width:200px;").tooltip('音频变速的上限，最终速度会在上下限之间随机一个值进行变速')

                if config.get("webui", "show_card", "common_config", "filter"):
                    with ui.card().style(card_css):
                        ui.label('过滤')    
                        with ui.grid(columns=6):
                            textarea_filter_before_must_str = ui.textarea(label='弹幕触发前缀', placeholder='前缀必须携带其中任一字符串才能触发\n例如：配置#，那么这个会触发：#你好', value=textarea_data_change(config.get("filter", "before_must_str"))).style("width:200px;").tooltip("前缀必须携带其中任一字符串才能触发\n例如：配置#，那么这个会触发：#你好")
                            textarea_filter_after_must_str = ui.textarea(label='弹幕触发后缀', placeholder='后缀必须携带其中任一字符串才能触发\n例如：配置。那么这个会触发：你好。', value=textarea_data_change(config.get("filter", "before_must_str"))).style("width:200px;").tooltip("后缀必须携带其中任一字符串才能触发\n例如：配置。那么这个会触发：你好。")
                            textarea_filter_before_filter_str = ui.textarea(label='弹幕过滤前缀', placeholder='当前缀为其中任一字符串时，弹幕会被过滤\n例如：配置#，那么这个会被过滤：#你好', value=textarea_data_change(config.get("filter", "before_filter_str"))).style("width:200px;").tooltip("当前缀为其中任一字符串时，弹幕会被过滤\n例如：配置#，那么这个会被过滤：#你好")
                            textarea_filter_after_filter_str = ui.textarea(label='弹幕过滤后缀', placeholder='当后缀为其中任一字符串时，弹幕会被过滤\n例如：配置#，那么这个会被过滤：你好#', value=textarea_data_change(config.get("filter", "before_filter_str"))).style("width:200px;").tooltip("当后缀为其中任一字符串时，弹幕会被过滤\n例如：配置#，那么这个会被过滤：你好#")
                            textarea_filter_before_must_str_for_llm = ui.textarea(label='LLM触发前缀', placeholder='前缀必须携带其中任一字符串才能触发LLM\n例如：配置#，那么这个会触发：#你好', value=textarea_data_change(config.get("filter", "before_must_str_for_llm"))).style("width:200px;").tooltip("前缀必须携带其中任一字符串才能触发LLM\n例如：配置#，那么这个会触发：#你好")
                            textarea_filter_after_must_str_for_llm = ui.textarea(label='LLM触发后缀', placeholder='后缀必须携带其中任一字符串才能触发LLM\n例如：配置。那么这个会触发：你好。', value=textarea_data_change(config.get("filter", "before_must_str_for_llm"))).style("width:200px;").tooltip('后缀必须携带其中任一字符串才能触发LLM\n例如：配置。那么这个会触发：你好。')
                            
                        with ui.row():
                            input_filter_max_len = ui.input(label='最大单词数', placeholder='最长阅读的英文单词数（空格分隔）', value=config.get("filter", "max_len")).style("width:150px;").tooltip('最长阅读的英文单词数（空格分隔）')
                            input_filter_max_char_len = ui.input(label='最大字符数', placeholder='最长阅读的字符数，双重过滤，避免溢出', value=config.get("filter", "max_char_len")).style("width:150px;").tooltip('最长阅读的字符数，双重过滤，避免溢出')
                            switch_filter_username_convert_digits_to_chinese = ui.switch('用户名中的数字转中文', value=config.get("filter", "username_convert_digits_to_chinese")).style(switch_internal_css).tooltip('用户名中的数字转中文')
                            switch_filter_emoji = ui.switch('弹幕表情过滤', value=config.get("filter", "emoji")).style(switch_internal_css)
                        with ui.grid(columns=5):
                            switch_filter_badwords_enable = ui.switch('违禁词过滤', value=config.get("filter", "badwords", "enable")).style(switch_internal_css)
                            switch_filter_badwords_discard = ui.switch('违禁语句丢弃', value=config.get("filter", "badwords", "discard")).style(switch_internal_css)
                            input_filter_badwords_path = ui.input(label='违禁词路径', value=config.get("filter", "badwords", "path"), placeholder='本地违禁词数据路径（你如果不需要，可以清空文件内容）').style("width:200px;").tooltip('本地违禁词数据路径（你如果不需要，可以清空文件内容）')
                            input_filter_badwords_bad_pinyin_path = ui.input(label='违禁拼音路径', value=config.get("filter", "badwords", "bad_pinyin_path"), placeholder='本地违禁拼音数据路径（你如果不需要，可以清空文件内容）').style("width:200px;").tooltip('本地违禁拼音数据路径（你如果不需要，可以清空文件内容）')
                            input_filter_badwords_replace = ui.input(label='违禁词替换', value=config.get("filter", "badwords", "replace"), placeholder='在不丢弃违禁语句的前提下，将违禁词替换成此项的文本').style("width:200px;").tooltip('在不丢弃违禁语句的前提下，将违禁词替换成此项的文本')
                        
                        with ui.expansion('消息遗忘&保留设置', icon="settings", value=True).classes('w-full'):
                            with ui.element('div').classes('p-2 bg-blue-100'):
                                ui.label("遗忘间隔 指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，但会保留最新的n个数据；保留数 指的是保留最新收到的数据的数量")
                            with ui.grid(columns=4):
                                input_filter_comment_forget_duration = ui.input(
                                    label='弹幕遗忘间隔', 
                                    placeholder='例：1', 
                                    value=config.get("filter", "comment_forget_duration")
                                ).style("width:200px;").tooltip('指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义')
                                input_filter_comment_forget_reserve_num = ui.input(label='弹幕保留数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "comment_forget_reserve_num")).style("width:200px;").tooltip('保留最新收到的数据的数量')
                                input_filter_gift_forget_duration = ui.input(label='礼物遗忘间隔', placeholder='指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义', value=config.get("filter", "gift_forget_duration")).style("width:200px;").tooltip('指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义')
                                input_filter_gift_forget_reserve_num = ui.input(label='礼物保留数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "gift_forget_reserve_num")).style("width:200px;").tooltip('保留最新收到的数据的数量')
                            with ui.grid(columns=4):
                                input_filter_entrance_forget_duration = ui.input(label='入场遗忘间隔', placeholder='指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义', value=config.get("filter", "entrance_forget_duration")).style("width:200px;").tooltip('指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义')
                                input_filter_entrance_forget_reserve_num = ui.input(label='入场保留数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "entrance_forget_reserve_num")).style("width:200px;").tooltip('保留最新收到的数据的数量')
                                input_filter_follow_forget_duration = ui.input(label='关注遗忘间隔', placeholder='指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义', value=config.get("filter", "follow_forget_duration")).style("width:200px;").tooltip('指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义')
                                input_filter_follow_forget_reserve_num = ui.input(label='关注保留数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "follow_forget_reserve_num")).style("width:200px;").tooltip('保留最新收到的数据的数量')
                            with ui.grid(columns=4):
                                input_filter_talk_forget_duration = ui.input(label='聊天遗忘间隔', placeholder='指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义', value=config.get("filter", "talk_forget_duration")).style("width:200px;").tooltip('指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义')
                                input_filter_talk_forget_reserve_num = ui.input(label='聊天保留数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "talk_forget_reserve_num")).style("width:200px;").tooltip('保留最新收到的数据的数量')
                                input_filter_schedule_forget_duration = ui.input(label='定时遗忘间隔', placeholder='指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义', value=config.get("filter", "schedule_forget_duration")).style("width:200px;").tooltip('指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义')
                                input_filter_schedule_forget_reserve_num = ui.input(label='定时保留数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "schedule_forget_reserve_num")).style("width:200px;").tooltip('保留最新收到的数据的数量')
                            with ui.grid(columns=4):
                                input_filter_idle_time_task_forget_duration = ui.input(label='闲时任务遗忘间隔', placeholder='指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义', value=config.get("filter", "idle_time_task_forget_duration")).style("width:200px;").tooltip('指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义')
                                input_filter_idle_time_task_forget_reserve_num = ui.input(label='闲时任务保留数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "idle_time_task_forget_reserve_num")).style("width:200px;").tooltip('保留最新收到的数据的数量')
                                input_filter_image_recognition_schedule_forget_duration = ui.input(label='图像识别遗忘间隔', placeholder='指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义', value=config.get("filter", "image_recognition_schedule_forget_duration")).style("width:200px;").tooltip('指的是每隔这个间隔时间（秒），就会丢弃这个间隔时间中接收到的数据，\n保留数据在以下配置中可以自定义')
                                input_filter_image_recognition_schedule_forget_reserve_num = ui.input(label='图像识别保留数', placeholder='保留最新收到的数据的数量', value=config.get("filter", "image_recognition_schedule_forget_reserve_num")).style("width:200px;").tooltip('保留最新收到的数据的数量')
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

                                with ui.element('div').classes('p-2 bg-blue-100'):
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
                            
            with ui.expansion('互动功能', icon="question_answer", value=True).classes('w-full'):

                if config.get("webui", "show_card", "common_config", "read_comment"):
                    with ui.card().style(card_css):
                        ui.label('念弹幕')
                        with ui.grid(columns=4):
                            switch_read_comment_enable = ui.switch('启用', value=config.get("read_comment", "enable")).style(switch_internal_css)
                            switch_read_comment_read_username_enable = ui.switch('念用户名', value=config.get("read_comment", "read_username_enable")).style(switch_internal_css)
                            input_read_comment_username_max_len = ui.input(label='用户名最大长度', value=config.get("read_comment", "username_max_len"), placeholder='需要保留的用户名的最大长度，超出部分将被丢弃').style("width:100px;").tooltip('需要保留的用户名的最大长度，超出部分将被丢弃')
                            switch_read_comment_voice_change = ui.switch('变声', value=config.get("read_comment", "voice_change")).style(switch_internal_css)
                        with ui.grid(columns=2):
                            textarea_read_comment_read_username_copywriting = ui.textarea(
                                label='念用户名文案', 
                                placeholder='念用户名时使用的文案，可以自定义编辑多个（换行分隔），实际中会随机一个使用', 
                                value=textarea_data_change(config.get("read_comment", "read_username_copywriting"))
                            ).style("width:500px;").tooltip('念用户名时使用的文案，可以自定义编辑多个（换行分隔），实际中会随机一个使用')
                        with ui.row():
                            switch_read_comment_periodic_trigger_enable = ui.switch('周期性触发启用', value=config.get("read_comment", "periodic_trigger", "enable")).style(switch_internal_css)
                            input_read_comment_periodic_trigger_periodic_time_min = ui.input(
                                label='触发周期最小值', 
                                value=config.get("read_comment", "periodic_trigger", "periodic_time_min"), 
                                placeholder='例如：5'
                            ).style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                            input_read_comment_periodic_trigger_periodic_time_max = ui.input(
                                label='触发周期最大值', 
                                value=config.get("read_comment", "periodic_trigger", "periodic_time_max"), 
                                placeholder='例如：10'
                            ).style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                            input_read_comment_periodic_trigger_trigger_num_min = ui.input(
                                label='触发次数最小值', 
                                value=config.get("read_comment", "periodic_trigger", "trigger_num_min"), 
                                placeholder='例如：0'
                            ).style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成')
                            input_read_comment_periodic_trigger_trigger_num_max = ui.input(
                                label='触发次数最大值', 
                                value=config.get("read_comment", "periodic_trigger", "trigger_num_max"), 
                                placeholder='例如：1'
                            ).style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成')
                
                if config.get("webui", "show_card", "common_config", "local_qa"):
                    with ui.card().style(card_css):
                        ui.label('本地问答')
                        with ui.row():
                            switch_local_qa_periodic_trigger_enable = ui.switch('周期性触发启用', value=config.get("local_qa", "periodic_trigger", "enable")).style(switch_internal_css)
                            input_local_qa_periodic_trigger_periodic_time_min = ui.input(label='触发周期最小值', value=config.get("local_qa", "periodic_trigger", "periodic_time_min"), placeholder='每隔这个周期的时间会触发n次此功能').style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                            input_local_qa_periodic_trigger_periodic_time_max = ui.input(label='触发周期最大值', value=config.get("local_qa", "periodic_trigger", "periodic_time_max"), placeholder='每隔这个周期的时间会触发n次此功能').style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                            input_local_qa_periodic_trigger_trigger_num_min = ui.input(label='触发次数最小值', value=config.get("local_qa", "periodic_trigger", "trigger_num_min"), placeholder='周期到后，会触发n次此功能').style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成') 
                            input_local_qa_periodic_trigger_trigger_num_max = ui.input(label='触发次数最大值', value=config.get("local_qa", "periodic_trigger", "trigger_num_max"), placeholder='周期到后，会触发n次此功能').style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成') 
                            
                        with ui.grid(columns=5):
                            switch_local_qa_text_enable = ui.switch('启用文本匹配', value=config.get("local_qa", "text", "enable")).style(switch_internal_css)
                            select_local_qa_text_type = ui.select(
                                label='弹幕日志类型',
                                options={'json': '自定义json', 'text': '一问一答'},
                                value=config.get("local_qa", "text", "type")
                            )
                            input_local_qa_text_file_path = ui.input(label='文本问答数据路径', placeholder='本地问答文本数据存储路径', value=config.get("local_qa", "text", "file_path")).style("width:200px;")
                            input_local_qa_text_similarity = ui.input(label='文本最低相似度', placeholder='最低文本匹配相似度，就是说用户发送的内容和本地问答库中设定的内容的最低相似度。\n低了就会被当做一般弹幕处理', value=config.get("local_qa", "text", "similarity")).style("width:200px;")
                            input_local_qa_text_username_max_len = ui.input(label='用户名最大长度', value=config.get("local_qa", "text", "username_max_len"), placeholder='需要保留的用户名的最大长度，超出部分将被丢弃').style("width:100px;")       
                        with ui.grid(columns=4):
                            switch_local_qa_audio_enable = ui.switch('启用音频匹配', value=config.get("local_qa", "audio", "enable")).style(switch_internal_css)
                            input_local_qa_audio_file_path = ui.input(label='音频存储路径', placeholder='本地问答音频文件存储路径', value=config.get("local_qa", "audio", "file_path")).style("width:200px;")
                            input_local_qa_audio_similarity = ui.input(label='音频最低相似度', placeholder='最低音频匹配相似度，就是说用户发送的内容和本地音频库中音频文件名的最低相似度。\n低了就会被当做一般弹幕处理', value=config.get("local_qa", "audio", "similarity")).style("width:200px;")
                        with ui.row():
                            input_local_qa_text_json_file_path = ui.input(label='json文件路径', placeholder='填写json文件路径，默认为本地问答文本数据存储路径', value=config.get("local_qa", "text", "file_path")).style("width:200px;").tooltip("填写json文件路径，默认为本地问答文本数据存储路径")

                            def local_qa_text_json_file_reload():
                                try:
                                    # 只做了个判空 所以别乱填
                                    if input_local_qa_text_json_file_path.value != "":
                                        textarea_local_qa_text_json_file_content.value = json.dumps(common.read_file(input_local_qa_text_json_file_path.value, "dict"), ensure_ascii=False, indent=3)
                                except Exception as e:
                                    logger.error(traceback.format_exc())
                                    ui.notify(f"文件路径有误或其他问题。报错：{str(e)}", position="top", type="negative")

                            button_local_qa_text_json_file_reload = ui.button('加载文件', on_click=lambda: local_qa_text_json_file_reload(), color=button_internal_color).style(button_internal_css)

                            textarea_local_qa_text_json_file_content = ui.textarea(label='JSON文件内容', placeholder='注意格式！').style("width:700px;")

                            local_qa_text_json_file_reload()
                
                if config.get("webui", "show_card", "common_config", "thanks"):
                    with ui.card().style(card_css):
                        ui.label('答谢')  
                        with ui.row():
                            input_thanks_username_max_len = ui.input(label='用户名最大长度', value=config.get("thanks", "username_max_len"), placeholder='需要保留的用户名的最大长度，超出部分将被丢弃').style("width:100px;")       
                        with ui.expansion('入场设置', icon="settings", value=True).classes('w-full'):
                            with ui.row():
                                switch_thanks_entrance_enable = ui.switch('启用入场欢迎', value=config.get("thanks", "entrance_enable")).style(switch_internal_css)
                                switch_thanks_entrance_random = ui.switch('随机选取', value=config.get("thanks", "entrance_random")).style(switch_internal_css)
                                textarea_thanks_entrance_copy = ui.textarea(label='入场文案', value=textarea_data_change(config.get("thanks", "entrance_copy")), placeholder='用户进入直播间的相关文案，请勿动 {username}，此字符串用于替换用户名').style("width:500px;")

                            with ui.row():
                                switch_thanks_entrance_periodic_trigger_enable = ui.switch('周期性触发启用', value=config.get("thanks", "entrance", "periodic_trigger", "enable")).style(switch_internal_css)
                                input_thanks_entrance_periodic_trigger_periodic_time_min = ui.input(label='触发周期最小值', value=config.get("thanks", "entrance", "periodic_trigger", "periodic_time_min"), placeholder='每隔这个周期的时间会触发n次此功能').style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                                input_thanks_entrance_periodic_trigger_periodic_time_max = ui.input(label='触发周期最大值', value=config.get("thanks", "entrance", "periodic_trigger", "periodic_time_max"), placeholder='每隔这个周期的时间会触发n次此功能').style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                                input_thanks_entrance_periodic_trigger_trigger_num_min = ui.input(label='触发次数最小值', value=config.get("thanks", "entrance", "periodic_trigger", "trigger_num_min"), placeholder='周期到后，会触发n次此功能').style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成') 
                                input_thanks_entrance_periodic_trigger_trigger_num_max = ui.input(label='触发次数最大值', value=config.get("thanks", "entrance", "periodic_trigger", "trigger_num_max"), placeholder='周期到后，会触发n次此功能').style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成') 
                        with ui.expansion('礼物设置', icon="settings", value=True).classes('w-full'):
                            with ui.row():
                                switch_thanks_gift_enable = ui.switch('启用礼物答谢', value=config.get("thanks", "gift_enable")).style(switch_internal_css)
                                switch_thanks_gift_random = ui.switch('随机选取', value=config.get("thanks", "gift_random")).style(switch_internal_css)
                                textarea_thanks_gift_copy = ui.textarea(label='礼物文案', value=textarea_data_change(config.get("thanks", "gift_copy")), placeholder='用户赠送礼物的相关文案，请勿动 {username} 和 {gift_name}，此字符串用于替换用户名和礼物名').style("width:500px;")
                                input_thanks_lowest_price = ui.input(label='最低答谢礼物价格', value=config.get("thanks", "lowest_price"), placeholder='设置最低答谢礼物的价格（元），低于这个设置的礼物不会触发答谢').style("width:100px;")
                            with ui.row():
                                switch_thanks_gift_periodic_trigger_enable = ui.switch('周期性触发启用', value=config.get("thanks", "gift", "periodic_trigger", "enable")).style(switch_internal_css)
                                input_thanks_gift_periodic_trigger_periodic_time_min = ui.input(label='触发周期最小值', value=config.get("thanks", "gift", "periodic_trigger", "periodic_time_min"), placeholder='每隔这个周期的时间会触发n次此功能').style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                                input_thanks_gift_periodic_trigger_periodic_time_max = ui.input(label='触发周期最大值', value=config.get("thanks", "gift", "periodic_trigger", "periodic_time_max"), placeholder='每隔这个周期的时间会触发n次此功能').style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                                input_thanks_gift_periodic_trigger_trigger_num_min = ui.input(label='触发次数最小值', value=config.get("thanks", "gift", "periodic_trigger", "trigger_num_min"), placeholder='周期到后，会触发n次此功能').style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成') 
                                input_thanks_gift_periodic_trigger_trigger_num_max = ui.input(label='触发次数最大值', value=config.get("thanks", "gift", "periodic_trigger", "trigger_num_max"), placeholder='周期到后，会触发n次此功能').style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成') 
                        with ui.expansion('关注设置', icon="settings", value=True).classes('w-full'):
                            with ui.row():
                                switch_thanks_follow_enable = ui.switch('启用关注答谢', value=config.get("thanks", "follow_enable")).style(switch_internal_css)
                                switch_thanks_follow_random = ui.switch('随机选取', value=config.get("thanks", "follow_random")).style(switch_internal_css)
                                textarea_thanks_follow_copy = ui.textarea(label='关注文案', value=textarea_data_change(config.get("thanks", "follow_copy")), placeholder='用户关注时的相关文案，请勿动 {username}，此字符串用于替换用户名').style("width:500px;")
                            with ui.row():
                                switch_thanks_follow_periodic_trigger_enable = ui.switch(
                                    '周期性触发启用', 
                                    value=config.get("thanks", "follow", "periodic_trigger", "enable")
                                ).style(switch_internal_css)
                                input_thanks_follow_periodic_trigger_periodic_time_min = ui.input(
                                    label='触发周期最小值', 
                                    value=config.get("thanks", "follow", "periodic_trigger", "periodic_time_min"), 
                                    placeholder='每隔这个周期的时间会触发n次此功能'
                                ).style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                                input_thanks_follow_periodic_trigger_periodic_time_max = ui.input(
                                    label='触发周期最大值', 
                                    value=config.get("thanks", "follow", "periodic_trigger", "periodic_time_max"), 
                                    placeholder='每隔这个周期的时间会触发n次此功能'
                                ).style("width:100px;").tooltip('每隔这个周期的时间会触发n次此功能，周期时间从最大最小值之间随机生成')
                                input_thanks_follow_periodic_trigger_trigger_num_min = ui.input(
                                    label='触发次数最小值', 
                                    value=config.get("thanks", "follow", "periodic_trigger", "trigger_num_min"), 
                                    placeholder='周期到后，会触发n次此功能'
                                ).style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成') 
                                input_thanks_follow_periodic_trigger_trigger_num_max = ui.input(
                                    label='触发次数最大值', 
                                    value=config.get("thanks", "follow", "periodic_trigger", "trigger_num_max"), 
                                    placeholder='周期到后，会触发n次此功能'
                                ).style("width:100px;").tooltip('周期到后，会触发n次此功能，次数从最大最小值之间随机生成') 
                        
                if config.get("webui", "show_card", "common_config", "choose_song"): 
                    with ui.card().style(card_css):
                        ui.label('点歌模式') 
                        with ui.row():
                            switch_choose_song_enable = ui.switch('启用', value=config.get("choose_song", "enable")).style(switch_internal_css)
                            textarea_choose_song_start_cmd = ui.textarea(
                                label='点歌触发命令', 
                                value=textarea_data_change(config.get("choose_song", "start_cmd")), 
                                placeholder='点歌触发命令，换行分隔，支持多个命令，弹幕发送触发（完全匹配才行）'
                            ).style("width:200px;").tooltip('点歌触发命令，换行分隔，支持多个命令，弹幕发送触发（完全匹配才行）')
                            textarea_choose_song_stop_cmd = ui.textarea(
                                label='取消点歌命令', 
                                value=textarea_data_change(config.get("choose_song", "stop_cmd")), 
                                placeholder='停止点歌命令，换行分隔，支持多个命令，弹幕发送触发（完全匹配才行）'
                            ).style("width:200px;").tooltip('停止点歌命令，换行分隔，支持多个命令，弹幕发送触发（完全匹配才行）')
                            textarea_choose_song_random_cmd = ui.textarea(
                                label='随机点歌命令', 
                                value=textarea_data_change(config.get("choose_song", "random_cmd")), 
                                placeholder='随机点歌命令，换行分隔，支持多个命令，弹幕发送触发（完全匹配才行）'
                            ).style("width:200px;").tooltip('随机点歌命令，换行分隔，支持多个命令，弹幕发送触发（完全匹配才行）')
                        with ui.row():
                            input_choose_song_song_path = ui.input(
                                label='歌曲路径', 
                                value=config.get("choose_song", "song_path"), 
                                placeholder='歌曲音频存放的路径，会自动读取音频文件'
                            ).style("width:200px;").tooltip('歌曲音频存放的路径，会自动读取音频文件')
                            input_choose_song_match_fail_copy = ui.input(
                                label='匹配失败文案', 
                                value=config.get("choose_song", "match_fail_copy"), 
                                placeholder='匹配失败返回的音频文案 注意 {content} 这个是用于替换用户发送的歌名的，请务必不要乱删！影响使用！'
                            ).style("width:300px;").tooltip('匹配失败返回的音频文案 注意 {content} 这个是用于替换用户发送的歌名的，请务必不要乱删！影响使用！')
                            input_choose_song_similarity = ui.input(
                                label='匹配最低相似度', 
                                value=config.get("choose_song", "similarity"), 
                                placeholder='最低音频匹配相似度，就是说用户发送的内容和本地音频库中音频文件名的最低相似度。\n低了就会被当做一般弹幕处理'
                            ).style("width:200px;").tooltip('最低音频匹配相似度，就是说用户发送的内容和本地音频库中音频文件名的最低相似度。\n低了就会被当做一般弹幕处理')
                
                if config.get("webui", "show_card", "common_config", "schedule"): 
                    with ui.card().style(card_css):
                        ui.label('定时任务')
                        with ui.row():
                            input_schedule_index = ui.input(label='任务索引', value="", placeholder='任务组的排序号，就是说第一个组是1，第二个组是2，以此类推。请填写纯正整数')
                            button_schedule_add = ui.button('增加任务组', on_click=schedule_add, color=button_internal_color).style(button_internal_css)
                            button_schedule_del = ui.button('删除任务组', on_click=lambda: schedule_del(input_schedule_index.value), color=button_internal_color).style(button_internal_css)
                        
                        schedule_var = {}
                        schedule_config_card = ui.card()
                        for index, schedule in enumerate(config.get("schedule")):
                            with schedule_config_card.style(card_css):
                                with ui.row():
                                    schedule_var[str(4 * index)] = ui.switch(text=f"启用任务#{index}", value=schedule["enable"]).style(switch_internal_css)
                                    schedule_var[str(4 * index + 1)] = ui.input(label=f"最小循环周期#{index}", value=schedule["time_min"], placeholder='定时任务循环的周期最小时长（秒），即每间隔这个周期就会执行一次').style("width:100px;").tooltip('定时任务循环的周期最小时长（秒），最终周期会从最大最小之间随机生成，即每间隔这个周期就会执行一次')
                                    schedule_var[str(4 * index + 2)] = ui.input(label=f"最大循环周期#{index}", value=schedule["time_max"], placeholder='定时任务循环的周期最大时长（秒），即每间隔这个周期就会执行一次').style("width:100px;").tooltip('定时任务循环的周期最小时长（秒），最终周期会从最大最小之间随机生成，即每间隔这个周期就会执行一次')
                                    schedule_var[str(4 * index + 3)] = ui.textarea(label=f"文案列表#{index}", value=textarea_data_change(schedule["copy"]), placeholder='存放文案的列表，通过空格或换行分割，通过{变量}来替换关键数据，可修改源码自定义功能').style("width:500px;").tooltip('存放文案的列表，通过空格或换行分割，通过{变量}来替换关键数据，可修改源码自定义功能')
                    
                if config.get("webui", "show_card", "common_config", "idle_time_task"): 
                    with ui.card().style(card_css):
                        ui.label('闲时任务')
                        with ui.row():
                            switch_idle_time_task_enable = ui.switch('启用', value=config.get("idle_time_task", "enable")).style(switch_internal_css)
                            select_idle_time_task_type = ui.select(
                                label='机制类型',
                                options={
                                    '待合成消息队列更新闲时': '待合成消息队列更新闲时', 
                                    '待播放音频队列更新闲时': '待播放音频队列更新闲时', 
                                    '直播间无消息更新闲时': '直播间无消息更新闲时',
                                },
                                value=config.get("idle_time_task", "type")
                            ).tooltip('闲时任务执行的逻辑，在不同逻辑下可以实现不同的触发效果。\n如果是用于带货，可以选用 待播放音频队列更新闲时，然后把触发值设为1，从而在音频数少于1的情况下才会触发闲时任务，有效抑制大量任务产生。\n如果用于不需要一直说话的场景，推荐使用：直播间无消息更新闲时，然后把间隔设大点，隔一段时间触发一次。')
                        with ui.row():
                            input_idle_time_task_idle_min_msg_queue_len_to_trigger = ui.input(
                                label='待合成消息队列个数小于此值时触发', 
                                value=config.get("idle_time_task", "min_msg_queue_len_to_trigger"), 
                                placeholder='待合成消息队列个数小于此值时，才会触发闲时任务'
                            ).style("width:250px;").tooltip('待合成消息队列个数小于此值时，才会触发闲时任务')
                            input_idle_time_task_idle_min_audio_queue_len_to_trigger = ui.input(
                                label='待播放音频队列个数小于此值时触发', 
                                value=config.get("idle_time_task", "min_audio_queue_len_to_trigger"), 
                                placeholder='待播放音频队列个数小于此值时，才会触发闲时任务'
                            ).style("width:250px;").tooltip('待播放音频队列个数小于此值时，才会触发闲时任务')
                            
                        with ui.row():
                            input_idle_time_task_idle_time_min = ui.input(
                                label='最小闲时时间', 
                                value=config.get("idle_time_task", "idle_time_min"), 
                                placeholder='最小闲时间隔时间（正整数，单位：秒），就是在没有弹幕情况下经过的时间'
                            ).style("width:150px;").tooltip('最小闲时间隔时间（正整数，单位：秒），就是在没有弹幕情况下经过的时间')
                            input_idle_time_task_idle_time_max = ui.input(
                                label='最大闲时时间', 
                                value=config.get("idle_time_task", "idle_time_max"), 
                                placeholder='最大闲时间隔时间（正整数，单位：秒），就是在没有弹幕情况下经过的时间'
                            ).style("width:150px;").tooltip('最大闲时间隔时间（正整数，单位：秒），就是在没有弹幕情况下经过的时间')
                            input_idle_time_task_wait_play_audio_num_threshold = ui.input(
                                label='等待播放音频数量阈值', 
                                value=config.get("idle_time_task", "wait_play_audio_num_threshold"), 
                                placeholder='当等待播放音频数量超过这个阈值，将会在音频播放完毕后触发闲时时间减少到设定的缩减值，旨在控制闲时任务触发总量'
                            ).style("width:150px;").tooltip('当等待播放音频数量超过这个阈值，将会在音频播放完毕后触发闲时时间减少到设定的缩减值，旨在控制闲时任务触发总量')
                            input_idle_time_task_idle_time_reduce_to = ui.input(label='闲时计时减小到', value=config.get("idle_time_task", "idle_time_reduce_to"), placeholder='达到阈值情况下，闲时计时缩减到的数值').style("width:150px;").tooltip('达到阈值情况下，闲时计时缩减到的数值')
                            
                        with ui.row():
                            ui.label('刷新闲时计时的消息类型')
                            # 类型列表
                            idle_time_task_trigger_type_list = ["comment", "gift", "entrance", "follow"]
                            idle_time_task_trigger_type_mapping = {
                                "comment": "弹幕",
                                "gift": "礼物",
                                "entrance": "入场",
                                "follow": "关注",
                            }
                            idle_time_task_trigger_type_var = {}
                            
                            for index, idle_time_task_trigger_type in enumerate(idle_time_task_trigger_type_list):
                                if idle_time_task_trigger_type in config.get("idle_time_task", "trigger_type"):
                                    idle_time_task_trigger_type_var[str(index)] = ui.checkbox(text=idle_time_task_trigger_type_mapping[idle_time_task_trigger_type], value=True)
                                else:
                                    idle_time_task_trigger_type_var[str(index)] = ui.checkbox(text=idle_time_task_trigger_type_mapping[idle_time_task_trigger_type], value=False)
                    

                        with ui.row():
                            switch_idle_time_task_copywriting_enable = ui.switch('文案模式', value=config.get("idle_time_task", "copywriting", "enable")).style(switch_internal_css)
                            switch_idle_time_task_copywriting_random = ui.switch('随机文案', value=config.get("idle_time_task", "copywriting", "random")).style(switch_internal_css)
                            textarea_idle_time_task_copywriting_copy = ui.textarea(
                                label='文案列表', 
                                value=textarea_data_change(config.get("idle_time_task", "copywriting", "copy")), 
                                placeholder='文案列表，文案之间用换行分隔，文案会丢LLM进行处理后直接合成返回的结果'
                            ).style("width:800px;").tooltip('文案列表，文案之间用换行分隔，文案会丢LLM进行处理后直接合成返回的结果')
                        
                        with ui.row():
                            switch_idle_time_task_comment_enable = ui.switch('弹幕触发LLM模式', value=config.get("idle_time_task", "comment", "enable")).style(switch_internal_css)
                            switch_idle_time_task_comment_random = ui.switch('随机弹幕', value=config.get("idle_time_task", "comment", "random")).style(switch_internal_css)
                            textarea_idle_time_task_comment_copy = ui.textarea(
                                label='弹幕列表', 
                                value=textarea_data_change(config.get("idle_time_task", "comment", "copy")), 
                                placeholder='弹幕列表，弹幕之间用换行分隔，文案会丢LLM进行处理后直接合成返回的结果'
                            ).style("width:800px;").tooltip('弹幕列表，弹幕之间用换行分隔，文案会丢LLM进行处理后直接合成返回的结果')
                        with ui.row():
                            switch_idle_time_task_local_audio_enable = ui.switch('本地音频模式', value=config.get("idle_time_task", "local_audio", "enable")).style(switch_internal_css)
                            switch_idle_time_task_local_audio_random = ui.switch('随机本地音频', value=config.get("idle_time_task", "local_audio", "random")).style(switch_internal_css)
                            textarea_idle_time_task_local_audio_path = ui.textarea(
                                label='本地音频路径列表', 
                                value=textarea_data_change(config.get("idle_time_task", "local_audio", "path")), 
                                placeholder='本地音频路径列表，相对/绝对路径之间用换行分隔，音频文件会直接丢进音频播放队列'
                            ).style("width:800px;").tooltip('本地音频路径列表，相对/绝对路径之间用换行分隔，音频文件会直接丢进音频播放队列')

                if config.get("webui", "show_card", "common_config", "search_online"):      
                    with ui.card().style(card_css):
                        ui.label('联网搜索')
                        with ui.row():
                            switch_search_online_enable = ui.switch('启用', value=config.get("search_online", "enable")).style(switch_internal_css) 
                            switch_search_online_keyword_enable = ui.switch('关键词触发', value=config.get("search_online", "keyword_enable")).style(switch_internal_css) 
                            textarea_search_online_before_keyword = ui.textarea(
                                label='关键词前缀', 
                                placeholder='前缀必须携带其中任一字符串才能触发联网搜索\n例如：配置 【联网：】那么这个会触发：联网：杭州天气', 
                                value=textarea_data_change(config.get("search_online", "before_keyword"))
                            ).style("width:200px;").tooltip('前缀必须携带其中任一字符串才能触发联网搜索\n例如：配置 【联网：】那么这个会触发：联网：杭州天气')
                            
                            select_search_online_engine = ui.select(
                                label='搜索引擎',
                                options={'baidu': '百度搜索', 'google': '谷歌搜索'},
                                value=config.get("search_online", "engine")
                            ).style("width:100px;").tooltip('使用的搜索引擎')
                            input_search_online_engine_id = ui.input(label='引擎ID', value=config.get("search_online", "engine_id"), placeholder='默认：1，不建议修改').style("width:100px;").tooltip('就是单个引擎可能会有多种搜索方式，目前仅谷歌有2种，默认不建议修改')
                            input_search_online_count = ui.input(label='检索的文章数', value=config.get("search_online", "count"), placeholder='默认为：1，但有时候可能文章内容解析出来是空的，可以适当扩大检索数').style("width:100px;").tooltip('默认为：1，但有时候可能文章内容解析出来是空的，可以适当扩大检索数')
                            input_search_online_resp_template = ui.input(label='结果模板', value=config.get("search_online", "resp_template"), placeholder='检索后数据会以这个模板格式生成问题，请不要删除{}的两个变量，会导致无法运行').style("width:500px;").tooltip('检索后数据会以这个模板格式生成问题，请不要删除{}的两个变量，会导致无法运行')
                            input_search_online_http_proxy = ui.input(
                                label='HTTP代理地址', 
                                value=config.get("search_online", "http_proxy"), 
                                placeholder='http代理地址，需要走代理时配置此项。',
                                validation={
                                    '请输入正确格式的URL': lambda value: common.is_url_check(value),
                                }
                            ).style("width:200px;").tooltip('http代理地址，需要走代理时配置此项。')
                            input_search_online_https_proxy = ui.input(
                                label='HTTPS代理地址', 
                                value=config.get("search_online", "https_proxy"), 
                                placeholder='https代理地址，需要走代理时配置此项。',
                                validation={
                                    '请输入正确格式的URL': lambda value: common.is_url_check(value),
                                }
                            ).style("width:200px;").tooltip('https代理地址，需要走代理时配置此项。')
                        
                if config.get("webui", "show_card", "common_config", "trends_copywriting"):        
                    with ui.card().style(card_css):
                        ui.label('动态文案')
                        with ui.row():
                            switch_trends_copywriting_enable = ui.switch('启用', value=config.get("trends_copywriting", "enable")).style(switch_internal_css)
                            select_trends_copywriting_llm_type = ui.select(
                                label='LLM类型',
                                options=chat_type_options,
                                value=config.get("trends_copywriting", "llm_type")
                            ).style("width:200px;")
                            switch_trends_copywriting_random_play = ui.switch('随机播放', value=config.get("trends_copywriting", "random_play")).style(switch_internal_css)
                            input_trends_copywriting_play_interval = ui.input(label='文案播放间隔', value=config.get("trends_copywriting", "play_interval"), placeholder='文案于文案之间的播放间隔时间（秒）').style("width:200px;").tooltip('文案于文案之间的播放间隔时间（秒）')
                        
                        with ui.row():
                            input_trends_copywriting_index = ui.input(label='文案索引', value="", placeholder='文案组的排序号，就是说第一个组是1，第二个组是2，以此类推。请填写纯正整数').tooltip('文案组的排序号，就是说第一个组是1，第二个组是2，以此类推。请填写纯正整数')
                            button_trends_copywriting_add = ui.button('增加文案组', on_click=trends_copywriting_add, color=button_internal_color).style(button_internal_css)
                            button_trends_copywriting_del = ui.button('删除文案组', on_click=lambda: trends_copywriting_del(input_trends_copywriting_index.value), color=button_internal_color).style(button_internal_css)
                        
                        trends_copywriting_copywriting_var = {}
                        trends_copywriting_config_card = ui.card()
                        for index, trends_copywriting_copywriting in enumerate(config.get("trends_copywriting", "copywriting")):
                            with trends_copywriting_config_card.style(card_css):
                                with ui.row():
                                    trends_copywriting_copywriting_var[str(3 * index)] = ui.input(label=f"文案路径#{index + 1}", value=trends_copywriting_copywriting["folder_path"], placeholder='文案文件存储的文件夹路径').style("width:200px;").tooltip('文案文件存储的文件夹路径')
                                    trends_copywriting_copywriting_var[str(3 * index + 1)] = ui.switch(text=f"提示词转换#{index + 1}", value=trends_copywriting_copywriting["prompt_change_enable"])
                                    trends_copywriting_copywriting_var[str(3 * index + 2)] = ui.input(label=f"提示词转换内容#{index + 1}", value=trends_copywriting_copywriting["prompt_change_content"], placeholder='使用此提示词内容对文案内容进行转换后再进行合成，使用的LLM为聊天类型配置').style("width:500px;").tooltip('使用此提示词内容对文案内容进行转换后再进行合成，使用的LLM为聊天类型配置')
                
                if config.get("webui", "show_card", "common_config", "key_mapping"):  
                    with ui.card().style(card_css):
                        ui.label('按键/文案/音频/串口/图片 映射')
                        with ui.row():
                            switch_key_mapping_enable = ui.switch('启用', value=config.get("key_mapping", "enable")).style(switch_internal_css)
                            input_key_mapping_start_cmd = ui.input(
                                label='命令前缀', 
                                value=config.get("key_mapping", "start_cmd"), 
                                placeholder='想要触发此功能必须以这个字符串做为命令起始，不然将不会被解析为按键映射命令'
                            ).style("width:200px;").tooltip('想要触发此功能必须以这个字符串做为命令起始，不然将不会被解析为按键映射命令')
                            select_key_mapping_type = ui.select(
                                label='捕获类型',
                                options={'弹幕': '弹幕', '回复': '回复', '弹幕+回复': '弹幕+回复'},
                                value=config.get("key_mapping", "type")
                            ).style("width:200px").tooltip('什么类型的数据会触发这个板块的功能')
                        with ui.row():
                            
                            select_key_mapping_key_trigger_type = ui.select(
                                label='按键触发类型',
                                options={'不启用': '不启用', '关键词': '关键词', '礼物': '礼物', '关键词+礼物': '关键词+礼物'},
                                value=config.get("key_mapping", "key_trigger_type")
                            ).style("width:120px").tooltip('什么类型的数据会触发按键映射')
                            switch_key_mapping_key_single_sentence_trigger_once_enable = ui.switch('单句仅触发一次（按键）', value=config.get("key_mapping", "key_single_sentence_trigger_once")).style(switch_internal_css).tooltip('一句话的数据，是否只让这句话触发一次按键映射，因为一句话中可能会有多个关键词，触发多次')
                            select_key_mapping_copywriting_trigger_type = ui.select(
                                label='文案触发类型',
                                options={'不启用': '不启用', '关键词': '关键词', '礼物': '礼物', '关键词+礼物': '关键词+礼物'},
                                value=config.get("key_mapping", "copywriting_trigger_type")
                            ).style("width:120px").tooltip('什么类型的数据会触发文案映射')
                            switch_key_mapping_copywriting_single_sentence_trigger_once_enable = ui.switch('单句仅触发一次（文案）', value=config.get("key_mapping", "copywriting_single_sentence_trigger_once")).style(switch_internal_css).tooltip('一句话的数据，是否只让这句话触发一次文案映射，因为一句话中可能会有多个关键词，触发多次')
                            select_key_mapping_local_audio_trigger_type = ui.select(
                                label='本地音频触发类型',
                                options={'不启用': '不启用', '关键词': '关键词', '礼物': '礼物', '关键词+礼物': '关键词+礼物'},
                                value=config.get("key_mapping", "local_audio_trigger_type")
                            ).style("width:120px").tooltip('什么类型的数据会触发本地音频映射')
                            switch_key_mapping_local_audio_single_sentence_trigger_once_enable = ui.switch('单句仅触发一次（文案）', value=config.get("key_mapping", "local_audio_single_sentence_trigger_once")).style(switch_internal_css).tooltip('一句话的数据，是否只让这句话触发一次本地音频映射，因为一句话中可能会有多个关键词，触发多次')
                            select_key_mapping_serial_trigger_type = ui.select(
                                label='串口触发类型',
                                options={'不启用': '不启用', '关键词': '关键词', '礼物': '礼物', '关键词+礼物': '关键词+礼物'},
                                value=config.get("key_mapping", "serial_trigger_type")
                            ).style("width:120px").tooltip('什么类型的数据会触发文案映射')
                            switch_key_mapping_serial_single_sentence_trigger_once_enable = ui.switch('单句仅触发一次（串口）', value=config.get("key_mapping", "serial_single_sentence_trigger_once")).style(switch_internal_css).tooltip('一句话的数据，是否只让这句话触发一次文案映射，因为一句话中可能会有多个关键词，触发多次')
                            select_key_mapping_img_path_trigger_type = ui.select(
                                label='图片触发类型',
                                options={'不启用': '不启用', '关键词': '关键词', '礼物': '礼物', '关键词+礼物': '关键词+礼物'},
                                value=config.get("key_mapping", "img_path_trigger_type")
                            ).style("width:120px").tooltip('什么类型的数据会触发文案映射')
                            switch_key_mapping_img_path_single_sentence_trigger_once_enable = ui.switch('单句仅触发一次（图片显示）', value=config.get("key_mapping", "img_path_single_sentence_trigger_once")).style(switch_internal_css).tooltip('一句话的数据，是否只让这句话触发一次文案映射，因为一句话中可能会有多个关键词，触发多次')
                            
                        with ui.row():
                            input_key_mapping_index = ui.input(label='配置索引', value="", placeholder='配置组的排序号，就是说第一个组是1，第二个组是2，以此类推。请填写纯正整数').tooltip('配置组的排序号，就是说第一个组是1，第二个组是2，以此类推。请填写纯正整数')
                            button_key_mapping_add = ui.button('增加配置组', on_click=key_mapping_add, color=button_internal_color).style(button_internal_css)
                            button_key_mapping_del = ui.button('删除配置组', on_click=lambda: key_mapping_del(input_key_mapping_index.value), color=button_internal_color).style(button_internal_css)
                        
                        
                        key_mapping_config_var = {}
                        key_mapping_config_card = ui.card()
                        for index, key_mapping_config in enumerate(config.get("key_mapping", "config")):
                            with key_mapping_config_card.style(card_css):
                                with ui.row():
                                    num = 9
                                    key_mapping_config_var[str(num * index)] = ui.textarea(label=f"关键词#{index + 1}", value=textarea_data_change(key_mapping_config["keywords"]), placeholder='此处输入触发的关键词，多个请以换行分隔').style("width:100px;").tooltip('此处输入触发的关键词，多个请以换行分隔')
                                    key_mapping_config_var[str(num * index + 1)] = ui.textarea(label=f"礼物#{index + 1}", value=textarea_data_change(key_mapping_config["gift"]), placeholder='此处输入触发的礼物名，多个请以换行分隔').style("width:100px;").tooltip('此处输入触发的礼物名，多个请以换行分隔')
                                    key_mapping_config_var[str(num * index + 2)] = ui.textarea(label=f"按键#{index + 1}", value=textarea_data_change(key_mapping_config["keys"]), placeholder='此处输入你要映射的按键，多个按键请以换行分隔（按键名参考pyautogui规则）').style("width:100px;").tooltip('此处输入你要映射的按键，多个按键请以换行分隔（按键名参考pyautogui规则）')
                                    key_mapping_config_var[str(num * index + 3)] = ui.input(label=f"相似度#{index + 1}", value=key_mapping_config["similarity"], placeholder='关键词与用户输入的相似度，默认1即100%').style("width:50px;").tooltip('关键词与用户输入的相似度，默认1即100%')
                                    key_mapping_config_var[str(num * index + 4)] = ui.textarea(label=f"文案#{index + 1}", value=textarea_data_change(key_mapping_config["copywriting"]), placeholder='此处输入触发后合成的文案内容，多个请以换行分隔').style("width:300px;").tooltip('此处输入触发后合成的文案内容，多个请以换行分隔')
                                    key_mapping_config_var[str(num * index + 5)] = ui.textarea(label=f"本地音频#{index + 1}", value=textarea_data_change(key_mapping_config["local_audio"]), placeholder='此处输入触发后播放的本地音频路径，多个请以换行分隔').style("width:300px;").tooltip('此处输入触发后播放的本地音频路径，多个请以换行分隔')
                                    key_mapping_config_var[str(num * index + 6)] = ui.input(label=f"串口名#{index + 1}", value=key_mapping_config["serial_name"], placeholder='例如：COM1').style("width:100px;").tooltip('串口页配置的串口名，例如：COM1')
                                    key_mapping_config_var[str(num * index + 7)] = ui.textarea(label=f"串口发送内容#{index + 1}", value=textarea_data_change(key_mapping_config["serial_send_data"]), placeholder='多个请以换行分隔，ASCII例如：open led\nHEX例如（2个字符的十六进制字符）：313233').style("width:300px;").tooltip('此处输入发送到串口的数据内容，数据类型根据串口页设置决定，多个请以换行分隔')
                                    key_mapping_config_var[str(num * index + 8)] = ui.textarea(label=f"图片路径#{index + 1}", value=textarea_data_change(key_mapping_config["img_path"]), placeholder='多个请以换行分隔，支持绝对路径或相对路径，需要注意路径的斜杠哈').style("width:300px;").tooltip('此处输入图片路径，多个请以换行分隔。默认随机显示')
                                    
                                    # with ui.card().style(card_css):
                                    #     key_mapping_config_var[str(6 * index + 5)] = ui.textarea(label=f"串口号#{index + 1}", value=textarea_data_change(key_mapping_config["serial_name"]), placeholder='例如：COM1').style("width:100px;").tooltip('发送的串口名')
                                    #     key_mapping_config_var[str(6 * index + 5)] = ui.textarea(label=f"发送数据#{index + 1}", value=key_mapping_config["serial_data"], placeholder='根据类型填写，多个请以换行分隔').style("width:300px;").tooltip('根据类型填写，多个请以换行分隔')
                
            with ui.expansion('辅助软件对接', icon="extension", value=True).classes('w-full'):

                with ui.card().style(card_css):
                    ui.label("洛曦 直播弹幕助手")
                    with ui.row():
                        switch_luoxi_project_Live_Comment_Assistant_enable = ui.switch('启用', value=config.get("luoxi_project", "Live_Comment_Assistant", "enable")).style(switch_internal_css)
                        select_luoxi_project_Live_Comment_Assistant_version = ui.select(
                            label='对接版本',
                            options={'V0.1.x': 'V0.1.x'},
                            value=config.get("luoxi_project", "Live_Comment_Assistant", "version")
                        ).style("width:100px;").tooltip('版本，因为不同版本可能会有接口上的改动')
                        input_luoxi_project_Live_Comment_Assistant_api_ip_port = ui.input(
                            label='API地址', 
                            value=config.get("luoxi_project", "Live_Comment_Assistant", "api_ip_port"), 
                            placeholder='洛曦 直播弹幕助手 API地址'
                        ).style("width:200px;").tooltip('洛曦 直播弹幕助手 API地址')
                
                    with ui.card().style(card_css):
                        ui.label("触发类型")
                        with ui.row():    
                            # 类型列表源自 音频合成的所支持的type值
                            luoxi_project_Live_Comment_Assistant_type_list = [
                                "comment",
                                "comment_reply", 
                                "idle_time_task", 
                                "entrance_reply", 
                                "follow_reply", 
                                "gift_reply", 
                                "reread", 
                                "schedule",
                                "integral",
                                "key_mapping_copywriting"
                            ]
                            luoxi_project_Live_Comment_Assistant_type_mapping = {
                                "comment": "弹幕消息",
                                "comment_reply": "弹幕回复",
                                "idle_time_task": "闲时任务",
                                "entrance_reply": "入场回复",
                                "follow_reply": "关注回复",
                                "gift_reply": "礼物回复",
                                "reread": "复读",
                                "schedule": "定时任务",
                                "integral": "积分消息",
                                "key_mapping_copywriting": "按键映射-文案"
                            }
                            luoxi_project_Live_Comment_Assistant_type_var = {}
                            
                            for index, luoxi_project_Live_Comment_Assistant_type in enumerate(luoxi_project_Live_Comment_Assistant_type_list):
                                if luoxi_project_Live_Comment_Assistant_type in config.get("luoxi_project", "Live_Comment_Assistant", "type"):
                                    luoxi_project_Live_Comment_Assistant_type_var[str(index)] = ui.checkbox(
                                        text=luoxi_project_Live_Comment_Assistant_type_mapping[luoxi_project_Live_Comment_Assistant_type], 
                                        value=True
                                    )
                                else:
                                    luoxi_project_Live_Comment_Assistant_type_var[str(index)] = ui.checkbox(
                                        text=luoxi_project_Live_Comment_Assistant_type_mapping[luoxi_project_Live_Comment_Assistant_type], 
                                        value=False
                                    )
                    with ui.card().style(card_css):
                        ui.label("触发位置")
                        with ui.row(): 
                            luoxi_project_Live_Comment_Assistant_trigger_position_list = [
                                "消息产生时", 
                                "音频播放时",
                            ]
                            luoxi_project_Live_Comment_Assistant_trigger_position_mapping = {
                                "消息产生时": "消息产生时",
                                "音频播放时": "音频播放时",
                            }
                            luoxi_project_Live_Comment_Assistant_trigger_position_var = {}
                            
                            for index, luoxi_project_Live_Comment_Assistant_trigger_position in enumerate(luoxi_project_Live_Comment_Assistant_trigger_position_list):
                                if luoxi_project_Live_Comment_Assistant_trigger_position in config.get("luoxi_project", "Live_Comment_Assistant", "trigger_position"):
                                    luoxi_project_Live_Comment_Assistant_trigger_position_var[str(index)] = ui.checkbox(
                                        text=luoxi_project_Live_Comment_Assistant_trigger_position_mapping[luoxi_project_Live_Comment_Assistant_trigger_position], 
                                        value=True
                                    )
                                else:
                                    luoxi_project_Live_Comment_Assistant_trigger_position_var[str(index)] = ui.checkbox(
                                        text=luoxi_project_Live_Comment_Assistant_trigger_position_mapping[luoxi_project_Live_Comment_Assistant_trigger_position], 
                                        value=False
                                    )        
                

                if config.get("webui", "show_card", "common_config", "sd"):      
                    with ui.card().style(card_css):
                        ui.label('Stable Diffusion')
                        with ui.row():
                            switch_sd_enable = ui.switch('启用', value=config.get("sd", "enable")).style(switch_internal_css) 
                            select_sd_translate_type = ui.select(
                                label='翻译类型',
                                options={'none': '不启用', 'baidu': '百度翻译', 'google': '谷歌翻译'},
                                value=config.get("sd", "translate_type")
                            ).style("width:100px;").tooltip('针对触发的画图命令使用翻译页的配置，进行翻译后再丢给SD画图')
                            select_sd_prompt_llm_type = ui.select(
                                label='LLM类型',
                                options=chat_type_options,
                                value=config.get("sd", "prompt_llm", "type")
                            ).style("width:100px;")
                            input_sd_prompt_llm_before_prompt = ui.input(label='提示词前缀', value=config.get("sd", "prompt_llm", "before_prompt"), placeholder='LLM提示词前缀').style("width:300px;")
                            input_sd_prompt_llm_after_prompt = ui.input(label='提示词后缀', value=config.get("sd", "prompt_llm", "after_prompt"), placeholder='LLM提示词后缀').style("width:300px;")
                        with ui.row(): 
                            input_sd_trigger = ui.input(label='弹幕触发前缀', value=config.get("sd", "trigger"), placeholder='触发的关键词（弹幕头部触发）').style("width:200px;")
                            input_sd_ip = ui.input(label='IP地址', value=config.get("sd", "ip"), placeholder='服务运行的IP地址').style("width:200px;")
                            input_sd_port = ui.input(label='端口', value=config.get("sd", "port"), placeholder='服务运行的端口').style("width:100px;")
                            input_sd_negative_prompt = ui.input(label='负面提示词', value=config.get("sd", "negative_prompt"), placeholder='负面文本提示，用于指定与生成图像相矛盾或相反的内容').style("width:200px;")
                            input_sd_seed = ui.input(label='随机种子', value=config.get("sd", "seed"), placeholder='随机种子，用于控制生成过程的随机性。可以设置一个整数值，以获得可重复的结果。').style("width:100px;")
                            textarea_sd_styles = ui.textarea(label='图像风格', placeholder='样式列表，用于指定生成图像的风格。可以包含多个风格，例如 ["anime", "portrait"]', value=textarea_data_change(config.get("sd", "styles"))).style("width:200px;")
                        with ui.row():
                            input_sd_cfg_scale = ui.input(label='提示词相关性', value=config.get("sd", "cfg_scale"), placeholder='提示词相关性，无分类器指导信息影响尺度(Classifier Free Guidance Scale) -图像应在多大程度上服从提示词-较低的值会产生更有创意的结果。').style("width:100px;")
                            input_sd_steps = ui.input(label='生成图像步数', value=config.get("sd", "steps"), placeholder='生成图像的步数，用于控制生成的精确程度。').style("width:100px;") 
                            input_sd_hr_resize_x = ui.input(label='图像水平像素', value=config.get("sd", "hr_resize_x"), placeholder='生成图像的水平尺寸。').style("width:100px;")
                            input_sd_hr_resize_y = ui.input(label='图像垂直像素', value=config.get("sd", "hr_resize_y"), placeholder='生成图像的垂直尺寸。').style("width:100px;")
                            input_sd_denoising_strength = ui.input(label='去噪强度', value=config.get("sd", "denoising_strength"), placeholder='去噪强度，用于控制生成图像中的噪点。').style("width:100px;")
                        with ui.row():
                            switch_sd_enable_hr = ui.switch('高分辨率生成', value=config.get("sd", "enable_hr")).style(switch_internal_css)
                            input_sd_hr_scale = ui.input(label='高分辨率缩放因子', value=config.get("sd", "hr_scale"), placeholder='高分辨率缩放因子，用于指定生成图像的高分辨率缩放级别。').style("width:200px;")
                            input_sd_hr_second_pass_steps = ui.input(label='高分生二次传递步数', value=config.get("sd", "hr_second_pass_steps"), placeholder='高分辨率生成的第二次传递步数。').style("width:200px;")
                            switch_sd_save_enable = ui.switch('保存图片到本地', value=config.get("sd", "save_enable")).style(switch_internal_css)
                            switch_sd_loop_cover = ui.switch('本地图片循环覆盖', value=config.get("sd", "loop_cover")).style(switch_internal_css)
                            input_sd_save_path = ui.input(label='图片保存路径', value=config.get("sd", "save_path"), placeholder='生成图片存储路径，不建议修改').style("width:200px;")
                
                if config.get("webui", "show_card", "common_config", "web_captions_printer"):
                    with ui.card().style(card_css):
                        ui.label('web字幕打印机')
                        with ui.grid(columns=2):
                            switch_web_captions_printer_enable = ui.switch('启用', value=config.get("web_captions_printer", "enable")).style(switch_internal_css).tooltip("如果您使用了audio player来做音频播放，并开启了其web字幕打印机功能,\n那请勿启动此功能，因为这样就重复惹")
                            input_web_captions_printer_api_ip_port = ui.input(
                                label='API地址', 
                                value=config.get("web_captions_printer", "api_ip_port"), 
                                placeholder='web字幕打印机的API地址，只需要 http://ip:端口 即可',
                                validation={
                                    '请输入正确格式的URL': lambda value: common.is_url_check(value),
                                }
                            ).style("width:200px;").tooltip('web字幕打印机的API地址，只需要 http://ip:端口 即可')


            with ui.expansion('高级功能', icon="view_in_ar", value=True).classes('w-full'):
                if config.get("webui", "show_card", "common_config", "log"):
                    with ui.card().style(card_css):
                        ui.label('日志')
                        with ui.grid(columns=4):
                            switch_captions_enable = ui.switch('启用', value=config.get("captions", "enable")).style(switch_internal_css)

                            select_comment_log_type = ui.select(
                                label='弹幕日志类型',
                                options={'问答': '问答', '问题': '问题', '回答': '回答', '不记录': '不记录'},
                                value=config.get("comment_log_type")
                            )

                            input_captions_file_path = ui.input(label='字幕日志路径', value=config.get("captions", "file_path"), placeholder='字幕日志存储路径').style("width:200px;")
                            input_captions_raw_file_path = ui.input(label='原文字幕日志路径', placeholder='原文字幕日志存储路径',
                                                                value=config.get("captions", "raw_file_path")).style("width:200px;")

                if config.get("webui", "show_card", "common_config", "database"):  
                    with ui.card().style(card_css):
                        ui.label('数据库')
                        with ui.grid(columns=4):
                            switch_database_comment_enable = ui.switch('弹幕日志', value=config.get("database", "comment_enable")).style(switch_internal_css)
                            switch_database_entrance_enable = ui.switch('入场日志', value=config.get("database", "entrance_enable")).style(switch_internal_css)
                            switch_database_gift_enable = ui.switch('礼物日志', value=config.get("database", "gift_enable")).style(switch_internal_css)
                            input_database_path = ui.input(label='数据库路径', value=config.get("database", "path"), placeholder='数据库文件存储路径').style("width:200px;")
                            
                              
                if config.get("webui", "show_card", "common_config", "custom_cmd"):  
                    with ui.card().style(card_css):
                        ui.label('自定义命令')
                        with ui.row():
                            switch_custom_cmd_enable = ui.switch('启用', value=config.get("custom_cmd", "enable")).style(switch_internal_css)
                            select_custom_cmd_type = ui.select(
                                label='类型',
                                options={'弹幕': '弹幕'},
                                value=config.get("custom_cmd", "type")
                            ).style("width:200px")
                        with ui.row():
                            input_custom_cmd_index = ui.input(label='配置索引', value="", placeholder='配置组的排序号，就是说第一个组是1，第二个组是2，以此类推。请填写纯正整数')
                            button_custom_cmd_add = ui.button('增加配置组', on_click=custom_cmd_add, color=button_internal_color).style(button_internal_css)
                            button_custom_cmd_del = ui.button('删除配置组', on_click=lambda: custom_cmd_del(input_custom_cmd_index.value), color=button_internal_color).style(button_internal_css)
                        
                        custom_cmd_config_var = {}
                        custom_cmd_config_card = ui.card()
                        for index, custom_cmd_config in enumerate(config.get("custom_cmd", "config")):
                            with custom_cmd_config_card.style(card_css):
                                with ui.row():
                                    custom_cmd_config_var[str(7 * index)] = ui.textarea(label=f"关键词#{index + 1}", value=textarea_data_change(custom_cmd_config["keywords"]), placeholder='此处输入触发的关键词，多个请以换行分隔').style("width:200px;")
                                    custom_cmd_config_var[str(7 * index + 1)] = ui.input(label=f"相似度#{index + 1}", value=custom_cmd_config["similarity"], placeholder='关键词与用户输入的相似度，默认1即100%').style("width:100px;")
                                    custom_cmd_config_var[str(7 * index + 2)] = ui.textarea(
                                        label=f"API URL#{index + 1}", 
                                        value=custom_cmd_config["api_url"], 
                                        placeholder='发送HTTP请求的API链接', 
                                        validation={
                                            '请输入正确格式的URL': lambda value: common.is_url_check(value),
                                        }
                                    ).style("width:300px;").tooltip('发送HTTP请求的API链接')
                                    custom_cmd_config_var[str(7 * index + 3)] = ui.select(label=f"API类型#{index + 1}", value=custom_cmd_config["api_type"], options={"GET": "GET"}).style("width:100px;")
                                    custom_cmd_config_var[str(7 * index + 4)] = ui.select(label=f"请求返回数据类型#{index + 1}", value=custom_cmd_config["resp_data_type"], options={"json": "json", "content": "content"}).style("width:150px;")
                                    custom_cmd_config_var[str(7 * index + 5)] = ui.textarea(label=f"数据解析（eval执行）#{index + 1}", value=custom_cmd_config["data_analysis"], placeholder='数据解析，请不要随意修改resp变量，会被用于最后返回数据内容的解析').style("width:200px;").tooltip('数据解析，请不要随意修改resp变量，会被用于最后返回数据内容的解析')
                                    custom_cmd_config_var[str(7 * index + 6)] = ui.textarea(label=f"返回内容模板#{index + 1}", value=custom_cmd_config["resp_template"], placeholder='请不要随意删除data变量，支持动态变量，最终会合并成完成内容进行音频合成').style("width:300px;").tooltip("请不要随意删除data变量，支持动态变量，最终会合并成完成内容进行音频合成")


                if config.get("webui", "show_card", "common_config", "trends_config"):  
                    with ui.card().style(card_css):
                        ui.label('动态配置')
                        with ui.row():
                            switch_trends_config_enable = ui.switch('启用', value=config.get("trends_config", "enable")).style(switch_internal_css)
                        trends_config_path_var = {}
                        for index, trends_config_path in enumerate(config.get("trends_config", "path")):
                            with ui.grid(columns=2):
                                trends_config_path_var[str(2 * index)] = ui.input(label="在线人数范围", value=trends_config_path["online_num"], placeholder='在线人数范围，用减号-分隔，例如：0-10').style("width:200px;").tooltip("在线人数范围，用减号-分隔，例如：0-10")
                                trends_config_path_var[str(2 * index + 1)] = ui.input(label="配置路径", value=trends_config_path["path"], placeholder='此处输入加载的配置文件的路径').style("width:200px;").tooltip("此处输入加载的配置文件的路径")
                
                if config.get("webui", "show_card", "common_config", "abnormal_alarm"): 
                    with ui.card().style(card_css):
                        ui.label('异常报警')
                        with ui.row():
                            switch_abnormal_alarm_platform_enable = ui.switch('启用平台报警', value=config.get("abnormal_alarm", "platform", "enable")).style(switch_internal_css)
                            select_abnormal_alarm_platform_type = ui.select(
                                label='类型',
                                options={'local_audio': '本地音频'},
                                value=config.get("abnormal_alarm", "platform", "type")
                            )
                            input_abnormal_alarm_platform_start_alarm_error_num = ui.input(label='开始报警错误数', value=config.get("abnormal_alarm", "platform", "start_alarm_error_num"), placeholder='开始异常报警的错误数，超过这个数后就会报警').style("width:100px;")
                            input_abnormal_alarm_platform_auto_restart_error_num = ui.input(label='自动重启错误数', value=config.get("abnormal_alarm", "platform", "auto_restart_error_num"), placeholder='记得先启用“自动运行”功能。自动重启的错误数，超过这个数后就会自动重启webui。').style("width:100px;")
                            input_abnormal_alarm_platform_local_audio_path = ui.input(label='本地音频路径', value=config.get("abnormal_alarm", "platform", "local_audio_path"), placeholder='本地音频存储的文件路径（可以是多个音频，随机一个）').style("width:300px;")
                        with ui.row():
                            switch_abnormal_alarm_llm_enable = ui.switch('启用LLM报警', value=config.get("abnormal_alarm", "llm", "enable")).style(switch_internal_css)
                            select_abnormal_alarm_llm_type = ui.select(
                                label='类型',
                                options={'local_audio': '本地音频'},
                                value=config.get("abnormal_alarm", "llm", "type")
                            )
                            input_abnormal_alarm_llm_start_alarm_error_num = ui.input(label='开始报警错误数', value=config.get("abnormal_alarm", "llm", "start_alarm_error_num"), placeholder='开始异常报警的错误数，超过这个数后就会报警').style("width:100px;")
                            input_abnormal_alarm_llm_auto_restart_error_num = ui.input(label='自动重启错误数', value=config.get("abnormal_alarm", "llm", "auto_restart_error_num"), placeholder='记得先启用“自动运行”功能。自动重启的错误数，超过这个数后就会自动重启webui。').style("width:100px;")
                            input_abnormal_alarm_llm_local_audio_path = ui.input(label='本地音频路径', value=config.get("abnormal_alarm", "llm", "local_audio_path"), placeholder='本地音频存储的文件路径（可以是多个音频，随机一个）').style("width:300px;")
                        with ui.row():
                            switch_abnormal_alarm_tts_enable = ui.switch('启用TTS报警', value=config.get("abnormal_alarm", "tts", "enable")).style(switch_internal_css)
                            select_abnormal_alarm_tts_type = ui.select(
                                label='类型',
                                options={'local_audio': '本地音频'},
                                value=config.get("abnormal_alarm", "tts", "type")
                            )
                            input_abnormal_alarm_tts_start_alarm_error_num = ui.input(label='开始报警错误数', value=config.get("abnormal_alarm", "tts", "start_alarm_error_num"), placeholder='开始异常报警的错误数，超过这个数后就会报警').style("width:100px;")
                            input_abnormal_alarm_tts_auto_restart_error_num = ui.input(label='自动重启错误数', value=config.get("abnormal_alarm", "tts", "auto_restart_error_num"), placeholder='记得先启用“自动运行”功能。自动重启的错误数，超过这个数后就会自动重启webui。').style("width:100px;")
                            input_abnormal_alarm_tts_local_audio_path = ui.input(label='本地音频路径', value=config.get("abnormal_alarm", "tts", "local_audio_path"), placeholder='本地音频存储的文件路径（可以是多个音频，随机一个）').style("width:300px;")
                        with ui.row():
                            switch_abnormal_alarm_svc_enable = ui.switch('启用SVC报警', value=config.get("abnormal_alarm", "svc", "enable")).style(switch_internal_css)
                            select_abnormal_alarm_svc_type = ui.select(
                                label='类型',
                                options={'local_audio': '本地音频'},
                                value=config.get("abnormal_alarm", "svc", "type")
                            )
                            input_abnormal_alarm_svc_start_alarm_error_num = ui.input(label='开始报警错误数', value=config.get("abnormal_alarm", "svc", "start_alarm_error_num"), placeholder='开始异常报警的错误数，超过这个数后就会报警').style("width:100px;")
                            input_abnormal_alarm_svc_auto_restart_error_num = ui.input(label='自动重启错误数', value=config.get("abnormal_alarm", "svc", "auto_restart_error_num"), placeholder='记得先启用“自动运行”功能。自动重启的错误数，超过这个数后就会自动重启webui。').style("width:100px;")
                            input_abnormal_alarm_svc_local_audio_path = ui.input(label='本地音频路径', value=config.get("abnormal_alarm", "svc", "local_audio_path"), placeholder='本地音频存储的文件路径（可以是多个音频，随机一个）').style("width:300px;")
                        with ui.row():
                            switch_abnormal_alarm_visual_body_enable = ui.switch('启用虚拟身体报警', value=config.get("abnormal_alarm", "visual_body", "enable")).style(switch_internal_css)
                            select_abnormal_alarm_visual_body_type = ui.select(
                                label='类型',
                                options={'local_audio': '本地音频'},
                                value=config.get("abnormal_alarm", "visual_body", "type")
                            )
                            input_abnormal_alarm_visual_body_start_alarm_error_num = ui.input(label='开始报警错误数', value=config.get("abnormal_alarm", "visual_body", "start_alarm_error_num"), placeholder='开始异常报警的错误数，超过这个数后就会报警').style("width:100px;")
                            input_abnormal_alarm_visual_body_auto_restart_error_num = ui.input(label='自动重启错误数', value=config.get("abnormal_alarm", "visual_body", "auto_restart_error_num"), placeholder='记得先启用“自动运行”功能。自动重启的错误数，超过这个数后就会自动重启webui。').style("width:100px;")
                            input_abnormal_alarm_visual_body_local_audio_path = ui.input(label='本地音频路径', value=config.get("abnormal_alarm", "visual_body", "local_audio_path"), placeholder='本地音频存储的文件路径（可以是多个音频，随机一个）').style("width:300px;")
                        with ui.row():
                            switch_abnormal_alarm_other_enable = ui.switch('启用其他报警', value=config.get("abnormal_alarm", "other", "enable")).style(switch_internal_css)
                            select_abnormal_alarm_other_type = ui.select(
                                label='类型',
                                options={'local_audio': '本地音频'},
                                value=config.get("abnormal_alarm", "other", "type")
                            )
                            input_abnormal_alarm_other_start_alarm_error_num = ui.input(label='开始报警错误数', value=config.get("abnormal_alarm", "other", "start_alarm_error_num"), placeholder='开始异常报警的错误数，超过这个数后就会报警').style("width:100px;")
                            input_abnormal_alarm_other_auto_restart_error_num = ui.input(label='自动重启错误数', value=config.get("abnormal_alarm", "other", "auto_restart_error_num"), placeholder='记得先启用“自动运行”功能。自动重启的错误数，超过这个数后就会自动重启webui。').style("width:100px;")
                            input_abnormal_alarm_other_local_audio_path = ui.input(label='本地音频路径', value=config.get("abnormal_alarm", "other", "local_audio_path"), placeholder='本地音频存储的文件路径（可以是多个音频，随机一个）').style("width:300px;")
                        
                if config.get("webui", "show_card", "common_config", "coordination_program"):
                    with ui.expansion('联动程序', icon="settings", value=True).classes('w-full'):
                        with ui.row():
                            input_coordination_program_index = ui.input(label='配置索引', value="", placeholder='配置组的排序号，就是说第一个组是1，第二个组是2，以此类推。请填写纯正整数')
                            button_coordination_program_add = ui.button('增加配置组', on_click=coordination_program_add, color=button_internal_color).style(button_internal_css)
                            button_coordination_program_del = ui.button('删除配置组', on_click=lambda: coordination_program_del(input_coordination_program_index.value), color=button_internal_color).style(button_internal_css)
                        
                        coordination_program_var = {}
                        coordination_program_config_card = ui.card()
                        for index, coordination_program in enumerate(config.get("coordination_program")):
                            with coordination_program_config_card.style(card_css):
                                with ui.row():
                                    coordination_program_var[str(4 * index)] = ui.switch(f'启用#{index + 1}', value=coordination_program["enable"]).style(switch_internal_css)
                                    coordination_program_var[str(4 * index + 1)] = ui.input(label=f"程序名#{index + 1}", value=coordination_program["name"], placeholder='给你的程序取个名字，别整特殊符号！').style("width:200px;")
                                    coordination_program_var[str(4 * index + 2)] = ui.input(label=f"可执行程序#{index + 1}", value=coordination_program["executable"], placeholder='可执行程序的路径，最好是绝对路径，如python的程序').style("width:400px;")
                                    coordination_program_var[str(4 * index + 3)] = ui.textarea(label=f'参数#{index + 1}', value=textarea_data_change(coordination_program["parameters"]), placeholder='参数，可以传入多个参数，换行分隔。如启动的程序的路径，命令携带的传参等').style("width:500px;")
                

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
                config, common, audio, state, card_css, switch_internal_css, button_internal_color, button_internal_css))

        with ui.tab_panel(integral_page).style(tab_panel_css):
            page_config_mappings.append(build_integral_tab(config, card_css, switch_internal_css))

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
            with ui.card().style(card_css):
                ui.label("webui配置")
                with ui.row():
                    input_webui_title = ui.input(label='标题', placeholder='webui的标题', value=config.get("webui", "title")).style("width:250px;")
                    input_webui_ip = ui.input(label='IP地址', placeholder='webui监听的IP地址', value=config.get("webui", "ip")).style("width:150px;")
                    input_webui_port = ui.input(label='端口', placeholder='webui监听的端口', value=config.get("webui", "port")).style("width:100px;")
                    switch_webui_auto_run = ui.switch('自动运行', value=config.get("webui", "auto_run")).style(switch_internal_css)
            
            with ui.card().style(card_css):
                ui.label("本地路径指定URL路径访问")
                with ui.row():
                    input_webui_local_dir_to_endpoint_index = ui.input(label='配置索引', value="", placeholder='配置组的排序号，就是说第一个组是1，第二个组是2，以此类推。请填写纯正整数')
                    button_webui_local_dir_to_endpoint_add = ui.button('增加配置组', on_click=webui_local_dir_to_endpoint_add, color=button_internal_color).style(button_internal_css)
                    button_webui_local_dir_to_endpoint_del = ui.button('删除配置组', on_click=lambda: webui_local_dir_to_endpoint_del(input_webui_local_dir_to_endpoint_index.value), color=button_internal_color).style(button_internal_css)
                
                with ui.row():
                    switch_webui_local_dir_to_endpoint_enable = ui.switch('启用', value=config.get("webui", "local_dir_to_endpoint", "enable")).style(switch_internal_css)
                with ui.row():
                    webui_local_dir_to_endpoint_config_var = {}
                    webui_local_dir_to_endpoint_config_card = ui.card()
                    for index, webui_local_dir_to_endpoint_config in enumerate(config.get("webui", "local_dir_to_endpoint", "config")):
                        with webui_local_dir_to_endpoint_config_card.style(card_css):
                            with ui.row():
                                webui_local_dir_to_endpoint_config_var[str(2 * index)] = ui.input(label=f"URL路径#{index + 1}", value=webui_local_dir_to_endpoint_config["url_path"], placeholder='以斜杠（"/"）开始的字符串，它标识了应该为客户端提供文件的URL路径').style("width:200px;")
                                webui_local_dir_to_endpoint_config_var[str(2 * index + 1)] = ui.input(label=f"本地文件夹路径#{index + 1}", value=webui_local_dir_to_endpoint_config["local_dir"], placeholder='本地文件夹路径，建议相对路径，最好是项目内部的路径').style("width:300px;")
                               

            with ui.card().style(card_css):
                ui.label("CSS")
                with ui.row():
                    theme_list = config.get("webui", "theme", "list").keys()
                    data_json = {}
                    for line in theme_list:
                        data_json[line] = line
                    select_webui_theme_choose = ui.select(
                        label='主题', 
                        options=data_json, 
                        value=config.get("webui", "theme", "choose")
                    )

            with ui.card().style(card_css):
                ui.label("配置模板")
                with ui.row():
                    # 获取指定路径下指定拓展名的文件名列表
                    config_template_paths = common.get_specify_extension_names_in_folder("./", "*.json")
                    data_json = {}
                    for line in config_template_paths:
                        data_json[line] = line
                    select_config_template_path = ui.select(
                        label='配置模板路径', 
                        options=data_json, 
                        value="",
                        with_input=True,
                        new_value_mode='add-unique',
                        clearable=True
                    )

                    button_config_template_save = ui.button('保存webui配置到文件', on_click=lambda: config_template_save(select_config_template_path.value), color=button_internal_color).style(button_internal_css)
                    button_config_template_load = ui.button('读取模板到本地（慎点）', on_click=lambda: config_template_load(select_config_template_path.value), color=button_internal_color).style(button_internal_css)
                    


            with ui.card().style(card_css):
                ui.label("板块显示/隐藏")
                
                with ui.card().style(card_css):
                    ui.label("通用配置")
                    with ui.row():
                        switch_webui_show_card_common_config_read_comment = ui.switch('念弹幕', value=config.get("webui", "show_card", "common_config", "read_comment")).style(switch_internal_css)
                        switch_webui_show_card_common_config_filter = ui.switch('过滤', value=config.get("webui", "show_card", "common_config", "filter")).style(switch_internal_css)
                        switch_webui_show_card_common_config_thanks = ui.switch('答谢', value=config.get("webui", "show_card", "common_config", "thanks")).style(switch_internal_css)
                        switch_webui_show_card_common_config_local_qa = ui.switch('本地问答', value=config.get("webui", "show_card", "common_config", "local_qa")).style(switch_internal_css)
                        switch_webui_show_card_common_config_choose_song = ui.switch('点歌', value=config.get("webui", "show_card", "common_config", "choose_song")).style(switch_internal_css)
                        switch_webui_show_card_common_config_sd = ui.switch('Stable Diffusion', value=config.get("webui", "show_card", "common_config", "sd")).style(switch_internal_css)
                        switch_webui_show_card_common_config_log = ui.switch('日志', value=config.get("webui", "show_card", "common_config", "log")).style(switch_internal_css)
                        switch_webui_show_card_common_config_schedule = ui.switch('定时任务', value=config.get("webui", "show_card", "common_config", "schedule")).style(switch_internal_css)
                        switch_webui_show_card_common_config_idle_time_task = ui.switch('闲时任务', value=config.get("webui", "show_card", "common_config", "idle_time_task")).style(switch_internal_css)
                        switch_webui_show_card_common_config_trends_copywriting = ui.switch('动态文案', value=config.get("webui", "show_card", "common_config", "trends_copywriting")).style(switch_internal_css)
                        switch_webui_show_card_common_config_database = ui.switch('数据库', value=config.get("webui", "show_card", "common_config", "database")).style(switch_internal_css)
                        switch_webui_show_card_common_config_play_audio = ui.switch('音频播放', value=config.get("webui", "show_card", "common_config", "play_audio")).style(switch_internal_css)
                        switch_webui_show_card_common_config_web_captions_printer = ui.switch('web字幕打印机', value=config.get("webui", "show_card", "common_config", "web_captions_printer")).style(switch_internal_css)
                        switch_webui_show_card_common_config_key_mapping = ui.switch('按键/文案映射', value=config.get("webui", "show_card", "common_config", "key_mapping")).style(switch_internal_css)
                        switch_webui_show_card_common_config_custom_cmd = ui.switch('自定义命令', value=config.get("webui", "show_card", "common_config", "custom_cmd")).style(switch_internal_css)
                        
                        switch_webui_show_card_common_config_trends_config = ui.switch('动态配置', value=config.get("webui", "show_card", "common_config", "trends_config")).style(switch_internal_css)
                        switch_webui_show_card_common_config_abnormal_alarm = ui.switch('异常报警', value=config.get("webui", "show_card", "common_config", "abnormal_alarm")).style(switch_internal_css)
                        switch_webui_show_card_common_config_coordination_program = ui.switch('联动程序', value=config.get("webui", "show_card", "common_config", "coordination_program")).style(switch_internal_css)
                        
                
                with ui.card().style(card_css):
                    ui.label("大语言模型")
                    with ui.row():
                        switch_webui_show_card_llm_chatgpt = ui.switch('ChatGPT/闻达', value=config.get("webui", "show_card", "llm", "chatgpt")).style(switch_internal_css)
                        switch_webui_show_card_llm_zhipu = ui.switch('智谱AI', value=config.get("webui", "show_card", "llm", "zhipu")).style(switch_internal_css)
                        switch_webui_show_card_llm_chat_with_file = ui.switch('chat_with_file', value=config.get("webui", "show_card", "llm", "chat_with_file")).style(switch_internal_css)
                        switch_webui_show_card_llm_langchain_chatchat = ui.switch('langchain_chatchat', value=config.get("webui", "show_card", "llm", "langchain_chatchat")).style(switch_internal_css)
                        switch_webui_show_card_llm_chatterbot = ui.switch('chatterbot', value=config.get("webui", "show_card", "llm", "chatterbot")).style(switch_internal_css)
                        switch_webui_show_card_llm_text_generation_webui = ui.switch('text_generation_webui', value=config.get("webui", "show_card", "llm", "text_generation_webui")).style(switch_internal_css)
                        switch_webui_show_card_llm_sparkdesk = ui.switch('讯飞星火', value=config.get("webui", "show_card", "llm", "sparkdesk")).style(switch_internal_css)
                        switch_webui_show_card_llm_bard = ui.switch('bard', value=config.get("webui", "show_card", "llm", "bard")).style(switch_internal_css)
                        switch_webui_show_card_llm_tongyi = ui.switch('通义千问', value=config.get("webui", "show_card", "llm", "tongyi")).style(switch_internal_css)
                        switch_webui_show_card_llm_tongyixingchen = ui.switch('通义星尘', value=config.get("webui", "show_card", "llm", "tongyixingchen")).style(switch_internal_css)
                        switch_webui_show_card_llm_my_wenxinworkshop = ui.switch('千帆大模型', value=config.get("webui", "show_card", "llm", "my_wenxinworkshop")).style(switch_internal_css)
                        switch_webui_show_card_llm_gemini = ui.switch('gemini', value=config.get("webui", "show_card", "llm", "gemini")).style(switch_internal_css)
                        switch_webui_show_card_llm_koboldcpp = ui.switch('koboldcpp', value=config.get("webui", "show_card", "llm", "koboldcpp")).style(switch_internal_css)
                        switch_webui_show_card_llm_anythingllm = ui.switch('AnythingLLM', value=config.get("webui", "show_card", "llm", "anythingllm")).style(switch_internal_css)
                        switch_webui_show_card_llm_gpt4free = ui.switch('GPT4Free', value=config.get("webui", "show_card", "llm", "gpt4free")).style(switch_internal_css)
                        switch_webui_show_card_llm_dify = ui.switch('Dify', value=config.get("webui", "show_card", "llm", "dify")).style(switch_internal_css)
                        switch_webui_show_card_llm_volcengine = ui.switch('火山引擎', value=config.get("webui", "show_card", "llm", "volcengine")).style(switch_internal_css)
                        
                        switch_webui_show_card_llm_custom_llm = ui.switch('自定义LLM', value=config.get("webui", "show_card", "llm", "custom_llm")).style(switch_internal_css)
                        switch_webui_show_card_llm_llm_tpu = ui.switch('LLM_TPU', value=config.get("webui", "show_card", "llm", "llm_tpu")).style(switch_internal_css)
                        
                with ui.card().style(card_css):
                    ui.label("文本转语音")
                    with ui.row():
                        switch_webui_show_card_tts_edge_tts = ui.switch('Edge TTS', value=config.get("webui", "show_card", "tts", "edge-tts")).style(switch_internal_css)
                        switch_webui_show_card_tts_vits = ui.switch('VITS', value=config.get("webui", "show_card", "tts", "vits")).style(switch_internal_css)
                        switch_webui_show_card_tts_bert_vits2 = ui.switch('Bert VITS2', value=config.get("webui", "show_card", "tts", "bert_vits2")).style(switch_internal_css)
                        switch_webui_show_card_tts_vits_fast = ui.switch('VITS Fast', value=config.get("webui", "show_card", "tts", "vits_fast")).style(switch_internal_css)
                        switch_webui_show_card_tts_elevenlabs = ui.switch('elevenlabs', value=config.get("webui", "show_card", "tts", "elevenlabs")).style(switch_internal_css)
                        switch_webui_show_card_tts_openai_tts = ui.switch('openai_tts', value=config.get("webui", "show_card", "tts", "openai_tts")).style(switch_internal_css)
                        switch_webui_show_card_tts_gradio_tts = ui.switch('gradio', value=config.get("webui", "show_card", "tts", "gradio_tts")).style(switch_internal_css)
                        switch_webui_show_card_tts_gpt_sovits = ui.switch('gpt_sovits', value=config.get("webui", "show_card", "tts", "gpt_sovits")).style(switch_internal_css)
                        switch_webui_show_card_tts_azure_tts = ui.switch('azure_tts', value=config.get("webui", "show_card", "tts", "azure_tts")).style(switch_internal_css)
                        switch_webui_show_card_tts_cosyvoice = ui.switch('CosyVoice', value=config.get("webui", "show_card", "tts", "cosyvoice")).style(switch_internal_css)
                        switch_webui_show_card_tts_f5_tts = ui.switch('F5-TTS', value=config.get("webui", "show_card", "tts", "f5_tts")).style(switch_internal_css)
                        switch_webui_show_card_tts_multitts = ui.switch('F5-TTS', value=config.get("webui", "show_card", "tts", "multitts")).style(switch_internal_css)
                        switch_webui_show_card_tts_melotts = ui.switch('F5-TTS', value=config.get("webui", "show_card", "tts", "melotts")).style(switch_internal_css)
                        switch_webui_show_card_tts_index_tts = ui.switch('Index-TTS', value=config.get("webui", "show_card", "tts", "index_tts")).style(switch_internal_css)
                        
                with ui.card().style(card_css):
                    ui.label("变声")
                    with ui.row():
                        switch_webui_show_card_svc_ddsp_svc = ui.switch('DDSP SVC', value=config.get("webui", "show_card", "svc", "ddsp_svc")).style(switch_internal_css)
                        switch_webui_show_card_svc_so_vits_svc = ui.switch('SO-VITS-SVC', value=config.get("webui", "show_card", "svc", "so_vits_svc")).style(switch_internal_css)
                with ui.card().style(card_css):
                    ui.label("虚拟身体")
                    with ui.row():
                        switch_webui_show_card_visual_body_live2d = ui.switch('Live2D', value=config.get("webui", "show_card", "visual_body", "live2d")).style(switch_internal_css)
                        switch_webui_show_card_visual_body_xuniren = ui.switch('xuniren', value=config.get("webui", "show_card", "visual_body", "xuniren")).style(switch_internal_css)
                        switch_webui_show_card_visual_body_metahuman_stream = ui.switch('metahuman_stream', value=config.get("webui", "show_card", "visual_body", "metahuman_stream")).style(switch_internal_css)
                        switch_webui_show_card_visual_body_unity = ui.switch('unity', value=config.get("webui", "show_card", "visual_body", "unity")).style(switch_internal_css)
                        switch_webui_show_card_visual_body_EasyAIVtuber = ui.switch('EasyAIVtuber', value=config.get("webui", "show_card", "visual_body", "EasyAIVtuber")).style(switch_internal_css)
                        switch_webui_show_card_visual_body_digital_human_video_player = ui.switch('digital_human_video_player', value=config.get("webui", "show_card", "visual_body", "digital_human_video_player")).style(switch_internal_css)
                        switch_webui_show_card_visual_body_live2d_TTS_LLM_GPT_SoVITS_Vtuber = ui.switch('live2d_TTS_LLM_GPT_SoVITS_Vtuber', value=config.get("webui", "show_card", "visual_body", "live2d_TTS_LLM_GPT_SoVITS_Vtuber")).style(switch_internal_css)
                                
                    
            
            with ui.card().style(card_css):
                ui.label("账号管理")
                with ui.row():
                    switch_login_enable = ui.switch('登录功能', value=config.get("login", "enable")).style(switch_internal_css)
                    input_login_username = ui.input(label='用户名', placeholder='您的账号喵，配置在config.json中', value=config.get("login", "username")).style("width:250px;")
                    input_login_password = ui.input(label='密码', password=True, placeholder='您的密码喵，配置在config.json中', value=config.get("login", "password")).style("width:250px;")
        with ui.tab_panel(docs_page).style(tab_panel_css):
            build_docs_tab()

        with ui.tab_panel(about_page).style(tab_panel_css):
            build_about_tab(card_css)

    with ui.grid(columns=6).style("position: fixed; bottom: 10px; text-align: center;"):
        button_save = ui.button('保存配置', on_click=lambda: save_config(), color=button_bottom_color).style(button_bottom_css).tooltip("保存webui的配置到本地文件，有些配置保存后需要重启生效")
        button_run = ui.button('一键运行', on_click=lambda: run_external_program(), color=button_bottom_color).style(button_bottom_css).tooltip("运行main.py")
        # 创建一个按钮，用于停止正在运行的程序
        button_stop = ui.button("停止运行", on_click=lambda: stop_external_program(), color=button_bottom_color).style(button_bottom_css).tooltip("停止运行main.py")
        button_light = ui.button('关灯', on_click=lambda: change_light_status(), color=button_bottom_color).style(button_bottom_css)
        # button_stop.enabled = False  # 初始状态下停止按钮禁用
        button_restart = ui.button('重启', on_click=lambda: restart_application(), color=button_bottom_color).style(button_bottom_css).tooltip("停止运行main.py并重启webui")
        # factory_btn = ui.button('恢复出厂配置', on_click=lambda: factory(), color=button_bottom_color).style(tab_panel_css)

    with ui.row().style("position:fixed; bottom: 20px; right: 20px;"):
        ui.button('⇧', on_click=lambda: scroll_to_top(), color=button_bottom_color).style(button_bottom_css)

    # 是否启用自动运行功能
    if config.get("webui", "auto_run"):
        logger.info("自动运行 已启用")
        run_external_program(type="api")

# 发送心跳包
ui.timer(9 * 60, lambda: common.send_heartbeat())

# 是否启用登录功能（暂不合理）
if config.get("login", "enable"):

    def my_login():
        try:
            global user_info

            username = input_login_username.value
            password = input_login_password.value

            if username == "" or password == "":
                ui.notify(position="top", type="info", message="用户名或密码不能为空")
                return

            API_URL = urljoin(config.get("login", "ums_api"), '/auth/login')
                        
            resp_json = common.check_login(API_URL, username, password)

            if resp_json is None:
                ui.notify(position="top", type="negative", message="登录失败")
                return

            if "data" not in resp_json or "success" not in resp_json:
                ui.notify(position="top", type="negative", message="用户名或密码不正确")
                return

            if not resp_json["success"]:
                remainder = common.time_difference_in_seconds(resp_json["data"]["expiration_ts"])
                ui.notify(position="top", type="warning", message=f'账号过期时间：{resp_json["data"]["expiration_ts"]}，已到期，请联系管理员续费')
                return

            user_info = resp_json["data"]
            expiration_ts = resp_json["data"]["expiration_ts"]

            remainder = common.time_difference_in_seconds(expiration_ts)
            if remainder < 0:
                ui.notify(position="top", type="warning", message=f"账号已过期：{remainder}秒，请联系管理员续费")
                return

            ui.notify(position="top", type="info", message=f'登录成功，账号到期时间：{resp_json["data"]["expiration_ts"]}，剩余时长：{remainder}秒')

            label_login.delete()
            input_login_username.delete()
            input_login_password.delete()
            button_login.delete()
            button_login_forget_password.delete()

            login_column.style("")
            login_card.style("position: unset;")

            goto_func_page()

            return
        except Exception as e:
            logger.error(traceback.format_exc())
            return

    # @ui.page('/forget_password')
    def forget_password():
        ui.notify(position="top", type="info", message="请联系管理员修改密码！")


    login_column = ui.column().style("width:100%;text-align: center;")
    with login_column:
        login_card = ui.card().style(config.get("webui", "theme", "list", theme_choose, "login_card"))
        with login_card:
            label_login = ui.label('AI    Vtuber').style("font-size: 30px;letter-spacing: 5px;color: #3b3838;")
            input_login_username = ui.input(label='用户名', placeholder='您的账号，请找管理员申请', value="").style("width:250px;")
            input_login_password = ui.input(label='密码', password=True, placeholder='您的密码，请找管理员申请', value="").style("width:250px;")
            button_login = ui.button('登录', on_click=lambda: my_login()).style("width:250px;")
            button_login_forget_password = ui.button('忘记账号/密码怎么办？', on_click=lambda: forget_password()).style("width:250px;")
            # link_login_forget_password = ui.link('忘记账号密码怎么办？', forget_password)

else:
    login_column = ui.column().style("width:100%;text-align: center;")
    with login_column:
        login_card = ui.card().style(config.get("webui", "theme", "list", theme_choose, "login_card"))
        
        # 跳转到功能页
        goto_func_page()


ui.run(host=webui_ip, port=webui_port, title=webui_title, favicon="./ui/favicon-64.ico", language="zh-CN", dark=False, reload=False)
# ui.run(host=webui_ip, port=webui_port, title=webui_title, favicon="./ui/favicon-64.ico", language="zh-CN", dark=False, reload=False,
#        ssl_certfile="F:\\FunASR_WS\\cert.pem", ssl_keyfile="F:\\FunASR_WS\\key.pem")