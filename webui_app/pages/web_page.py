"""页面配置页：WebUI 自身参数、静态目录映射、主题与配置模板。"""
import json
import traceback

from nicegui import ui

from utils.my_log import logger
from webui_app.config_store import update_config
from webui_app.confirm import confirm, delete_button
from webui_app.groups import GroupPicker
from webui_app.pages import PageConfig
from webui_app.theme import INK, background_of, preview_css, readable_on

# 试穿用的覆盖样式表放在一个可增删的 <style> 里：退出预览只要清空它，
# 不用去逐个还原 850 多个控件的内联样式（那些本来就是建页时按当前主题写的）。
THEME_SCRIPT = """
<script>
window.__lunaThemeCss = %s;
(function () {
    const put = function (css) {
        let el = document.getElementById('luna-theme-preview');
        if (!el) {
            el = document.createElement('style');
            el.id = 'luna-theme-preview';
            document.head.appendChild(el);
        }
        el.textContent = css || '';
    };
    window.__lunaThemePreview = function (name) { put(window.__lunaThemeCss[name]); return true; };
    window.__lunaThemeClear = function () { put(''); return true; };
})();
</script>
"""


def _swatch(name, theme, on_pick, current=False):
    """一小块色板：上面是这套主题的页面底，里面嵌一张卡，点一下当场试穿。"""
    panel = background_of(theme.get('tab_panel')) or '#f2f5f8'
    card = background_of(theme.get('card')) or '#ffffff'
    box = ui.element('div').style(
        f'background:{panel};border-radius:10px;padding:8px;width:158px;cursor:pointer;'
        + ('border:2px solid #2b5d9b;box-shadow:0 1px 3px rgba(0,0,0,0.12);' if current else
           'border:1px solid rgba(0,0,0,0.14);box-shadow:0 1px 3px rgba(0,0,0,0.12);'))
    with box:
        with ui.row().style('justify-content:space-between;align-items:baseline;width:100%;'):
            ui.label(name).style(f'font-size:12px;font-weight:600;color:{readable_on(panel)};')
            if current:
                # 不标出来，试穿两轮之后就分不清「配置文件里到底是哪套」了
                ui.label('当前').style(
                    f'font-size:11px;color:{readable_on(panel)};opacity:0.85;')
        inner = ui.element('div').style(f'background:{card};border-radius:6px;padding:6px 8px;margin-top:6px;')
        with inner:
            ui.label('配置卡片').style(f'font-size:11px;color:{readable_on(card)};')
            accent = (theme.get('button_bottom_color') or '').strip()
            ui.element('div').style(
                f'width:44px;height:12px;border-radius:6px;margin-top:4px;'
                f'background:{accent or "#5898d4"};')
    box.on('click', lambda: on_pick(name))
    return box


def _theme_preview(select_theme, themes, dirty_guard, chosen):
    """走查 audit-23：换主题原先要「改配置 → 保存 → 重启」才能看到效果。"""
    payload = json.dumps({name: preview_css(theme) for name, theme in themes.items()},
                         ensure_ascii=False).replace('</', '<\\/')
    ui.add_head_html(THEME_SCRIPT % payload)

    def pick(name):
        select_theme.value = name
        # 程序改的值不会触发 on_value_change，脏计数得自己记一笔，否则角标会说「没改动」
        dirty_guard.note_change(select_theme.id)
        ui.run_javascript(f'window.__lunaThemePreview({json.dumps(name, ensure_ascii=False)})')
        ui.notify(f'已用「{name}」试穿。要固定下来还是得点「保存配置」再重启。', position='top')

    with ui.element('div').classes('tip-bar'):
        ui.label('点下面的色板可以在当前页面试穿这套主题（不改文件）；要固定下来，'
                 '还是得「保存配置」+ 重启 webui——主题值是建页时写死在各控件上的。')
    with ui.row().style('gap:10px;flex-wrap:wrap;'):
        for name, theme in themes.items():
            _swatch(name, theme, pick, current=name == chosen)
        ui.button('退出预览', on_click=lambda: ui.run_javascript('window.__lunaThemeClear()')) \
            .props('flat no-caps dense').style(f'align-self:center;color:{INK};')


def build_web_page_tab(config, common, config_path, config_to_dict, card_css, switch_internal_css,
                       button_internal_color, button_internal_css, dirty_guard):
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
    def webui_local_dir_to_endpoint_del(pos):
        try:
            # 删除操作
            keys_to_delete = [str(2 * pos + i) for i in range(2)]
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

            config_data = config_to_dict(config_data)

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
            picker_local_dir = GroupPicker(lambda: webui_local_dir_to_endpoint_config_card, '本地路径映射', webui_local_dir_to_endpoint_del, lambda: webui_local_dir_to_endpoint_config_var).build()
            button_webui_local_dir_to_endpoint_add = ui.button('增加配置组', on_click=lambda: (webui_local_dir_to_endpoint_add(), picker_local_dir.refresh()), color=button_internal_color).style(button_internal_css)
            button_webui_local_dir_to_endpoint_del = delete_button('删除配置组', picker_local_dir.ask_delete).style(button_internal_css)
        
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
        theme_list = config.get("webui", "theme", "list")
        data_json = {}
        for line in theme_list.keys():
            data_json[line] = line
        select_webui_theme_choose = ui.select(
            label='主题',
            options=data_json,
            value=config.get("webui", "theme", "choose")
        )
        _theme_preview(select_webui_theme_choose, theme_list, dirty_guard,
                       config.get("webui", "theme", "choose"))

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
                # 这个下拉框允许用户现输一个新路径，初始就是「未选中」；
                # 空串不在 options 里，nicegui 3 会拒绝，None 才是未选中的正确表达
                value=None,
                with_input=True,
                new_value_mode='add-unique',
                clearable=True
            )

            button_config_template_save = ui.button('保存webui配置到文件', on_click=lambda: config_template_save(select_config_template_path.value), color=button_internal_color).style(button_internal_css)
            # 这是全站唯一一个不经「保存配置」就写盘的按钮，按危险操作对待：警示色 + 警示图标
            button_config_template_load = ui.button('读取模板到本地（慎点）', icon='warning', on_click=lambda: confirm.ask(
                f'确认用「{select_config_template_path.value or "（未填路径）"}」覆盖当前配置？',
                lambda: config_template_load(select_config_template_path.value),
                '这一步直接写配置文件，不经过「保存配置」，写完要重启 webui 才生效，也没法撤销。'),
                color='negative').style(button_internal_css)
            


    with ui.card().style(card_css):
        ui.label("板块显示/隐藏")
        
        with ui.card().style(card_css):
            ui.label("功能板块（已从 通用配置 拆到各页，关掉即从页面上移除）")
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
                switch_webui_show_card_llm_chatgpt = ui.switch('ChatGPT', value=config.get("webui", "show_card", "llm", "chatgpt")).style(switch_internal_css)
                switch_webui_show_card_llm_zhipu = ui.switch('智谱AI', value=config.get("webui", "show_card", "llm", "zhipu")).style(switch_internal_css)
                switch_webui_show_card_llm_chat_with_file = ui.switch('chat_with_file', value=config.get("webui", "show_card", "llm", "chat_with_file")).style(switch_internal_css)
                switch_webui_show_card_llm_langchain_chatchat = ui.switch('langchain_chatchat', value=config.get("webui", "show_card", "llm", "langchain_chatchat")).style(switch_internal_css)
                switch_webui_show_card_llm_tongyi = ui.switch('通义千问', value=config.get("webui", "show_card", "llm", "tongyi")).style(switch_internal_css)
                switch_webui_show_card_llm_my_wenxinworkshop = ui.switch('千帆大模型', value=config.get("webui", "show_card", "llm", "my_wenxinworkshop")).style(switch_internal_css)
                switch_webui_show_card_llm_gemini = ui.switch('gemini', value=config.get("webui", "show_card", "llm", "gemini")).style(switch_internal_css)
                switch_webui_show_card_llm_anythingllm = ui.switch('AnythingLLM', value=config.get("webui", "show_card", "llm", "anythingllm")).style(switch_internal_css)
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
                switch_webui_show_card_tts_multitts = ui.switch('MultiTTS', value=config.get("webui", "show_card", "tts", "multitts")).style(switch_internal_css)
                switch_webui_show_card_tts_melotts = ui.switch('MeloTTS', value=config.get("webui", "show_card", "tts", "melotts")).style(switch_internal_css)
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

    def save_webui(config_data):
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
                        "tongyi": (switch_webui_show_card_llm_tongyi, 'bool'),
                        "my_wenxinworkshop": (switch_webui_show_card_llm_my_wenxinworkshop, 'bool'),
                        "gemini": (switch_webui_show_card_llm_gemini, 'bool'),
                        "anythingllm": (switch_webui_show_card_llm_anythingllm, 'bool'),
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

        

    return PageConfig(on_save=save_webui)
