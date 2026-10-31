<div align="center">
  <a href="https://ikaros-521.github.io/Luna-Docs/site/">
    <img src="./docs/icon.png" width="240" height="240" alt="Luna AI">
  </a>
</div>

<div align="center">

[简体中文](./README.md) | [English](./README_EN.md)

</div>

<div align="center">

# ✨ Luna AI  ✨



[![][python]][python]
[![][github-release-shield]][github-release-link]
[![][github-stars-shield]][github-stars-link]
[![][github-forks-shield]][github-forks-link]
[![][github-issues-shield]][github-issues-link]  
[![][github-contributors-shield]][github-contributors-link]
[![][github-license-shield]][github-license-link]
[![][FOSSA-Status]][FOSSA-Status]


</div>

`Luna AI` 是一款结合了最先进技术的虚拟AI主播。它的核心是一系列高效的人工智能模型和平台，包括 `GPT、Claude、langchain、chatglm、智谱AI、阿里云百炼（通义千问、百川、月之暗面、零一万物、MiniMax）、千帆大模型（文心一言）、Gemini、Kimi Chat、FastGPT、Ollama、One-API、AnythingLLM、LLM_TPU、Dify、火山引擎（豆包）`。这些模型既可以在本地运行，也可以通过云端服务提供支持。当然，为了让对话照进现实，还结合了多模态模型，包括 `Gemini、glm-4v` 的图像识别能力，获取电脑画面进行分析讲解。  

`Luna AI` 的外观由 `Live2D、Vtube Studio、xuniren、UE5 结合 Audio2Face、EasyAIVtuber、数字人视频播放器（Easy-Wav2Lip、Sadtalker、GeneFace++、MuseTalk、AniTalker、本地视频）、metahuman-stream（ernerf、musetalk、wav2lip）、DH_live、live2d-TTS-LLM-GPT-SoVITS-Vtuber` 技术打造，为用户提供了一个生动、互动的虚拟形象。这使得 `Luna AI` 能够在各大直播平台，如 `Bilibili、抖音、快手、微信视频号、拼多多、1688、斗鱼、淘宝、YouTube、Twitch 和 TikTok`，进行实时互动直播。当然，它也可以在本地环境中与您进行个性化对话。

> 其中 `拼多多、1688、斗鱼、淘宝、快手2` 的弹幕不是本程序直连平台，而是由「直播弹幕监听助手」（游猴）通过 websocket 推给本机，所以平台下拉里把它们合成为一项 `直播弹幕监听助手`（旧的几个平台名在 `config.json` 里仍然认，不用手改）。本机监听的 ip 和端口在 `通用配置 → 功能管理 → 平台相关 → 直播弹幕监听助手` 修改，对应 `config.json` 的 `live_monitor_assistant` 段，默认 `127.0.0.1:5001`；监听哪个直播间由助手那边决定，`直播间号` 留空即可。这条链路目前接弹幕和礼物（`type` 为 `comment`、`gift`），助手推的点赞（`like`）本程序没有对应的处理会被忽略，进场、关注也不在这条链路里。礼物只能从直播间页面上扒到文字，没有数量和价格，因此按 `1 个 / 0 元` 记录——想让这条路触发礼物感谢播报，要把 `感谢 → 礼物感谢最低值` 设成 `0`，否则会被「低于最低值不感谢」挡掉；按礼物名走的积分、按键映射、自定义命令不受影响。

为了使交流更加自然，`Luna AI` 使用了先进的自然语言处理技术，结合文本转语音系统，如 `Edge-TTS、VITS-Fast、elevenlabs、VALL-E-X、睿声AI、OpenVoice、GPT_SoVITS、clone-voice、Azure TTS、fish-speech、ChatTTS、CosyVoice、F5-TTS、MultiTTS、MeloTTS`。这不仅让它能够生成流畅的回答，还可以通过 `so-vits-svc 和 DDSP-SVC` 实现声音的变化，以适应不同的场景和角色。

此外，`Luna AI` 还能够通过特定指令与 `Stable Diffusion` 协作，展示画作。用户还可以自定义文案，让 Luna AI 循环播放，以满足不同场合的需求。

```
本项目个人使用完全免费，商用抽成10%，如需商用请联系作者授权。    
如有发现一模一样的套壳售卖程序，皆为盗版，请及时止损。  
```

<a href="//space.bilibili.com/3709626/channel/collectiondetail?sid=1422512" target="_blank">▶︎ 视频教程合集</span></a>
<span> | </span>
<a href="//ikaros521.eu.org/site">📄 在线文档</span></a>
<span> | </span>
<a href="//github.com/Ikaros-521/AI-Vtuber" target="_blank">🍉 GitHub</span></a>
<span> | </span>
<a href="//gitee.com/ikaros-521/AI-Vtuber" target="_blank">🍓 Gitee</span></a>
<span> | </span>
<a href="http://qm.qq.com/cgi-bin/qm/qr?_wv=1027&k=Q9vzZr7a2BUt3Nk0LDKZOVFaQ7lYUYEn&authKey=ze2sFJ7v5S6ffgpXoRh80H4c5%2FejPXc2OydSg%2FuAS4YZey6VuKxS%2FyUK0SuEHYjH&noverify=0&group_code=996470582" target="_blank">🐧 AI交流Q群</span></a>

![思维导图](./docs/xmind.png)

## 💡 提问的智慧

提交issues前请先阅读以下内容

https://lug.ustc.edu.cn/wiki/doc/smart-questions

## 🀅 开发&项目相关

后端分层与关键设计决策见 [docs/backend-architecture.md](./docs/backend-architecture.md)（入口层 / app 服务层 / luna 六域包、配置单例、线程模型、如何新增 LLM/TTS provider）；全部文档索引在 [docs/README.md](./docs/README.md)。

可以使用 GitHub Codespaces 进行在线开发：

[![][github-codespace-shield]][github-codespace-link]  

### 启动 WebUI（v3）

v3 起 WebUI 是 `webui_server`（FastAPI 后端）+ `webui_react`（React 前端），单端口运行：

```bash
python -m webui_server          # 默认读 config.json 的 webui.ip / webui.port
WEBUI_V3_PORT=8082 python -m webui_server   # 端口被其它程序占用时用环境变量错开
```

- 服务就绪后**自动打开浏览器**进入配置页；不想自动开（自动化/测试场景）设 `WEBUI_V3_NO_OPEN=1`。
- 上次强退残留的旧实例会占住端口：启动时会自动检测，确认是残留的 `webui_server` 就**连同它拉起的
  main.py 等子进程一起回收**；若是别的程序占用，日志会报出 PID 不做处理——这时再换端口或手动结束它。
- 手动访问地址是 `http://127.0.0.1:<webui.port>`；`Scripts/1.双击我启动程序.bat` 已指向 webui_server。
- 前端构建产物（`webui_react/dist/`）随仓库分发，普通使用**不需要装 Node**。

改前端代码才需要 Node（仅开发）：

```bash
cd webui_react
npm install && npm run build    # 重新构建，产物在 dist/（带 hash 文件名，提交仓库）
npm run dev                     # 开发模式：5173 端口，/api 自动代理到本地的 webui_server
```

> 对 main.py 的 `/set_config` `/sys_cmd` `/send` `/callback` `/tts` `/llm` 接口由
> `webui_server` 原样提供，外部脚本无需改动。

### 依赖分层

`requirements/` 按功能分组，跑起来只需要核心组，其余按用到的功能加装：

| 分组 | 内容 | 何时需要 |
| --- | --- | --- |
| `core.txt` | WebUI（FastAPI 后端 + React 前端）、本地对话、edge-tts、拾音、文本处理 | 必装（61 个包） |
| `llm.txt` | 智谱/通义/千帆/Gemini/火山引擎/Dify 等模型 SDK | 选用对应 `chat_type` |
| `tts.txt` | elevenlabs、Azure TTS、gradio_client | 选用对应 TTS |
| `asr.txt` | FunASR、Faster-Whisper（会带 torch） | 本地语音识别 |
| `platform.txt` | B站/抖音/快手/TikTok/YouTube 弹幕与逆向协议 | 对应直播平台 |
| `visual.txt` | OpenCV、Pillow、虚拟摄像头、SD、pyautogui | 数字人/绘图/桌面自动化 |
| `chat-with-file.txt` | 文档问答：OpenAI 向量化 + faiss 检索 | 启用 `chat_with_file` |

B站弹幕库 `blivedm` 不走 pip：上游 1.1.2 把 `aiohttp`/`yarl` 钉死在 `~=3.9`/`~=1.9`，与 core 组要求的 `aiohttp>=3.14` 在依赖解析层面互斥，而它实际只用到多年未变的 aiohttp API，所以源码内置在 `vendor/blivedm/`（MIT，含原许可声明，代码未改动）。详见该目录下的 README。

`pyproject.toml` 只是把上述分组镜像成 Poetry 依赖组（`[tool.poetry.group.*]`），方便用 Poetry 工具链查看；实际安装仍以 `requirements/` 为准，两处不一致时同理。

```bash
# 最小安装：直接用锁定文件，装出来的环境和仓库验证过的一致
uv venv --python 3.10 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements/core.lock.txt

# 需要某个功能时，在核心之上追加
uv pip install --python .venv/Scripts/python.exe -r requirements/llm.txt

# 全量安装（等价于以前的 requirements.txt）
pip install -r requirements.txt
```

`core.lock.txt` 以及 `core+<组>.lock.txt` 由 uv 生成（Python 3.10）。**解析要用一个空的虚拟环境**：`uv pip compile --python <venv>` 会优先沿用该环境里已经装好的版本，拿一个装过东西的环境去解析，传递依赖会被悄悄压在旧版上。

```bash
# 每次重解析前重建一个干净的解释器环境
uv venv --python 3.10 .venv-res

uv pip compile requirements/core.txt --python .venv-res/Scripts/python.exe -o requirements/core.lock.txt

# 含 gitee 分叉包的分组加 --no-build-isolation（那几个分叉的 setup.py 里直接 import 了 requests）
uv pip compile requirements/core.txt requirements/llm.txt --python .venv-res/Scripts/python.exe --no-build-isolation -o requirements/core+llm.lock.txt
```

`platform` 组的 lock 也已生成（`requirements/core+platform.lock.txt`）：`bilibili-api-python` 升到 17.4.2 后不再钉死 `requests`/`httpx`/`aiohttp`/`brotli` 上限，可与 core 合并解析。注意 17.x 的登录 API 换成了异步的 `login_v2`，且需要极验验证码的「账号密码登录」已移除，B站登录请用 `cookie` 或 `手机扫码`。

#### 仍受约束的包

| 包 | 现状 | 为什么钉在这里 |
| --- | --- | --- |
| `pydub` | 0.25.1 | 这就是 PyPI 上的最新版，上游多年不发布 |
| `jieba` / `langid` / `profanity` | 各自末版 | 上游已停止维护，功能仍可用 |
| `grpclib` | 0.3.2 | 被 `betterproto 2.0.0b1` 钉住，升 0.4 需要 betterproto 出正式版 |

历史上卡住过的几条约束都已解除，别再当限制：`fastapi`/`starlette`（nicegui 1.x 钉 `fastapi<0.110`，随 nicegui 3.18 解锁）、`aiohttp`/`yarl`（blivedm 钉 `~=3.9`/`~=1.9`，随其改为内置源码消失）、`numpy`/`opencv`（曾以为 numpy 2 会破坏 faiss-cpu/opencv 的编译扩展 ABI，实测 faiss 1.15.1 只要 `numpy>=1.25`、opencv 5 与 numpy 2.2.6 一起可用，已双双升上去）。`websockets` 16 则要求 `gradio_client>=2.7`（1.10.3 钉 `<16`）。

### 单元测试

只依赖 `core` 分组即可运行，不需要任何模型 key 或外网：

```bash
uv pip install --python .venv/Scripts/python.exe -r requirements/dev.txt
python -m pytest
```

用例放在 `tests/unit/`，覆盖：交互流水线与过滤器、本地问答库、限时去重、共享状态锁并发、
配置单例、HTTP 客户端代理规范化、音频队列/播放、LLM provider 注册表、内部 API 与 WebUI 后端
（FastAPI TestClient）。`tests/manual/` 下是各平台/模型的手工联调脚本（要真实 key 和外网），
不会被 pytest 收集——`pyproject.toml` 里已把 `testpaths` 钉在 `tests/unit`。

GitHub Actions 每次 push 都会跑一遍 `pytest` + 冒烟测试，见 `.github/workflows/ci.yml`。

### 冒烟测试

改完依赖或核心代码后，先跑这个确认主链路没被改坏：

```bash
python tools/smoke_test.py               # 配置检查 + 核心模块导入 + 平台注册表 + 启动 WebUI 并请求首页
python tools/smoke_test.py --skip-webui   # 只做静态检查（含平台注册表）
```

测试用 `LUNA_CONFIG_PATH` 指向临时副本并把端口换成空闲端口，不会动你的 `config.json`，也不需要先关掉正在运行的实例。

### 简易流程图

![image](./docs/simple_flowchart.png)
![image](./docs/chart.jpg)

## License

[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2FIkaros-521%2FAI-Vtuber.svg?type=large&issueType=license)](https://app.fossa.com/projects/git%2Bgithub.com%2FIkaros-521%2FAI-Vtuber?ref=badge_large&issueType=license) 

## ⭐️ Star 经历

[![Star History Chart](https://api.star-history.com/svg?repos=Ikaros-521/AI-Vtuber&type=Date)](https://star-history.com/#Ikaros-521/AI-Vtuber&Date)

## 🤝 贡献

### 🎉 鸣谢

感谢以下开发者对该项目做出的贡献：

<a href="https://github.com/Ikaros-521/AI-Vtuber/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Ikaros-521/AI-Vtuber" />
</a>

### 💸 投资方

![image](./docs/投资人/invest.png)

### 🌏 合作伙伴

AIHubMix: [aihubmix.com](https://aihubmix.com/register?aff=1BMI)  ———— OpenAI,Google,通义千问等大语言模型API代理站  

​迅雷加速器：[jsq.xunlei.com](https://jsq.xunlei.com/) 新用户可以凭口令领取7x24小时的免费福利加速。兑换码 口令：ikaros  

### 🙌 赞助

<div>
  <img src="https://images.cnblogs.com/cnblogs_com/ikaros-521/2328032/o_230719075908_%E6%94%AF%E4%BB%98%E5%AE%9D.png" style="width: 200px;">
  <img src="https://images.cnblogs.com/cnblogs_com/ikaros-521/2328032/o_230719075908_%E5%BE%AE%E4%BF%A1.png" style="width: 230px;">
</div>

## 🕳️ 黑名单

| 用户信息 | 名人名言 |
|--------|------|
| QQ：750359376 | 笑死，连点开源精神都没有 |
| QQ：378198682 | 【散播谣言】 |
| QQ：1939834860 | 【广告哥】 |
| QQ：1687246688 | 【白嫖还嘴臭】 |

[FOSSA-Status]: https://app.fossa.com/api/projects/git%2Bgithub.com%2FIkaros-521%2FAI-Vtuber.svg?type=shield&labelColor=black&issueType=license
[python]: https://img.shields.io/badge/python-3.10+-blue.svg?labelColor=black
[back-to-top]: https://img.shields.io/badge/-BACK_TO_TOP-black?style=flat-square
[github-action-release-link]: https://github.com/actions/workflows/Ikaros-521/AI-Vtuber/release.yml
[github-action-release-shield]: https://img.shields.io/github/actions/workflow/status/Ikaros-521/AI-Vtuber/release.yml?label=release&labelColor=black&logo=githubactions&logoColor=white&style=flat-square
[github-action-test-link]: https://github.com/actions/workflows/Ikaros-521/AI-Vtuber/test.yml
[github-action-test-shield]: https://img.shields.io/github/actions/workflow/status/Ikaros-521/AI-Vtuber/test.yml?label=test&labelColor=black&logo=githubactions&logoColor=white&style=flat-square
[github-codespace-link]: https://codespaces.new/Ikaros-521/AI-Vtuber
[github-codespace-shield]: https://github.com/codespaces/badge.svg
[github-contributors-link]: https://github.com/Ikaros-521/AI-Vtuber/graphs/contributors
[github-contributors-shield]: https://img.shields.io/github/contributors/Ikaros-521/AI-Vtuber?color=c4f042&labelColor=black&style=flat-square
[github-forks-link]: https://github.com/Ikaros-521/AI-Vtuber/network/members
[github-forks-shield]: https://img.shields.io/github/forks/Ikaros-521/AI-Vtuber?color=8ae8ff&labelColor=black&style=flat-square
[github-issues-link]: https://github.com/Ikaros-521/AI-Vtuber/issues
[github-issues-shield]: https://img.shields.io/github/issues/Ikaros-521/AI-Vtuber?color=ff80eb&labelColor=black&style=flat-square
[github-license-link]: https://github.com/Ikaros-521/AI-Vtuber/blob/main/LICENSE
[github-license-shield]: https://img.shields.io/github/license/Ikaros-521/AI-Vtuber?color=white&labelColor=black&style=flat-square
[github-release-link]: https://github.com/Ikaros-521/AI-Vtuber/releases
[github-release-shield]: https://img.shields.io/github/v/release/Ikaros-521/AI-Vtuber?color=369eff&labelColor=black&logo=github&style=flat-square
[github-releasedate-link]: https://github.com/Ikaros-521/AI-Vtuber/releases
[github-releasedate-shield]: https://img.shields.io/github/release-date/Ikaros-521/AI-Vtuber?labelColor=black&style=flat-square
[github-stars-link]: https://github.com/Ikaros-521/AI-Vtuber/network/stargazers
[github-stars-shield]: https://img.shields.io/github/stars/Ikaros-521/AI-Vtuber?color=ffcb47&labelColor=black&style=flat-square
[pr-welcome-link]: https://github.com/Ikaros-521/AI-Vtuber/pulls
[pr-welcome-shield]: https://img.shields.io/badge/%F0%9F%A4%AF%20PR%20WELCOME-%E2%86%92-ffcb47?labelColor=black&style=for-the-badge
[profile-link]: https://github.com/Ikaros-521
