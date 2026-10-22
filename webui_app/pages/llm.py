"""大语言模型页：OpenAI 兼容接口与各家 provider 配置。"""
import asyncio

from nicegui import ui

from utils.my_log import logger
from webui_app.helpers import common_textarea_handle, textarea_data_change
from webui_app.pages import PageConfig


def merge_model_options(models, current):
    """把搜索到的模型名做成下拉选项，并决定选中哪个。

    Args:
        models (list): 接口返回的模型名
        current (str): 模型框里现在的值

    Returns:
        tuple: (options 字典, 应该选中的值)
    """
    options = {name: name for name in models}

    # 用户手输的、或搜索前就配好的名字，接口没列出来也要留着——
    # 点一次搜索就把别人的自定义模型名挤掉是不该发生的
    if current and current not in options:
        options[current] = current

    # 原来有值就尊重原值；没值才自动填第一个，省得手打
    if current:
        return options, current

    return options, (models[0] if models else current)


def build_llm_tab(config, common, card_css, switch_internal_css,
                  button_bottom_color, button_bottom_css, button_internal_color, button_internal_css):
    # openai 测试key可用性
    def test_openai_key():
        data_json = {
            "base_url": input_openai_api.value, 
            "api_keys": textarea_openai_api_key.value, 
            "model": select_chatgpt_model.value,
            "temperature": round(float(input_chatgpt_temperature.value), 1),
            "max_tokens": int(input_chatgpt_max_tokens.value),
            "top_p": round(float(input_chatgpt_top_p.value), 1),
            "presence_penalty": round(float(input_chatgpt_presence_penalty.value), 1),
            "frequency_penalty": round(float(input_chatgpt_frequency_penalty.value), 1),
            "preset": input_chatgpt_preset.value
        }

        resp_json = common.test_openai_key(data_json, 2)
        if resp_json["code"] == 200:
            ui.notify(position="top", type="positive", message=resp_json["msg"])
        else:
            ui.notify(position="top", type="negative", message=resp_json["msg"])

    # 搜索模型：请求 /v1/models，把模型名回填到左边的模型框
    async def search_chatgpt_models():
        button_chatgpt_model_search.set_enabled(False)
        try:
            # 这是个 blocking 的 requests，放线程里跑，别把整个 webui 的事件循环卡住
            resp_json = await asyncio.to_thread(
                common.get_openai_models, input_openai_api.value, textarea_openai_api_key.value
            )
        finally:
            button_chatgpt_model_search.set_enabled(True)

        if resp_json["code"] != 200:
            ui.notify(position="top", type="negative", message=resp_json["msg"])
            return

        models = resp_json["models"]
        options, selected = merge_model_options(models, select_chatgpt_model.value)
        select_chatgpt_model.options = options
        select_chatgpt_model.value = selected
        select_chatgpt_model.update()

        if selected and selected in models:
            message = f'取到 {len(models)} 个模型，当前是：{selected}（也可以直接手输）'
        elif selected:
            message = f'取到 {len(models)} 个模型，你原来的模型名接口没列出来，已保留：{selected}'
        else:
            message = f'取到 {len(models)} 个模型，点下拉选一个，也可以直接手输'
        ui.notify(position="top", type="positive", message=message)


    if config.get("webui", "show_card", "llm", "chatgpt"):
        with ui.card().style(card_css):
            ui.label("ChatGLM3 | Kimi Chat | Ollama | One-API等OpenAI接口模型 ")
            with ui.row():
                input_openai_api = ui.input(
                    label='API地址', 
                    placeholder='API请求地址，支持代理', 
                    value=config.get("openai", "api"),
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                ).style("width:200px;")
                textarea_openai_api_key = ui.textarea(label='API密钥', placeholder='API KEY，支持代理', value=textarea_data_change(config.get("openai", "api_key"))).style("width:400px;")
                button_openai_test = ui.button('测试', on_click=lambda: test_openai_key(), color=button_bottom_color).style(button_bottom_css)
            with ui.row():
                chatgpt_models = [
                    "gpt-3.5-turbo",
                    "gpt-3.5-turbo-instruct",
                    "gpt-3.5-turbo-0125",
                    "gpt-4",
                    "gpt-4-turbo-preview",
                    "gpt-4-0125-preview",
                    "gpt-4o",
                    "gpt-4o-mini",
                    "text-embedding-3-large",
                    "text-embedding-3-small",
                    "text-davinci-003",
                    "rwkv",
                    "chatglm3-6b",
                    "moonshot-v1-8k",
                    "gemma:2b",
                    "qwen",
                    "qwen:1.8b-chat"
                ]
                # 将用户配置的值插入list（如果不存在）
                if config.get("chatgpt", "model") not in chatgpt_models:
                    chatgpt_models.append(config.get("chatgpt", "model"))
                data_json = {}
                for line in chatgpt_models:
                    data_json[line] = line
                select_chatgpt_model = ui.select(
                    label='模型', 
                    options=data_json, 
                    value=config.get("chatgpt", "model"),
                    with_input=True,
                    new_value_mode='add-unique',
                    clearable=True
                ).tooltip("如果你没有在此找到你用的模型名，你可以删除此配置项的内容，然后手动输入，最后一定要回车！确认！")
                button_chatgpt_model_search = ui.button(
                    '搜索模型',
                    on_click=search_chatgpt_models,
                    color=button_bottom_color
                ).style(button_bottom_css).tooltip('用上面的 API地址 + 密钥列表里的第一个 key 请求 /v1/models，把返回的模型名填进左边的下拉框。搜索不会挤掉你手输的模型名，下拉框也始终可以直接输入')
                input_chatgpt_temperature = ui.input(label='温度', placeholder='控制生成文本的随机性。较高的温度值会使生成的文本更随机和多样化，而较低的温度值会使生成的文本更加确定和一致。', value=config.get("chatgpt", "temperature")).style("width:100px;")
                input_chatgpt_max_tokens = ui.input(label='最大token数', placeholder='限制生成回答的最大长度。', value=config.get("chatgpt", "max_tokens")).style("width:100px;")
                input_chatgpt_top_p = ui.input(label='top_p', placeholder='Nucleus采样。这个参数控制模型从累积概率大于一定阈值的令牌中进行采样。较高的值会产生更多的多样性，较低的值会产生更少但更确定的回答。', value=config.get("chatgpt", "top_p")).style("width:100px;")
                switch_chatgpt_stream = ui.switch('流式输出', value=config.get("chatgpt", "stream")).tooltip("是否开启流式输出，开启后，回答会逐句输出，关闭后，回答会一次性输出。")
            with ui.row():
                input_chatgpt_presence_penalty = ui.input(label='存在惩罚', placeholder='控制模型生成回答时对给定问题提示的关注程度。较高的存在惩罚值会减少模型对给定提示的重复程度，鼓励模型更自主地生成回答。', value=config.get("chatgpt", "presence_penalty")).style("width:100px;")
                input_chatgpt_frequency_penalty = ui.input(label='频率惩罚', placeholder='控制生成回答时对已经出现过的令牌的惩罚程度。较高的频率惩罚值会减少模型生成已经频繁出现的令牌，以避免重复和过度使用特定词语。', value=config.get("chatgpt", "frequency_penalty")).style("width:100px;")

                input_chatgpt_preset = ui.input(label='预设', placeholder='用于指定一组预定义的设置，以便模型更好地适应特定的对话场景。', value=config.get("chatgpt", "preset")).style("width:500px") 

    
    
    if config.get("webui", "show_card", "llm", "chat_with_file"):
        with ui.card().style(card_css):
            ui.label("chat_with_file")
            with ui.row():
                lines = [ "openai_gpt", "openai_vector_search"]
                data_json = {}
                for line in lines:
                    data_json[line] = line
                select_chat_with_file_chat_mode = ui.select(
                    label='聊天模式', 
                    options=data_json, 
                    value=config.get("chat_with_file", "chat_mode")
                )
                input_chat_with_file_data_path = ui.input(label='数据文件路径', placeholder='加载的本地zip数据文件路径（到x.zip）, 如：./data/伊卡洛斯百度百科.zip', value=config.get("chat_with_file", "data_path"))
                input_chat_with_file_data_path.style("width:400px")
            with ui.row():
                input_chat_with_file_separator = ui.input(label='分隔符', placeholder='拆分文本的分隔符，这里使用 换行符 作为分隔符。', value=config.get("chat_with_file", "separator"))
                input_chat_with_file_separator.style("width:300px")
                input_chat_with_file_chunk_size = ui.input(label='块大小', placeholder='每个文本块的最大字符数(文本块字符越多，消耗token越多，回复越详细)', value=config.get("chat_with_file", "chunk_size"))
                input_chat_with_file_chunk_size.style("width:300px")
                input_chat_with_file_chunk_overlap = ui.input(label='块重叠', placeholder='两个相邻文本块之间的重叠字符数。这种重叠可以帮助保持文本的连贯性，特别是当文本被用于训练语言模型或其他需要上下文信息的机器学习模型时', value=config.get("chat_with_file", "chunk_overlap"))
                input_chat_with_file_chunk_overlap.style("width:300px")
            with ui.row():
                input_chat_with_file_chain_type = ui.input(label='链类型', placeholder='指定要生成的语言链的类型，例如：stuff', value=config.get("chat_with_file", "chain_type"))
                input_chat_with_file_chain_type.style("width:300px")
                input_chat_with_file_question_prompt = ui.input(label='问题总结提示词', placeholder='通过LLM总结本地向量数据库输出内容，此处填写总结用提示词', value=config.get("chat_with_file", "question_prompt"))
                input_chat_with_file_question_prompt.style("width:300px")
                input_chat_with_file_local_max_query = ui.input(label='最大查询数据库次数', placeholder='最大查询数据库次数。限制次数有助于节省token', value=config.get("chat_with_file", "local_max_query"))
                input_chat_with_file_local_max_query.style("width:300px")
                switch_chat_with_file_show_token_cost = ui.switch('显示成本', value=config.get("chat_with_file", "show_token_cost")).style(switch_internal_css)
    
    if config.get("webui", "show_card", "llm", "langchain_chatchat"):  
        with ui.card().style(card_css):
            ui.label("Langchain_ChatChat")
            with ui.row():
                input_langchain_chatchat_api_ip_port = ui.input(
                    label='API地址', 
                    placeholder='langchain_chatchat的API版本运行后的服务链接（需要完整的URL）', 
                    value=config.get("langchain_chatchat", "api_ip_port"),
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                )
                input_langchain_chatchat_api_ip_port.style("width:400px")
                lines = ["模型", "知识库", "搜索引擎"]
                data_json = {}
                for line in lines:
                    data_json[line] = line
                select_langchain_chatchat_chat_type = ui.select(
                    label='类型', 
                    options=data_json, 
                    value=config.get("langchain_chatchat", "chat_type")
                )
                switch_langchain_chatchat_history_enable = ui.switch('上下文记忆', value=config.get("langchain_chatchat", "history_enable")).style(switch_internal_css)
                input_langchain_chatchat_history_max_len = ui.input(label='最大记忆长度', placeholder='最大记忆的上下文字符数量，不建议设置过大，容易爆显存，自行根据情况配置', value=config.get("langchain_chatchat", "history_max_len"))
                input_langchain_chatchat_history_max_len.style("width:400px")
            with ui.row():
                with ui.card().style(card_css):
                    ui.label("模型")
                    with ui.row():
                        input_langchain_chatchat_llm_model_name = ui.input(label='LLM模型', value=config.get("langchain_chatchat", "llm", "model_name"), placeholder='本地加载的LLM模型名')
                        input_langchain_chatchat_llm_temperature = ui.input(label='温度', value=config.get("langchain_chatchat", "llm", "temperature"), placeholder='采样温度，控制输出的随机性，必须为正数\n取值范围是：(0.0,1.0]，不能等于 0,默认值为 0.95\n值越大，会使输出更随机，更具创造性；值越小，输出会更加稳定或确定\n建议您根据应用场景调整 top_p 或 temperature 参数，但不要同时调整两个参数')
                        input_langchain_chatchat_llm_max_tokens = ui.input(label='max_tokens', value=config.get("langchain_chatchat", "llm", "max_tokens"), placeholder='大于0的正整数，不建议太大，你可能会爆显存')
                        input_langchain_chatchat_llm_prompt_name = ui.input(label='Prompt模板', value=config.get("langchain_chatchat", "llm", "prompt_name"), placeholder='本地存在的提示词模板文件名')
            with ui.row():
                with ui.card().style(card_css):
                    ui.label("知识库")
                    with ui.row():
                        input_langchain_chatchat_knowledge_base_knowledge_base_name = ui.input(label='知识库名', value=config.get("langchain_chatchat", "knowledge_base", "knowledge_base_name"), placeholder='本地添加的知识库名，运行时会自动检索存在的知识库列表，输出到cmd，请自行查看')
                        input_langchain_chatchat_knowledge_base_top_k = ui.input(label='匹配搜索结果条数', value=config.get("langchain_chatchat", "knowledge_base", "top_k"), placeholder='匹配搜索结果条数')
                        input_langchain_chatchat_knowledge_base_score_threshold = ui.input(label='知识匹配分数阈值', value=config.get("langchain_chatchat", "knowledge_base", "score_threshold"), placeholder='0.00-2.00之间')
                        input_langchain_chatchat_knowledge_base_model_name = ui.input(label='LLM模型', value=config.get("langchain_chatchat", "knowledge_base", "model_name"), placeholder='本地加载的LLM模型名')
                        input_langchain_chatchat_knowledge_base_temperature = ui.input(label='温度', value=config.get("langchain_chatchat", "knowledge_base", "temperature"), placeholder='采样温度，控制输出的随机性，必须为正数\n取值范围是：(0.0,1.0]，不能等于 0,默认值为 0.95\n值越大，会使输出更随机，更具创造性；值越小，输出会更加稳定或确定\n建议您根据应用场景调整 top_p 或 temperature 参数，但不要同时调整两个参数')
                        input_langchain_chatchat_knowledge_base_max_tokens = ui.input(label='max_tokens', value=config.get("langchain_chatchat", "knowledge_base", "max_tokens"), placeholder='大于0的正整数，不建议太大，你可能会爆显存')
                        input_langchain_chatchat_knowledge_base_prompt_name = ui.input(label='Prompt模板', value=config.get("langchain_chatchat", "knowledge_base", "prompt_name"), placeholder='本地存在的提示词模板文件名')
            with ui.row():
                with ui.card().style(card_css):
                    ui.label("搜索引擎")
                    with ui.row():
                        lines = ['bing', 'duckduckgo', 'metaphor']
                        data_json = {}
                        for line in lines:
                            data_json[line] = line
                        select_langchain_chatchat_search_engine_search_engine_name = ui.select(
                            label='搜索引擎', 
                            options=data_json, 
                            value=config.get("langchain_chatchat", "search_engine", "search_engine_name")
                        )
                        input_langchain_chatchat_search_engine_top_k = ui.input(label='匹配搜索结果条数', value=config.get("langchain_chatchat", "search_engine", "top_k"), placeholder='匹配搜索结果条数')
                        input_langchain_chatchat_search_engine_model_name = ui.input(label='LLM模型', value=config.get("langchain_chatchat", "search_engine", "model_name"), placeholder='本地加载的LLM模型名')
                        input_langchain_chatchat_search_engine_temperature = ui.input(label='温度', value=config.get("langchain_chatchat", "search_engine", "temperature"), placeholder='采样温度，控制输出的随机性，必须为正数\n取值范围是：(0.0,1.0]，不能等于 0,默认值为 0.95\n值越大，会使输出更随机，更具创造性；值越小，输出会更加稳定或确定\n建议您根据应用场景调整 top_p 或 temperature 参数，但不要同时调整两个参数')
                        input_langchain_chatchat_search_engine_max_tokens = ui.input(label='max_tokens', value=config.get("langchain_chatchat", "search_engine", "max_tokens"), placeholder='大于0的正整数，不建议太大，你可能会爆显存')
                        input_langchain_chatchat_search_engine_prompt_name = ui.input(label='Prompt模板', value=config.get("langchain_chatchat", "search_engine", "prompt_name"), placeholder='本地存在的提示词模板文件名')
    
    if config.get("webui", "show_card", "llm", "zhipu"):  
        with ui.card().style(card_css):
            ui.label("智谱AI")
            with ui.row():
                input_zhipu_api_key = ui.input(label='api key', placeholder='具体参考官方文档，申请地址：https://open.bigmodel.cn/usercenter/apikeys', value=config.get("zhipu", "api_key"))
                input_zhipu_api_key.style("width:200px")
                lines = [
                    '应用',
                    '智能体',
                    'glm-3-turbo', 
                    'glm-4', 
                    'glm-4-flash',
                    'charglm-3',
                    'characterglm', 
                    'chatglm_turbo', 
                    'chatglm_pro', 
                    'chatglm_std', 
                    'chatglm_lite', 
                    'chatglm_lite_32k'
                ]
                data_json = {}
                for line in lines:
                    data_json[line] = line
                select_zhipu_model = ui.select(
                    label='模型', 
                    options=data_json, 
                    value=config.get("zhipu", "model"),
                    with_input=True,
                    new_value_mode='add-unique',
                    clearable=True
                )
                input_zhipu_app_id = ui.input(label='应用ID', value=config.get("zhipu", "app_id"), placeholder='在 模型为：应用，会自动检索你平台上添加的所有应用信息，然后从日志中复制你需要的应用ID即可').style("width:200px")
                
            with ui.row():
                input_zhipu_top_p = ui.input(label='top_p', placeholder='用温度取样的另一种方法，称为核取样\n取值范围是：(0.0,1.0)；开区间，不能等于 0 或 1，默认值为 0.7\n模型考虑具有 top_p 概率质量的令牌的结果。所以 0.1 意味着模型解码器只考虑从前 10% 的概率的候选集中取tokens\n建议您根据应用场景调整 top_p 或 temperature 参数，但不要同时调整两个参数', value=config.get("zhipu", "top_p"))
                input_zhipu_top_p.style("width:200px")
                input_zhipu_temperature = ui.input(label='temperature', placeholder='采样温度，控制输出的随机性，必须为正数\n取值范围是：(0.0,1.0]，不能等于 0,默认值为 0.95\n值越大，会使输出更随机，更具创造性；值越小，输出会更加稳定或确定\n建议您根据应用场景调整 top_p 或 temperature 参数，但不要同时调整两个参数', value=config.get("zhipu", "temperature"))
                input_zhipu_temperature.style("width:200px")
                switch_zhipu_history_enable = ui.switch('上下文记忆', value=config.get("zhipu", "history_enable")).style(switch_internal_css)
                input_zhipu_history_max_len = ui.input(label='最大记忆长度', placeholder='最长能记忆的问答字符串长度，超长会丢弃最早记忆的内容，请慎用！配置过大可能会有丢大米', value=config.get("zhipu", "history_max_len"))
                input_zhipu_history_max_len.style("width:200px")
            with ui.row():
                input_zhipu_user_info = ui.input(label='用户信息', placeholder='用户信息，当使用characterglm时需要配置', value=config.get("zhipu", "user_info"))
                input_zhipu_user_info.style("width:400px")
                input_zhipu_bot_info = ui.input(label='角色信息', placeholder='角色信息，当使用characterglm时需要配置', value=config.get("zhipu", "bot_info"))
                input_zhipu_bot_info.style("width:400px")
                input_zhipu_bot_name = ui.input(label='角色名称', placeholder='角色名称，当使用characterglm时需要配置', value=config.get("zhipu", "bot_name"))
                input_zhipu_bot_name.style("width:200px")
                input_zhipu_username = ui.input(label='用户名称', placeholder='用户名称，默认值为用户，当使用characterglm时需要配置', value=config.get("zhipu", "username"))
                input_zhipu_username.style("width:200px")
            with ui.row():
                switch_zhipu_remove_useless = ui.switch('删除无用字符', value=config.get("zhipu", "remove_useless")).style(switch_internal_css)
                switch_zhipu_stream = ui.switch('流式输出', value=config.get("zhipu", "stream")).tooltip("是否开启流式输出，开启后，回答会逐句输出，关闭后，回答会一次性输出。")
            with ui.card().style(card_css):
                ui.label("智能体")
                with ui.row():
                    input_zhipu_assistant_api_api_key = ui.input(
                        label='智能体API Key', 
                        placeholder='智能体 创作者中心申请API：https://chatglm.cn/developersPanel/apiSet', 
                        value=config.get("zhipu", "assistant_api", "api_key")
                    ).style("width:150px").tooltip('智能体 创作者中心申请API：https://chatglm.cn/developersPanel/apiSet')
                    input_zhipu_assistant_api_api_secret = ui.input(
                        label='智能体API Secret', 
                        placeholder='智能体 创作者中心申请API：https://chatglm.cn/developersPanel/apiSet', 
                        value=config.get("zhipu", "assistant_api", "api_secret")
                    ).style("width:150px").tooltip('智能体 创作者中心申请API：https://chatglm.cn/developersPanel/apiSet')
                    input_zhipu_assistant_api_assistant_id = ui.input(
                        label='智能体ID', 
                        placeholder='智能体 ID，浏览器打开智能体对话页后，可通过URL地址栏查看，那一串英文数字', 
                        value=config.get("zhipu", "assistant_api", "assistant_id")
                    ).style("width:200px").tooltip('智能体 ID，浏览器打开智能体对话页后，可通过URL地址栏查看，那一串英文数字')

    if config.get("webui", "show_card", "llm", "my_wenxinworkshop"): 
        with ui.card().style(card_css):
            ui.label("千帆大模型")
            with ui.row():
                select_my_wenxinworkshop_type = ui.select(
                    label='类型', 
                    options={"千帆大模型": "千帆大模型", "AppBuilder": "AppBuilder"}, 
                    value=config.get("my_wenxinworkshop", "type")
                ).style("width:150px")
                switch_my_wenxinworkshop_history_enable = ui.switch('上下文记忆', value=config.get("my_wenxinworkshop", "history_enable")).style(switch_internal_css)
                input_my_wenxinworkshop_history_max_len = ui.input(label='最大记忆长度', value=config.get("my_wenxinworkshop", "history_max_len"), placeholder='最长能记忆的问答字符串长度，超长会丢弃最早记忆的内容，请慎用！配置过大可能会有丢大米')
                switch_my_wenxinworkshop_stream = ui.switch('流式输出', value=config.get("my_wenxinworkshop", "stream")).tooltip("是否开启流式输出，开启后，回答会逐句输出，关闭后，回答会一次性输出。")
            
            with ui.row():
                input_my_wenxinworkshop_api_key = ui.input(label='api_key', value=config.get("my_wenxinworkshop", "api_key"), placeholder='千帆大模型平台，开通对应服务。应用接入-创建应用，填入api key')
                input_my_wenxinworkshop_secret_key = ui.input(label='secret_key', value=config.get("my_wenxinworkshop", "secret_key"), placeholder='千帆大模型平台，开通对应服务。应用接入-创建应用，填入secret key')
                lines = [
                    "ERNIEBot",
                    "ERNIEBot_turbo",
                    "ERNIEBot_4_0",
                    "ERNIE_SPEED_128K",
                    "ERNIE_SPEED_8K",
                    "ERNIE_LITE_8K",
                    "ERNIE_LITE_8K_0922",
                    "ERNIE_TINY_8K",
                    "BLOOMZ_7B",
                    "LLAMA_2_7B",
                    "LLAMA_2_13B",
                    "LLAMA_2_70B",
                    "ERNIEBot_4_0",
                    "QIANFAN_BLOOMZ_7B_COMPRESSED",
                    "QIANFAN_CHINESE_LLAMA_2_7B",
                    "CHATGLM2_6B_32K",
                    "AQUILACHAT_7B",
                    "ERNIE_BOT_8K",
                    "CODELLAMA_7B_INSTRUCT",
                    "XUANYUAN_70B_CHAT",
                    "CHATLAW",
                    "QIANFAN_BLOOMZ_7B_COMPRESSED",
                ]
                data_json = {}
                for line in lines:
                    data_json[line] = line
                select_my_wenxinworkshop_model = ui.select(
                    label='模型', 
                    options=data_json, 
                    value=config.get("my_wenxinworkshop", "model")
                ).style("width:150px")
                
                input_my_wenxinworkshop_temperature = ui.input(label='温度', value=config.get("my_wenxinworkshop", "temperature"), placeholder='(0, 1.0] 控制生成文本的随机性。较高的温度值会使生成的文本更随机和多样化，而较低的温度值会使生成的文本更加确定和一致。').style("width:200px;")
                input_my_wenxinworkshop_top_p = ui.input(label='前p个选择', value=config.get("my_wenxinworkshop", "top_p"), placeholder='[0, 1.0] Nucleus采样。这个参数控制模型从累积概率大于一定阈值的令牌中进行采样。较高的值会产生更多的多样性，较低的值会产生更少但更确定的回答。').style("width:200px;")
                input_my_wenxinworkshop_penalty_score = ui.input(label='惩罚得分', value=config.get("my_wenxinworkshop", "penalty_score"), placeholder='[1.0, 2.0] 在生成文本时对某些词语或模式施加的惩罚。这是一种调节生成内容的机制，用来减少或避免不希望出现的内容。').style("width:200px;")
            with ui.row():
                input_my_wenxinworkshop_app_id = ui.input(label='AppBuilder 应用ID', value=config.get("my_wenxinworkshop", "app_id"), placeholder='千帆AppBuilder平台，个人空间 应用 应用ID').style("width:200px;")
                input_my_wenxinworkshop_app_token = ui.input(label='AppBuilder app_token', value=config.get("my_wenxinworkshop", "app_token"), placeholder='千帆AppBuilder平台，我的应用-应用配置-发布详情-我的Agent应用-API调用，填入app_token').style("width:200px;")
                


    
    if config.get("webui", "show_card", "llm", "gemini"):
        with ui.card().style(card_css):
            ui.label("Gemini")
            with ui.row():
                input_gemini_api_key = ui.input(label='api_key', value=config.get("gemini", "api_key"), placeholder='谷歌AI Studio创建api key')
                lines = [
                    "gemini-pro",
                ]
                data_json = {}
                for line in lines:
                    data_json[line] = line
                select_gemini_model = ui.select(
                    label='模型', 
                    options=data_json, 
                    value=config.get("gemini", "model")
                ).style("width:150px")
                switch_gemini_history_enable = ui.switch('上下文记忆', value=config.get("gemini", "history_enable")).style(switch_internal_css)
                input_gemini_history_max_len = ui.input(label='最大记忆长度', value=config.get("gemini", "history_max_len"), placeholder='最长能记忆的问答字符串长度，超长会丢弃最早记忆的内容，请慎用！配置过大可能会有丢大米')
            with ui.row():
                input_gemini_http_proxy = ui.input(label='HTTP代理地址', value=config.get("gemini", "http_proxy"), placeholder='http代理地址，需要魔法才能使用，所以需要配置此项。').style("width:200px;")
                input_gemini_https_proxy = ui.input(label='HTTPS代理地址', value=config.get("gemini", "https_proxy"), placeholder='https代理地址，需要魔法才能使用，所以需要配置此项。').style("width:200px;")
            with ui.row():
                input_gemini_max_output_tokens = ui.input(label='最大输出token数', value=config.get("gemini", "max_output_tokens"), placeholder='候选输出中包含的最大token数')
                input_gemini_max_temperature = ui.input(label='temperature', value=config.get("gemini", "temperature"), placeholder='控制输出的随机性。值范围为[0.0,1.0]，包括0.0和1.0。值越接近1.0，生成的响应将更加多样化和创造性，而值越接近0.0，通常会导致模型产生更加直接的响应。')
                input_gemini_top_p = ui.input(label='top_p', value=config.get("gemini", "top_p"), placeholder='在抽样时考虑的标记的最大累积概率。根据其分配的概率对标记进行排序，以仅考虑最可能的标记。Top-k采样直接限制要考虑的标记的最大数量，而Nucleus采样则基于累积概率限制标记的数量。')
                input_gemini_top_k = ui.input(label='top_k', value=config.get("gemini", "top_k"), placeholder='在抽样时考虑的标记的最大数量。Top-k采样考虑一组top_k最有可能的标记。默认值为40。')

    if config.get("webui", "show_card", "llm", "anythingllm"):
        with ui.card().style(card_css):
            ui.label("AnythingLLM")
            with ui.row():
                input_anythingllm_api_ip_port = ui.input(
                    label='API地址', 
                    value=config.get("anythingllm", "api_ip_port"), 
                    placeholder='anythingllm启动后API监听的ip端口地址',
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                )
    
                input_anythingllm_api_key = ui.input(label='API密钥', value=config.get("anythingllm", "api_key"), placeholder='API密钥，设置里面获取')
                select_anythingllm_mode = ui.select(
                    label='模式', 
                    options={'chat': '聊天', 'query': '仅查询知识库'}, 
                    value=config.get("anythingllm", "mode")
                ).style("width:200px")
                select_anythingllm_workspace_slug = ui.select(
                    label='工作区slug', 
                    options={config.get("anythingllm", "workspace_slug"): config.get("anythingllm", "workspace_slug")}, 
                    value=config.get("anythingllm", "workspace_slug")
                ).style("width:200px")

                def anythingllm_get_workspaces_list():
                    try:
                        from utils.gpt_model.anythingllm import AnythingLLM

                        tmp_config = config.get("anythingllm")
                        tmp_config["api_ip_port"] = input_anythingllm_api_ip_port.value
                        tmp_config["api_key"] = input_anythingllm_api_key.value

                        anythingllm = AnythingLLM(tmp_config)

                        workspaces_list = anythingllm.get_workspaces_list()
                        data_json = {}
                        for workspace_info in workspaces_list:
                            data_json[workspace_info['slug']] = workspace_info['slug']

                        select_anythingllm_workspace_slug.set_options(data_json)
                        select_anythingllm_workspace_slug.set_value(config.get("anythingllm", "workspace_slug"))

                        logger.info("读取工作区成功")
                        ui.notify(position="top", type="positive", message="读取工作区成功")
                    except Exception as e:
                        logger.error(f"读取工作区失败！\n{e}")
                        ui.notify(position="top", type="negative", message=f"读取工作区失败！\n{e}")

                button_anythingllm_get_workspaces_list = ui.button('获取所有工作区slug', on_click=lambda: anythingllm_get_workspaces_list(), color=button_internal_color).style(button_internal_css)
        

    if config.get("webui", "show_card", "llm", "tongyi"):           
        with ui.card().style(card_css):
            ui.label("通义千问/阿里云百炼")
            with ui.row():
                lines = ['web', 'api']
                data_json = {}
                for line in lines:
                    data_json[line] = line
                select_tongyi_type = ui.select(
                    label='类型', 
                    options=data_json, 
                    value=config.get("tongyi", "type")
                ).style("width:100px")
                input_tongyi_cookie_path = ui.input(label='cookie路径', placeholder='web类型下，通义千问登录后，通过浏览器插件Cookie Editor获取Cookie JSON串，然后将数据保存在这个路径的文件中', value=config.get("tongyi", "cookie_path"))
                input_tongyi_cookie_path.style("width:400px")
            with ui.row():
                lines = [
                    'qwen-turbo', 
                    'qwen-plus', 
                    'qwen-long', 
                    'qwen-max-longcontext', 
                    'qwen-max', 
                    'qwen-max-0428', 
                    'baichuan2-turbo', 
                    'moonshot-v1-8k', 
                    'moonshot-v1-32k', 
                    'moonshot-v1-128k',
                    'yi-large',
                    'yi-large-turbo',
                    'yi-medium',
                ]
                data_json = {}
                for line in lines:
                    data_json[line] = line
                select_tongyi_model = ui.select(
                    label='类型', 
                    options=data_json, 
                    value=config.get("tongyi", "model"),
                    with_input=True,
                    new_value_mode='add-unique',
                    clearable=True
                ).style("width:150px")
                input_tongyi_api_key = ui.input(label='密钥', value=config.get("tongyi", "api_key"), placeholder='API类型下，DashScope平台申请的API密钥')
                input_tongyi_preset = ui.input(label='预设', placeholder='API类型下，用于指定一组预定义的设置，以便模型更好地适应特定的对话场景。', value=config.get("tongyi", "preset")).style("width:500px") 
                input_tongyi_temperature = ui.input(label='temperature', value=config.get("tongyi", "temperature"), placeholder='控制输出的随机性。').style("width:100px")
                input_tongyi_top_p = ui.input(label='top_p', value=config.get("tongyi", "top_p"), placeholder='在抽样时考虑的标记的最大累积概率。根据其分配的概率对标记进行排序，以仅考虑最可能的标记。Top-k采样直接限制要考虑的标记的最大数量，而Nucleus采样则基于累积概率限制标记的数量。').style("width:100px")
                input_tongyi_top_k = ui.input(label='top_k', value=config.get("tongyi", "top_k"), placeholder='在抽样时考虑的标记的最大数量。Top-k采样考虑一组top_k最有可能的标记。默认值为40。').style("width:100px")
                switch_tongyi_enable_search = ui.switch('联网搜索', value=config.get("tongyi", "enable_search")).style(switch_internal_css)
                
            with ui.row():
                switch_tongyi_history_enable = ui.switch('上下文记忆', value=config.get("tongyi", "history_enable")).style(switch_internal_css)
                input_tongyi_history_max_len = ui.input(label='最大记忆长度', value=config.get("tongyi", "history_max_len"), placeholder='最长能记忆的问答字符串长度，超长会丢弃最早记忆的内容，请慎用！配置过大可能会有丢大米')
                switch_tongyi_stream = ui.switch('流式输出', value=config.get("tongyi", "stream")).tooltip("是否开启流式输出，开启后，回答会逐句输出，关闭后，回答会一次性输出。")
            
    if config.get("webui", "show_card", "llm", "dify"):
        with ui.card().style(card_css):
            ui.label("Dify")
            with ui.row():
                input_dify_api_ip_port = ui.input(
                    label="API地址", 
                    value=config.get("dify", "api_ip_port"), 
                    placeholder='Dify API地址，从应用的API文档复制过来即可', 
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                ).style("width:200px;").tooltip('Dify API地址，从应用的API文档复制过来即可')
                input_dify_api_key = ui.input(label='API密钥', value=config.get("dify", "api_key"), placeholder='API密钥，API页面获取').tooltip('API密钥，API页面获取')
                select_dify_type = ui.select(
                    label='应用类型', 
                    options={'聊天助手': '聊天助手', '工作流': '工作流'}, 
                    value=config.get("dify", "type")
                ).style("width:200px")
                switch_dify_stream = ui.switch('流式响应', value=config.get("dify", "stream")).style(switch_internal_css)
                
                switch_dify_history_enable = ui.switch('上下文记忆', value=config.get("dify", "history_enable")).style(switch_internal_css)
                textarea_dify_custom_params = ui.textarea(
                    label=f"工作流自定义参数（JSON）", 
                    value=config.get("dify", "custom_params"), 
                    placeholder='inputs传递的参数，注意JSON格式',
                ).style("width:200px;").tooltip('发送HTTP请求的API链接')
    if config.get("webui", "show_card", "llm", "volcengine"):
        with ui.card().style(card_css):
            ui.label("火山引擎")
            with ui.row():
                input_volcengine_model = ui.input(label='模型ID', value=config.get("volcengine", "model"), placeholder='推理接入点名称').tooltip('推理接入点名称')
                
                input_volcengine_api_key = ui.input(label='API密钥', value=config.get("volcengine", "api_key"), placeholder='API密钥，API页面获取').tooltip('API密钥，API页面获取')
                input_volcengine_preset = ui.input(label='预设', value=config.get("volcengine", "preset"), placeholder='用于指定一组预定义的设置，以便模型更好地适应特定的对话场景。').style("width:500px") 
                switch_volcengine_history_enable = ui.switch('上下文记忆', value=config.get("volcengine", "history_enable")).style(switch_internal_css)
                input_volcengine_history_max_len = ui.input(label='最大记忆长度', value=config.get("volcengine", "history_max_len"), placeholder='最长能记忆的问答字符串长度，超长会丢弃最早记忆的内容，请慎用！配置过大可能会有丢大米')
                switch_volcengine_stream = ui.switch('流式输出', value=config.get("volcengine", "stream")).style(switch_internal_css)
                

    if config.get("webui", "show_card", "llm", "custom_llm"):
        with ui.card().style(card_css):
            ui.label("自定义LLM")
            with ui.row():
                textarea_custom_llm_url = ui.textarea(
                    label=f"API URL", 
                    value=config.get("custom_llm", "url"), 
                    placeholder='发送HTTP请求的API链接', 
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                ).style("width:200px;").tooltip('发送HTTP请求的API链接')
                textarea_custom_llm_method = ui.select(label=f"API类型", value=config.get("custom_llm", "method"), options={"GET": "GET", "POST": "POST"}).style("width:100px;").tooltip('API类型')
                textarea_custom_llm_headers = ui.textarea(label=f"请求头", value=config.get("custom_llm", "headers"), placeholder='换行分隔，例：Content-Type:application/json\nAuthorization:Bearer sk').style("width:300px;").tooltip('换行分隔，例：Content-Type:application/json\nAuthorization:Bearer sk')
                textarea_custom_llm_proxies = ui.textarea(label=f"代理", value=config.get("custom_llm", "proxies"), placeholder='requests库代理配置方法，json数据用"双引号').style("width:200px;").tooltip('requests库代理配置方法，json数据用"双引号')
            with ui.row():
                select_custom_llm_body_type = ui.select(label=f"请求体类型", value=config.get("custom_llm", "body_type"), options={"json": "json", "raw": "raw"}).style("width:150px;").tooltip('请求体类型')
                textarea_custom_llm_body = ui.textarea(label=f"请求体", value=config.get("custom_llm", "body"), placeholder='请求体，写字符串，注意变量需要两个大括号包裹{{}}，json数据的话用"双引号').style("width:300px;").tooltip('请求体，写字符串，注意变量需要两个大括号包裹{{}}，json数据的话用"双引号')
                select_custom_llm_resp_data_type = ui.select(label=f"请求返回数据类型", value=config.get("custom_llm", "resp_data_type"), options={"json": "json", "content": "content"}).style("width:150px;").tooltip('请求返回数据类型')
                textarea_custom_llm_data_analysis = ui.textarea(label=f"数据解析（eval执行）", value=config.get("custom_llm", "data_analysis"), placeholder='数据解析，请不要随意修改resp变量，会被用于最后返回数据内容的解析').style("width:300px;").tooltip('数据解析，请不要随意修改resp变量，会被用于最后返回数据内容的解析')
                textarea_custom_llm_resp_template = ui.textarea(label=f"返回内容模板", value=config.get("custom_llm", "resp_template"), placeholder='请不要随意删除data变量，支持动态变量，最终会合并成完成内容进行音频合成').style("width:300px;").tooltip('请不要随意删除data变量，支持动态变量，最终会合并成完成内容进行音频合成')

    if config.get("webui", "show_card", "llm", "llm_tpu"): 
        with ui.card().style(card_css):
            ui.label("LLM_TPU")
            with ui.row():
                input_llm_tpu_api_ip_port = ui.input(
                    label='API地址', 
                    value=config.get("llm_tpu", "api_ip_port"), 
                    placeholder='llm_tpu启动gradio web demo后监听的ip端口地址',
                    validation={
                        '请输入正确格式的URL': lambda value: common.is_url_check(value),
                    }
                )
                switch_llm_tpu_history_enable = ui.switch('上下文记忆', value=config.get("llm_tpu", "history_enable")).style(switch_internal_css)
                input_llm_tpu_history_max_len = ui.input(label='最大记忆长度', value=config.get("llm_tpu", "history_max_len"), placeholder='最长能记忆的问答字符串长度，超长会丢弃最早记忆的内容，请慎用！配置过大可能会有丢大米')
            
            with ui.row():
                input_llm_tpu_max_length = ui.input(label='max_length', value=config.get("llm_tpu", "max_length"), placeholder='max_length').style("width:200px;")
                input_llm_tpu_temperature = ui.input(label='温度', value=config.get("llm_tpu", "temperature"), placeholder='(0, 1.0] 控制生成文本的随机性。较高的温度值会使生成的文本更随机和多样化，而较低的温度值会使生成的文本更加确定和一致。').style("width:200px;")
                input_llm_tpu_top_p = ui.input(label='前p个选择', value=config.get("llm_tpu", "top_p"), placeholder='[0, 1.0] Nucleus采样。这个参数控制模型从累积概率大于一定阈值的令牌中进行采样。较高的值会产生更多的多样性，较低的值会产生更少但更确定的回答。').style("width:200px;")
                

    def save_openai(config_data):
        if config.get("webui", "show_card", "llm", "chatgpt"):
            openai_config = config_data.setdefault("openai", {})
            openai_config["api"] = input_openai_api.value
            openai_config["api_key"] = common_textarea_handle(textarea_openai_api_key.value)

    mapping = {}
    if config.get("webui", "show_card", "llm", "chatgpt"):
        # logger.info(select_chatgpt_model.value)

        mapping["chatgpt"] = {
            "model": (select_chatgpt_model, 'str'),
            "temperature": (input_chatgpt_temperature, 'float'),
            "max_tokens": (input_chatgpt_max_tokens, 'int'),
            "top_p": (input_chatgpt_top_p, 'float'),
            "presence_penalty": (input_chatgpt_presence_penalty, 'float'),
            "frequency_penalty": (input_chatgpt_frequency_penalty, 'float'),
            "preset": (input_chatgpt_preset, 'str'),
            "stream": (switch_chatgpt_stream, 'bool'),
        }



    if config.get("webui", "show_card", "llm", "chat_with_file"):
        mapping["chat_with_file"] = {
            "chat_mode": (select_chat_with_file_chat_mode, 'str'),
            "data_path": (input_chat_with_file_data_path, 'str'),
            "separator": (input_chat_with_file_separator, 'str'),
            "chunk_size": (input_chat_with_file_chunk_size, 'int'),
            "chunk_overlap": (input_chat_with_file_chunk_overlap, 'int'),
            "chain_type": (input_chat_with_file_chain_type, 'str'),
            "question_prompt": (input_chat_with_file_question_prompt, 'str'),
            "local_max_query": (input_chat_with_file_local_max_query, 'int'),
            "show_token_cost": (switch_chat_with_file_show_token_cost, 'bool'),
        }
    if config.get("webui", "show_card", "llm", "langchain_chatchat"):
        mapping["langchain_chatchat"] = {
            "api_ip_port": (input_langchain_chatchat_api_ip_port, 'str'),
            "chat_type": (select_langchain_chatchat_chat_type, 'str'),
            "history_enable": (switch_langchain_chatchat_history_enable, 'bool'),
            "history_max_len": (input_langchain_chatchat_history_max_len, 'int'),
            "llm": {
                "model_name": (input_langchain_chatchat_llm_model_name, 'str'),
                "temperature": (input_langchain_chatchat_llm_temperature, 'float'),
                "max_tokens": (input_langchain_chatchat_llm_max_tokens, 'int'),
                "prompt_name": (input_langchain_chatchat_llm_prompt_name, 'str'),
            },
            "knowledge_base": {
                "knowledge_base_name": (input_langchain_chatchat_knowledge_base_knowledge_base_name, 'str'),
                "top_k": (input_langchain_chatchat_knowledge_base_top_k, 'int'),
                "score_threshold": (input_langchain_chatchat_knowledge_base_score_threshold, 'float'),
                "model_name": (input_langchain_chatchat_knowledge_base_model_name, 'str'),
                "temperature": (input_langchain_chatchat_knowledge_base_temperature, 'float'),
                "max_tokens": (input_langchain_chatchat_knowledge_base_max_tokens, 'int'),
                "prompt_name": (input_langchain_chatchat_knowledge_base_prompt_name, 'str'),
            },
            "search_engine": {
                "search_engine_name": (select_langchain_chatchat_search_engine_search_engine_name, 'str'),
                "top_k": (input_langchain_chatchat_search_engine_top_k, 'int'),
                "model_name": (input_langchain_chatchat_search_engine_model_name, 'str'),
                "temperature": (input_langchain_chatchat_search_engine_temperature, 'float'),
                "max_tokens": (input_langchain_chatchat_search_engine_max_tokens, 'int'),
                "prompt_name": (input_langchain_chatchat_search_engine_prompt_name, 'str'),
            },
        }
    if config.get("webui", "show_card", "llm", "zhipu"):
        mapping["zhipu"] = {
            "api_key": (input_zhipu_api_key, 'str'),
            "model": (select_zhipu_model, 'str'),
            "app_id": (input_zhipu_app_id, 'str'),
            "top_p": (input_zhipu_top_p, 'str'),
            "temperature": (input_zhipu_temperature, 'str'),
            "history_enable": (switch_zhipu_history_enable, 'bool'),
            "history_max_len": (input_zhipu_history_max_len, 'str'),
            "user_info": (input_zhipu_user_info, 'str'),
            "bot_info": (input_zhipu_bot_info, 'str'),
            "bot_name": (input_zhipu_bot_name, 'str'),
            "username": (input_zhipu_username, 'str'),
            "remove_useless": (switch_zhipu_remove_useless, 'bool'),
            "stream": (switch_zhipu_stream, 'bool'),
            "assistant_api": {
                "api_key": (input_zhipu_assistant_api_api_key, 'str'),
                "api_secret": (input_zhipu_assistant_api_api_secret, 'str'),
                "assistant_id": (input_zhipu_assistant_api_assistant_id, 'str'),
            },
        }
    if config.get("webui", "show_card", "llm", "tongyi"):
        mapping["tongyi"] = {
            "type": (select_tongyi_type, 'str'),
            "cookie_path": (input_tongyi_cookie_path, 'str'),
            "api_key": (input_tongyi_api_key, 'str'),
            "model": (select_tongyi_model, 'str'),
            "preset": (input_tongyi_preset, 'str'),
            "temperature": (input_tongyi_temperature, 'float'),
            "top_p": (input_tongyi_top_p, 'float'),
            "top_k": (input_tongyi_top_k, 'int'),
            "enable_search": (switch_tongyi_enable_search, 'bool'),
            "history_enable": (switch_tongyi_history_enable, 'bool'),
            "history_max_len": (input_tongyi_history_max_len, 'int'),
            "stream": (switch_tongyi_stream, 'bool'),
        }
    if config.get("webui", "show_card", "llm", "my_wenxinworkshop"):
        mapping["my_wenxinworkshop"] = {
            "type": (select_my_wenxinworkshop_type, 'str'),
            "model": (select_my_wenxinworkshop_model, 'str'),
            "api_key": (input_my_wenxinworkshop_api_key, 'str'),
            "secret_key": (input_my_wenxinworkshop_secret_key, 'str'),
            "top_p": (input_my_wenxinworkshop_top_p, 'float'),
            "temperature": (input_my_wenxinworkshop_temperature, 'float'),
            "penalty_score": (input_my_wenxinworkshop_penalty_score, 'float'),
            "history_enable": (switch_my_wenxinworkshop_history_enable, 'bool'),
            "history_max_len": (input_my_wenxinworkshop_history_max_len, 'int'),
            "stream": (switch_my_wenxinworkshop_stream, 'bool'),
            "app_id": (input_my_wenxinworkshop_app_id, 'str'),
            "app_token": (input_my_wenxinworkshop_app_token, 'str'),
        }
    if config.get("webui", "show_card", "llm", "gemini"):
        mapping["gemini"] = {
            "api_key": (input_gemini_api_key, 'str'),
            "model": (select_gemini_model, 'str'),
            "history_enable": (switch_gemini_history_enable, 'bool'),
            "history_max_len": (input_gemini_history_max_len, 'int'),
            "http_proxy": (input_gemini_http_proxy, 'str'),
            "https_proxy": (input_gemini_https_proxy, 'str'),
            "max_output_tokens": (input_gemini_max_output_tokens, 'int'),
            "temperature": (input_gemini_max_temperature, 'float'),
            "top_p": (input_gemini_top_p, 'float'),
            "top_k": (input_gemini_top_k, 'int'),
        }
    
    if config.get("webui", "show_card", "llm", "anythingllm"):
        mapping["anythingllm"] = {
            "api_ip_port": (input_anythingllm_api_ip_port, 'str'),
            "api_key": (input_anythingllm_api_key, 'str'),
            "mode": (select_anythingllm_mode, 'str'),
            "workspace_slug": (select_anythingllm_workspace_slug, 'str'),
        }
    if config.get("webui", "show_card", "llm", "dify"):
        mapping["dify"] = {
            "api_ip_port": (input_dify_api_ip_port, 'str'),
            "api_key": (input_dify_api_key, 'str'),
            "type": (select_dify_type, 'str'),
            "history_enable": (switch_dify_history_enable, 'bool'),
            "stream": (switch_dify_stream, 'bool'),
            "custom_params": (textarea_dify_custom_params, 'str'),  
        }
    if config.get("webui", "show_card", "llm", "volcengine"):
        mapping["volcengine"] = {
            "api_key": (input_volcengine_api_key, 'str'),
            "model": (input_volcengine_model, 'str'),
            "preset": (input_volcengine_preset, 'str'),
            "history_enable": (switch_volcengine_history_enable, 'bool'),
            "history_max_len": (input_volcengine_history_max_len, 'int'),
            "stream": (switch_volcengine_stream, 'bool'),
        }
    if config.get("webui", "show_card", "llm", "custom_llm"):
        mapping["custom_llm"] = {
            "url": (textarea_custom_llm_url, 'str'),
            "method": (textarea_custom_llm_method, 'str'),
            "headers": (textarea_custom_llm_headers, 'str'),
            "proxies": (textarea_custom_llm_proxies, 'str'),
            "body_type": (select_custom_llm_body_type, 'str'),
            "body": (textarea_custom_llm_body, 'str'),
            "resp_data_type": (select_custom_llm_resp_data_type, 'str'),
            "data_analysis": (textarea_custom_llm_data_analysis, 'str'),
            "resp_template": (textarea_custom_llm_resp_template, 'str'),
        }
    if config.get("webui", "show_card", "llm", "llm_tpu"):
        mapping["llm_tpu"] = {
            "api_ip_port": (input_llm_tpu_api_ip_port, 'str'),
            "history_enable": (switch_llm_tpu_history_enable, 'bool'),
            "history_max_len": (input_llm_tpu_history_max_len, 'int'),
            "max_length": (input_llm_tpu_max_length, 'float'),
            "temperature": (input_llm_tpu_temperature, 'float'),
            "top_p": (input_llm_tpu_top_p, 'float'),
        }



    return PageConfig(mapping=mapping, on_save=save_openai)
