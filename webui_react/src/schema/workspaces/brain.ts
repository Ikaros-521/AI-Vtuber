/** 人设与大脑工作区：LLM 各家 provider、对话与回复模板、本地问答、翻译、图像识别。

 * 字段与 config 键逐项对齐 v2 llm.py / translate.py / image_recognition.py /
 * common_config.py（对话模板那排裸 row 在 v2 就归这页，本地问答同理）。
 */
import type { Field, Workspace } from '../types'

const CHATGPT_PRESET_MODELS = [
  'gpt-3.5-turbo', 'gpt-3.5-turbo-instruct', 'gpt-3.5-turbo-0125', 'gpt-4', 'gpt-4-turbo-preview',
  'gpt-4-0125-preview', 'gpt-4o', 'gpt-4o-mini', 'text-embedding-3-large', 'text-embedding-3-small',
  'text-davinci-003', 'rwkv', 'chatglm3-6b', 'moonshot-v1-8k', 'gemma:2b', 'qwen', 'qwen:1.8b-chat',
]

const LLM_HISTORY = (prefix: (string | number)[]): Field[] => [
  { kind: 'switch', key: [...prefix, 'history_enable'], label: '上下文记忆' },
  { kind: 'number', key: [...prefix, 'history_max_len'], label: '最大记忆长度', w: 'md', int: true, placeholder: '最长能记忆的问答字符串长度，超长会丢弃最早记忆的内容，请慎用！配置过大可能会有丢大米' },
]

export const brainWorkspace: Workspace = {
  id: 'brain',
  title: '人设与大脑',
  groups: [
    {
      title: '模型引擎 (LLM)',
      sections: [
        {
          id: 'llm-chatgpt',
          title: 'OpenAI / Ollama / 通用模型',
          showCard: ['llm', 'chatgpt'],
          desc: '兼容 OpenAI 标准接口协议的大语言模型服务（如 ChatGPT、DeepSeek、Moonshot、通义千问兼容端点等）。',
          rows: [
            [
              { kind: 'input', key: ['openai', 'api'], label: 'API地址', w: 'lg', placeholder: 'API请求地址，支持代理' },
              { kind: 'string-list', key: ['openai', 'api_key'], label: 'API密钥', w: 'lg', placeholder: 'API KEY，支持多个（换行分隔）' },
              { kind: 'action', key: ['_action', 'test'], label: '测试可用性', w: 'sm', action: 'llm-test', params: { base_url: ['openai', 'api'], api_keys: ['openai', 'api_key'], model: ['chatgpt', 'model'], temperature: ['chatgpt', 'temperature'], max_tokens: ['chatgpt', 'max_tokens'], top_p: ['chatgpt', 'top_p'], presence_penalty: ['chatgpt', 'presence_penalty'], frequency_penalty: ['chatgpt', 'frequency_penalty'], preset: ['chatgpt', 'preset'] } },
            ],
            [
              { kind: 'select', key: ['chatgpt', 'model'], label: '模型', w: 'md', free: true, options: Object.fromEntries(CHATGPT_PRESET_MODELS.map((m) => [m, m])), dynamicOptions: 'llm-models', hint: '没找到你用的模型名就直接手输；搜索来的和你手输的都会保留' },
              { kind: 'action', key: ['_action', 'models'], label: '搜索模型', w: 'sm', action: 'llm-models', params: { base_url: ['openai', 'api'], api_keys: ['openai', 'api_key'] }, hint: '用上面的 API地址 + 密钥列表里的第一个 key 请求 /v1/models，把返回的模型名填进左边的下拉框' },
              { kind: 'number', key: ['chatgpt', 'temperature'], label: '温度', w: 'sm', placeholder: '控制生成文本的随机性，高更随机，低更确定' },
              { kind: 'number', key: ['chatgpt', 'max_tokens'], label: '最大token数', w: 'sm', int: true, placeholder: '限制生成回答的最大长度' },
              { kind: 'number', key: ['chatgpt', 'top_p'], label: 'top_p', w: 'sm', placeholder: 'Nucleus采样' },
              { kind: 'switch', key: ['chatgpt', 'stream'], label: '流式输出', hint: '开启后回答逐句输出，关闭后一次性输出' },
            ],
            [
              { kind: 'number', key: ['chatgpt', 'presence_penalty'], label: '存在惩罚', w: 'sm', placeholder: '较高的值会减少模型对给定提示的重复程度' },
              { kind: 'number', key: ['chatgpt', 'frequency_penalty'], label: '频率惩罚', w: 'sm', placeholder: '较高的值会减少重复令牌' },
              { kind: 'input', key: ['chatgpt', 'preset'], label: '预设', w: 'xl', placeholder: '用于指定一组预定义的设置，以便模型更好地适应特定的对话场景' },
            ],
          ],
        },
        {
          id: 'llm-langchain',
          title: 'Langchain_ChatChat',
          showCard: ['llm', 'langchain_chatchat'],
          desc: '基于 Langchain-ChatChat 开源框架部署的本地知识库与搜索引擎问答服务接口。',
          rows: [
            [
              { kind: 'input', key: ['langchain_chatchat', 'api_ip_port'], label: 'API地址', w: 'xl', placeholder: 'langchain_chatchat的API版本运行后的服务链接（需要完整的URL）' },
              { kind: 'select', key: ['langchain_chatchat', 'chat_type'], label: '类型', w: 'sm', options: { 模型: '模型', 知识库: '知识库', 搜索引擎: '搜索引擎' } },
              ...LLM_HISTORY(['langchain_chatchat']),
            ],
          ],
          cards: [
            {
              id: 'llm-langchain-llm',
              title: '模型',
              rows: [[
                { kind: 'input', key: ['langchain_chatchat', 'llm', 'model_name'], label: 'LLM模型', w: 'md', placeholder: '本地加载的LLM模型名' },
                { kind: 'number', key: ['langchain_chatchat', 'llm', 'temperature'], label: '温度', w: 'sm' },
                { kind: 'number', key: ['langchain_chatchat', 'llm', 'max_tokens'], label: 'max_tokens', w: 'sm', int: true, placeholder: '大于0的正整数，不建议太大，你可能会爆显存' },
                { kind: 'input', key: ['langchain_chatchat', 'llm', 'prompt_name'], label: 'Prompt模板', w: 'md', placeholder: '本地存在的提示词模板文件名' },
              ]],
            },
            {
              id: 'llm-langchain-kb',
              title: '知识库',
              rows: [[
                { kind: 'input', key: ['langchain_chatchat', 'knowledge_base', 'knowledge_base_name'], label: '知识库名', w: 'md', placeholder: '本地添加的知识库名，运行时会自动检索存在的知识库列表输出到日志' },
                { kind: 'number', key: ['langchain_chatchat', 'knowledge_base', 'top_k'], label: '匹配搜索结果条数', w: 'sm', int: true },
                { kind: 'number', key: ['langchain_chatchat', 'knowledge_base', 'score_threshold'], label: '知识匹配分数阈值', w: 'sm', placeholder: '0.00-2.00之间' },
                { kind: 'input', key: ['langchain_chatchat', 'knowledge_base', 'model_name'], label: 'LLM模型', w: 'md' },
                { kind: 'number', key: ['langchain_chatchat', 'knowledge_base', 'temperature'], label: '温度', w: 'sm' },
                { kind: 'number', key: ['langchain_chatchat', 'knowledge_base', 'max_tokens'], label: 'max_tokens', w: 'sm', int: true },
                { kind: 'input', key: ['langchain_chatchat', 'knowledge_base', 'prompt_name'], label: 'Prompt模板', w: 'md' },
              ]],
            },
            {
              id: 'llm-langchain-search',
              title: '搜索引擎',
              rows: [[
                { kind: 'select', key: ['langchain_chatchat', 'search_engine', 'search_engine_name'], label: '搜索引擎', w: 'sm', options: { bing: 'bing', duckduckgo: 'duckduckgo', metaphor: 'metaphor' } },
                { kind: 'number', key: ['langchain_chatchat', 'search_engine', 'top_k'], label: '匹配搜索结果条数', w: 'sm', int: true },
                { kind: 'input', key: ['langchain_chatchat', 'search_engine', 'model_name'], label: 'LLM模型', w: 'md' },
                { kind: 'number', key: ['langchain_chatchat', 'search_engine', 'temperature'], label: '温度', w: 'sm' },
                { kind: 'number', key: ['langchain_chatchat', 'search_engine', 'max_tokens'], label: 'max_tokens', w: 'sm', int: true },
                { kind: 'input', key: ['langchain_chatchat', 'search_engine', 'prompt_name'], label: 'Prompt模板', w: 'md' },
              ]],
            },
          ],
        },
        {
          id: 'llm-zhipu',
          title: '智谱AI',
          showCard: ['llm', 'zhipu'],
          desc: '智谱开放平台 GLM 系列大语言模型服务（支持联网搜索与代码执行）。',
          rows: [
            [
              { kind: 'input', key: ['zhipu', 'api_key'], label: 'api key', w: 'md', placeholder: '具体参考官方文档，申请地址：https://open.bigmodel.cn/usercenter/apikeys' },
              { kind: 'select', key: ['zhipu', 'model'], label: '模型', w: 'md', free: true, options: Object.fromEntries(['应用', '智能体', 'glm-3-turbo', 'glm-4', 'glm-4-flash', 'charglm-3', 'characterglm', 'chatglm_turbo', 'chatglm_pro', 'chatglm_std', 'chatglm_lite', 'chatglm_lite_32k'].map((m) => [m, m])) },
              { kind: 'input', key: ['zhipu', 'app_id'], label: '应用ID', w: 'md', placeholder: '在 模型为：应用 时，从日志里复制你需要的应用ID' },
            ],
            [
              { kind: 'input', key: ['zhipu', 'top_p'], label: 'top_p', w: 'sm', placeholder: '(0.0,1.0) 开区间' },
              { kind: 'input', key: ['zhipu', 'temperature'], label: 'temperature', w: 'sm', placeholder: '(0.0,1.0] 采样温度' },
              ...LLM_HISTORY(['zhipu']),
            ],
            [
              { kind: 'input', key: ['zhipu', 'user_info'], label: '用户信息', w: 'lg', placeholder: '当使用characterglm时需要配置' },
              { kind: 'input', key: ['zhipu', 'bot_info'], label: '角色信息', w: 'lg', placeholder: '当使用characterglm时需要配置' },
              { kind: 'input', key: ['zhipu', 'bot_name'], label: '角色名称', w: 'sm' },
              { kind: 'input', key: ['zhipu', 'username'], label: '用户名称', w: 'sm', placeholder: '默认值为用户' },
            ],
            [
              { kind: 'switch', key: ['zhipu', 'remove_useless'], label: '删除无用字符' },
              { kind: 'switch', key: ['zhipu', 'stream'], label: '流式输出' },
            ],
          ],
          cards: [
            {
              id: 'llm-zhipu-assistant',
              title: '智能体',
              rows: [[
                { kind: 'input', key: ['zhipu', 'assistant_api', 'api_key'], label: '智能体API Key', w: 'md', placeholder: '智能体 创作者中心申请API：https://chatglm.cn/developersPanel/apiSet' },
                { kind: 'input', key: ['zhipu', 'assistant_api', 'api_secret'], label: '智能体API Secret', w: 'md', placeholder: '同上' },
                { kind: 'input', key: ['zhipu', 'assistant_api', 'assistant_id'], label: '智能体ID', w: 'lg', placeholder: '浏览器打开智能体对话页后，URL地址栏那串英文数字' },
              ]],
            },
          ],
        },
        {
          id: 'llm-wenxin',
          title: '千帆大模型',
          showCard: ['llm', 'my_wenxinworkshop'],
          desc: '百度智能云千帆大模型平台（文心一言 ERNIE 系列模型接口）。',
          rows: [
            [
              { kind: 'select', key: ['my_wenxinworkshop', 'type'], label: '类型', w: 'sm', options: { 千帆大模型: '千帆大模型', AppBuilder: 'AppBuilder' } },
              ...LLM_HISTORY(['my_wenxinworkshop']),
              { kind: 'switch', key: ['my_wenxinworkshop', 'stream'], label: '流式输出' },
            ],
            [
              { kind: 'input', key: ['my_wenxinworkshop', 'api_key'], label: 'api_key', w: 'lg', placeholder: '千帆大模型平台，应用接入-创建应用，填入api key' },
              { kind: 'input', key: ['my_wenxinworkshop', 'secret_key'], label: 'secret_key', w: 'lg', placeholder: '应用接入-创建应用，填入secret key' },
              { kind: 'select', key: ['my_wenxinworkshop', 'model'], label: '模型', w: 'md', options: Object.fromEntries(['ERNIEBot', 'ERNIEBot_turbo', 'ERNIEBot_4_0', 'ERNIE_SPEED_128K', 'ERNIE_SPEED_8K', 'ERNIE_LITE_8K', 'ERNIE_LITE_8K_0922', 'ERNIE_TINY_8K', 'BLOOMZ_7B', 'LLAMA_2_7B', 'LLAMA_2_13B', 'LLAMA_2_70B', 'QIANFAN_BLOOMZ_7B_COMPRESSED', 'QIANFAN_CHINESE_LLAMA_2_7B', 'CHATGLM2_6B_32K', 'AQUILACHAT_7B', 'ERNIE_BOT_8K', 'CODELLAMA_7B_INSTRUCT', 'XUANYUAN_70B_CHAT', 'CHATLAW'].map((m) => [m, m])) },
              { kind: 'number', key: ['my_wenxinworkshop', 'temperature'], label: '温度', w: 'sm', placeholder: '(0, 1.0]' },
              { kind: 'number', key: ['my_wenxinworkshop', 'top_p'], label: '前p个选择', w: 'sm', placeholder: '[0, 1.0]' },
              { kind: 'number', key: ['my_wenxinworkshop', 'penalty_score'], label: '惩罚得分', w: 'sm', placeholder: '[1.0, 2.0]' },
            ],
            [
              { kind: 'input', key: ['my_wenxinworkshop', 'app_id'], label: 'AppBuilder 应用ID', w: 'md', placeholder: '千帆AppBuilder平台，个人空间 应用 应用ID' },
              { kind: 'input', key: ['my_wenxinworkshop', 'app_token'], label: 'AppBuilder app_token', w: 'lg', placeholder: '我的应用-应用配置-发布详情-API调用，填入app_token' },
            ],
          ],
        },
        {
          id: 'llm-gemini',
          title: 'Gemini',
          showCard: ['llm', 'gemini'],
          desc: 'Google 谷歌多模态大语言模型，具备极高的响应速度与丰富的知识储备。',
          rows: [
            [
              { kind: 'input', key: ['gemini', 'api_key'], label: 'api_key', w: 'lg', placeholder: '谷歌AI Studio创建api key' },
              { kind: 'select', key: ['gemini', 'model'], label: '模型', w: 'sm', free: true, options: { 'gemini-pro': 'gemini-pro' } },
              ...LLM_HISTORY(['gemini']),
            ],
            [
              { kind: 'input', key: ['gemini', 'http_proxy'], label: 'HTTP代理地址', w: 'md', placeholder: '需要魔法才能使用，所以需要配置此项' },
              { kind: 'input', key: ['gemini', 'https_proxy'], label: 'HTTPS代理地址', w: 'md', placeholder: '需要魔法才能使用，所以需要配置此项' },
            ],
            [
              { kind: 'number', key: ['gemini', 'max_output_tokens'], label: '最大输出token数', w: 'sm', int: true },
              { kind: 'number', key: ['gemini', 'temperature'], label: 'temperature', w: 'sm' },
              { kind: 'number', key: ['gemini', 'top_p'], label: 'top_p', w: 'sm' },
              { kind: 'number', key: ['gemini', 'top_k'], label: 'top_k', w: 'sm', placeholder: '默认值为40' },
            ],
          ],
        },
        {
          id: 'llm-anythingllm',
          title: 'AnythingLLM',
          showCard: ['llm', 'anythingllm'],
          desc: '对接 AnythingLLM 工作区 API，将整套本地工作区文档库集成进直播问答中。',
          rows: [
            [
              { kind: 'input', key: ['anythingllm', 'api_ip_port'], label: 'API地址', w: 'lg', placeholder: 'anythingllm启动后API监听的ip端口地址' },
              { kind: 'input', key: ['anythingllm', 'api_key'], label: 'API密钥', w: 'md', placeholder: 'API密钥，设置里面获取' },
              { kind: 'select', key: ['anythingllm', 'mode'], label: '模式', w: 'md', options: { chat: '聊天', query: '仅查询知识库' } },
              { kind: 'select', key: ['anythingllm', 'workspace_slug'], label: '工作区slug', w: 'md', free: true, options: {}, dynamicOptions: 'anythingllm-slugs' },
              { kind: 'action', key: ['_action', 'slugs'], label: '获取所有工作区slug', w: 'md', action: 'anythingllm-workspaces', params: { api_ip_port: ['anythingllm', 'api_ip_port'], api_key: ['anythingllm', 'api_key'] } },
            ],
          ],
        },
        {
          id: 'llm-tongyi',
          title: '通义千问/阿里云百炼',
          showCard: ['llm', 'tongyi'],
          desc: '阿里云通义千问（Qwen）官方大模型 API，支持超长上下文与丰富的系统人设。',
          rows: [
            [
              { kind: 'select', key: ['tongyi', 'type'], label: '类型', w: 'xs', options: { web: 'web', api: 'api' } },
              { kind: 'input', key: ['tongyi', 'cookie_path'], label: 'cookie路径', w: 'xl', placeholder: 'web类型下，通义千问登录后用浏览器插件 Cookie Editor 导出 JSON 存到这个路径' },
            ],
            [
              { kind: 'select', key: ['tongyi', 'model'], label: '模型', w: 'md', free: true, options: Object.fromEntries(['qwen-turbo', 'qwen-plus', 'qwen-long', 'qwen-max-longcontext', 'qwen-max', 'qwen-max-0428', 'baichuan2-turbo', 'moonshot-v1-8k', 'moonshot-v1-32k', 'moonshot-v1-128k', 'yi-large', 'yi-large-turbo', 'yi-medium'].map((m) => [m, m])) },
              { kind: 'input', key: ['tongyi', 'api_key'], label: '密钥', w: 'md', placeholder: 'API类型下，DashScope平台申请的API密钥' },
              { kind: 'input', key: ['tongyi', 'preset'], label: '预设', w: 'xl', placeholder: 'API类型下，用于指定一组预定义的设置' },
              { kind: 'number', key: ['tongyi', 'temperature'], label: 'temperature', w: 'xs' },
              { kind: 'number', key: ['tongyi', 'top_p'], label: 'top_p', w: 'xs' },
              { kind: 'number', key: ['tongyi', 'top_k'], label: 'top_k', w: 'xs' },
              { kind: 'switch', key: ['tongyi', 'enable_search'], label: '联网搜索' },
            ],
            [
              { kind: 'switch', key: ['tongyi', 'history_enable'], label: '上下文记忆' },
              { kind: 'number', key: ['tongyi', 'history_max_len'], label: '最大记忆长度', w: 'md', int: true },
              { kind: 'switch', key: ['tongyi', 'stream'], label: '流式输出' },
            ],
          ],
        },
        {
          id: 'llm-dify',
          title: 'Dify',
          showCard: ['llm', 'dify'],
          desc: '对接 Dify.ai 企业级大语言模型工作流/Agent 平台，支持复杂提示词编排与多工具协同。',
          rows: [
            [
              { kind: 'input', key: ['dify', 'api_ip_port'], label: 'API地址', w: 'md', placeholder: 'Dify API地址，从应用的API文档复制过来即可' },
              { kind: 'input', key: ['dify', 'api_key'], label: 'API密钥', w: 'md', placeholder: 'API密钥，API页面获取' },
              { kind: 'select', key: ['dify', 'type'], label: '应用类型', w: 'sm', options: { 聊天助手: '聊天助手', 工作流: '工作流' } },
              { kind: 'switch', key: ['dify', 'stream'], label: '流式响应' },
              { kind: 'switch', key: ['dify', 'history_enable'], label: '上下文记忆' },
              { kind: 'textarea', key: ['dify', 'custom_params'], label: '工作流自定义参数（JSON）', w: 'lg', placeholder: 'inputs传递的参数，注意JSON格式' },
            ],
          ],
        },
        {
          id: 'llm-volcengine',
          title: '火山引擎',
          showCard: ['llm', 'volcengine'],
          desc: '字节跳动火山引擎豆包（Doubao）大语言模型 API 接入。',
          rows: [
            [
              { kind: 'input', key: ['volcengine', 'model'], label: '模型ID', w: 'md', placeholder: '推理接入点名称' },
              { kind: 'input', key: ['volcengine', 'api_key'], label: 'API密钥', w: 'md', placeholder: 'API密钥，API页面获取' },
              { kind: 'input', key: ['volcengine', 'preset'], label: '预设', w: 'xl', placeholder: '用于指定一组预定义的设置' },
              { kind: 'switch', key: ['volcengine', 'history_enable'], label: '上下文记忆' },
              { kind: 'number', key: ['volcengine', 'history_max_len'], label: '最大记忆长度', w: 'md', int: true },
              { kind: 'switch', key: ['volcengine', 'stream'], label: '流式输出' },
            ],
          ],
        },
        {
          id: 'llm-custom',
          title: '自定义LLM',
          showCard: ['llm', 'custom_llm'],
          desc: '自定义通用 HTTP 接口，可灵活对接任意遵循标准 JSON 格式的自建大模型或第三方中转服务。',
          rows: [
            [
              { kind: 'textarea', key: ['custom_llm', 'url'], label: 'API URL', w: 'md', placeholder: '发送HTTP请求的API链接' },
              { kind: 'select', key: ['custom_llm', 'method'], label: 'API类型', w: 'xs', options: { GET: 'GET', POST: 'POST' } },
              { kind: 'textarea', key: ['custom_llm', 'headers'], label: '请求头', w: 'lg', placeholder: '换行分隔，例：Content-Type:application/json\nAuthorization:Bearer sk' },
              { kind: 'textarea', key: ['custom_llm', 'proxies'], label: '代理', w: 'md', placeholder: 'requests库代理配置方法，json数据用"双引号' },
            ],
            [
              { kind: 'select', key: ['custom_llm', 'body_type'], label: '请求体类型', w: 'sm', options: { json: 'json', raw: 'raw' } },
              { kind: 'textarea', key: ['custom_llm', 'body'], label: '请求体', w: 'lg', placeholder: '写字符串，注意变量需要两个大括号包裹{{}}，json数据用"双引号' },
              { kind: 'select', key: ['custom_llm', 'resp_data_type'], label: '请求返回数据类型', w: 'sm', options: { json: 'json', content: 'content' } },
              { kind: 'textarea', key: ['custom_llm', 'data_analysis'], label: '数据解析（eval执行）', w: 'lg', placeholder: '请不要随意修改resp变量，会被用于最后返回数据内容的解析' },
              { kind: 'textarea', key: ['custom_llm', 'resp_template'], label: '返回内容模板', w: 'lg', placeholder: '请不要随意删除data变量，支持动态变量' },
            ],
          ],
        },
      ],
    },
    {
      title: '人设与知识',
      sections: [
        {
          id: 'chat-template',
          title: '对话与回复模板',
          desc: '追在弹幕前后发给 LLM 的提示词，以及弹幕/回复内容的改写模板。',
          rows: [
            [
              { kind: 'select', key: ['need_lang'], label: '回复语言', w: 'sm', options: { none: '所有', zh: '中文', en: '英文', jp: '日文' }, hint: '限制回复的语言，如：选中中文，则只会回复中文提问，其他语言将被跳过' },
              { kind: 'input', key: ['before_prompt'], label: '提示词前缀', w: 'md', placeholder: '此配置会追加在弹幕前，再发送给LLM处理' },
              { kind: 'input', key: ['after_prompt'], label: '提示词后缀', w: 'md', placeholder: '此配置会追加在弹幕后，再发送给LLM处理' },
            ],
            [
              { kind: 'switch', key: ['comment_template', 'enable'], label: '启用弹幕模板' },
              { kind: 'input', key: ['comment_template', 'copywriting'], label: '弹幕模板', w: 'xl', placeholder: '此配置会对弹幕内容进行修改，{}内为变量，会被替换为指定内容，请勿随意删除变量' },
              { kind: 'switch', key: ['reply_template', 'enable'], label: '启用回复模板' },
              { kind: 'number', key: ['reply_template', 'username_max_len'], label: '回复用户名的最大长度', w: 'sm', int: true },
            ],
            [
              { kind: 'string-list', key: ['reply_template', 'copywriting'], label: '回复模板', w: 'xl', placeholder: '此配置会对LLM回复内容进行修改，{}内为变量，会被替换为指定内容，请勿随意删除变量' },
            ],
          ],
        },
        {
          id: 'local-qa',
          title: '本地问答',
          showCard: ['common_config', 'local_qa'],
          desc: '优先于大模型的预设问答库：命中关键词时秒回预设文案，不耗 Token 且回答 100% 精准。',
          rows: [
            [
              { kind: 'switch', key: ['local_qa', 'periodic_trigger', 'enable'], label: '周期性触发启用' },
              { kind: 'number', key: ['local_qa', 'periodic_trigger', 'periodic_time_min'], label: '触发周期最小值', w: 'sm', int: true },
              { kind: 'number', key: ['local_qa', 'periodic_trigger', 'periodic_time_max'], label: '触发周期最大值', w: 'sm', int: true },
              { kind: 'number', key: ['local_qa', 'periodic_trigger', 'trigger_num_min'], label: '触发次数最小值', w: 'sm', int: true },
              { kind: 'number', key: ['local_qa', 'periodic_trigger', 'trigger_num_max'], label: '触发次数最大值', w: 'sm', int: true },
            ],
            [
              { kind: 'switch', key: ['local_qa', 'text', 'enable'], label: '启用文本匹配' },
              { kind: 'select', key: ['local_qa', 'text', 'type'], label: '问答数据类型', w: 'sm', options: { json: '自定义json', text: '一问一答' } },
              { kind: 'input', key: ['local_qa', 'text', 'file_path'], label: '文本问答数据路径', w: 'md', placeholder: '本地问答文本数据存储路径；json 文件也在这里填' },
              { kind: 'number', key: ['local_qa', 'text', 'similarity'], label: '文本最低相似度', w: 'sm', placeholder: '低于就会被当做一般弹幕处理' },
              { kind: 'number', key: ['local_qa', 'text', 'username_max_len'], label: '用户名最大长度', w: 'sm', int: true },
            ],
            [
              { kind: 'switch', key: ['local_qa', 'audio', 'enable'], label: '启用音频匹配' },
              { kind: 'input', key: ['local_qa', 'audio', 'file_path'], label: '音频存储路径', w: 'md', placeholder: '本地问答音频文件存储路径' },
              { kind: 'number', key: ['local_qa', 'audio', 'similarity'], label: '音频最低相似度', w: 'sm', placeholder: '和本地音频库文件名的最低相似度' },
            ],
            [
              { kind: 'file-json', key: ['local_qa', 'text', 'file_path'], label: 'JSON文件内容', w: 'xl', hint: '「问答数据类型」为 自定义json 时生效：加载上面的路径，改完保存写回文件' },
            ],
          ],
        },
      ],
    },
    {
      title: '多模态与翻译',
      sections: [
        {
          id: 'image-recognition',
          title: '图像识别',
          desc: '截图/摄像头取图后交给 Gemini 或智谱分析，结果作为复读消息发送。',
          rows: [
            [
              { kind: 'switch', key: ['image_recognition', 'enable'], label: '启用' },
              { kind: 'select', key: ['image_recognition', 'model'], label: '模型', w: 'sm', options: { gemini: 'gemini', zhipu: '智谱AI' } },
              { kind: 'input', key: ['image_recognition', 'img_save_path'], label: '截图保存路径', w: 'md', placeholder: '支持绝对或相对路径' },
              { kind: 'input', key: ['image_recognition', 'prompt'], label: '携带的提示词', w: 'xl', placeholder: '图片识别时附带的提示词，协同图片获取回答' },
            ],
          ],
          cards: [
            {
              id: 'img-screenshot',
              title: '电脑截图',
              desc: '截取指定窗口画面，交由多模态模型进行视觉识别与实时解说。截图识别需要核心程序在运行。',
              rows: [
                [
                  { kind: 'select', key: ['image_recognition', 'screenshot_window_title'], label: '截图窗口标题', w: 'lg', options: {}, dynamicOptions: 'window-titles', free: true },
                  { kind: 'action', key: ['_action', 'win-list'], label: '刷新窗口列表', w: 'sm', action: 'window-titles' },
                  { kind: 'number', key: ['image_recognition', 'screenshot_delay'], label: 'N秒后进行截图', w: 'sm', placeholder: '截图延迟，方便打开对应窗口' },
                  { kind: 'action', key: ['_action', 'shot'], label: '截图并发送', w: 'sm', action: 'img-screenshot', params: { source: 'window', title_or_index: ['image_recognition', 'screenshot_window_title'], img_save_path: ['image_recognition', 'img_save_path'], prompt: ['image_recognition', 'prompt'], model: ['image_recognition', 'model'] } },
                ],
                [
                  { kind: 'switch', key: ['image_recognition', 'loop_screenshot_enable'], label: '循环截图并发送', hint: '由核心程序按下面的间隔自动截图识别' },
                  { kind: 'number', key: ['image_recognition', 'loop_screenshot_delay'], label: 'N秒后自动截图', w: 'sm', int: true, placeholder: '自动截图延迟' },
                ],
              ],
            },
            {
              id: 'img-cam',
              title: '摄像头截图',
              rows: [
                [
                  { kind: 'switch', key: ['image_recognition', 'cam_screenshot_enable'], label: '启用' },
                  { kind: 'select', key: ['image_recognition', 'cam_index'], label: '摄像头索引', w: 'xs', options: {}, dynamicOptions: 'cameras' },
                  { kind: 'action', key: ['_action', 'cam-list'], label: '刷新摄像头列表', w: 'sm', action: 'cameras' },
                  { kind: 'number', key: ['image_recognition', 'cam_screenshot_delay'], label: 'N秒后进行截图', w: 'sm' },
                  { kind: 'action', key: ['_action', 'shot'], label: '截图并发送', w: 'sm', action: 'img-screenshot', params: { source: 'camera', title_or_index: ['image_recognition', 'cam_index'], img_save_path: ['image_recognition', 'img_save_path'], prompt: ['image_recognition', 'prompt'], model: ['image_recognition', 'model'] } },
                ],
                [
                  { kind: 'switch', key: ['image_recognition', 'loop_cam_screenshot_enable'], label: '循环截图并发送' },
                  { kind: 'number', key: ['image_recognition', 'loop_cam_screenshot_delay'], label: 'N秒后自动截图', w: 'sm', int: true },
                ],
              ],
            },
            {
              id: 'img-gemini',
              title: 'Gemini',
              rows: [[
                { kind: 'select', key: ['image_recognition', 'gemini', 'model'], label: '模型', w: 'md', options: { 'gemini-pro-vision': 'gemini-pro-vision' } },
                { kind: 'input', key: ['image_recognition', 'gemini', 'api_key'], label: 'API Key', w: 'md' },
                { kind: 'input', key: ['image_recognition', 'gemini', 'http_proxy'], label: 'HTTP代理地址', w: 'md' },
                { kind: 'input', key: ['image_recognition', 'gemini', 'https_proxy'], label: 'HTTPS代理地址', w: 'md' },
              ]],
            },
            {
              id: 'img-zhipu',
              title: '智谱AI',
              rows: [[
                { kind: 'select', key: ['image_recognition', 'zhipu', 'model'], label: '模型', w: 'sm', options: { 'glm-4v': 'glm-4v' } },
                { kind: 'input', key: ['image_recognition', 'zhipu', 'api_key'], label: 'API Key', w: 'md' },
              ]],
            },
          ],
        },
        {
          id: 'translate',
          title: '翻译设置',
          desc: '直播双语翻译：支持观众外语弹幕实时中译、主播回复自动外译，降低跨语种直播门槛。',
          rows: [
            [
              { kind: 'switch', key: ['translate', 'enable'], label: '启用' },
              { kind: 'select', key: ['translate', 'type'], label: '类型', w: 'sm', options: { baidu: '百度翻译', google: '谷歌翻译' } },
              { kind: 'select', key: ['translate', 'trans_type'], label: '翻译类型', w: 'md', options: { 弹幕: '弹幕', 回复: '回复', '弹幕+回复': '弹幕+回复' } },
            ],
          ],
          cards: [
            {
              id: 'translate-baidu',
              title: '百度翻译',
              desc: '对接百度翻译开放平台官方 API 接口。',
              rows: [[
                { kind: 'input', key: ['translate', 'baidu', 'appid'], label: 'APP ID', w: 'md', placeholder: '翻译开放平台 开发者中心 APP ID' },
                { kind: 'input', key: ['translate', 'baidu', 'appkey'], label: '密钥', w: 'md', placeholder: '翻译开放平台 开发者中心 密钥' },
                { kind: 'select', key: ['translate', 'baidu', 'from_lang'], label: '源语言', w: 'sm', options: { auto: '自动检测', zh: '中文', cht: '繁体中文', en: '英文', jp: '日文', kor: '韩文', yue: '粤语', wyw: '文言文' } },
                { kind: 'select', key: ['translate', 'baidu', 'to_lang'], label: '目标语言', w: 'sm', options: { zh: '中文', cht: '繁体中文', en: '英文', jp: '日文', kor: '韩文', yue: '粤语', wyw: '文言文' } },
              ]],
            },
            {
              id: 'translate-google',
              title: '谷歌翻译',
              desc: '对接 Google 在线翻译接口。',
              rows: [[
                { kind: 'input', key: ['translate', 'google', 'proxy'], label: '代理地址', w: 'lg', placeholder: '代理的完整地址，请携带协议' },
                { kind: 'select', key: ['translate', 'google', 'src_lang'], label: '源语言', w: 'sm', options: { auto: '自动', 'zh-CN': '中文', en: '英文', ja: '日文' } },
                { kind: 'select', key: ['translate', 'google', 'tgt_lang'], label: '目标语言', w: 'sm', options: { 'zh-CN': '中文', en: '英文', ja: '日文' } },
              ]],
            },
          ],
        },
      ],
    },
  ],
}
