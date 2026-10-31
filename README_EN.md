<div align="center">
  <a href="https://ikaros-521.github.io/Luna-Docs/site/">
    <img src="./docs/icon.png" width="240" height="240" alt="Luna AI">
  </a>
</div>

<div align="center">

[简体中文](./README.md) | [English](./README_EN.md)

</div>

<div align="center">

# ✨ Luna AI ✨

[![][python]][python]
[![][github-release-shield]][github-release-link]
[![][github-stars-shield]][github-stars-link]
[![][github-forks-shield]][github-forks-link]
[![][github-issues-shield]][github-issues-link]  
[![][github-contributors-shield]][github-contributors-link]
[![][github-license-shield]][github-license-link]
[![][FOSSA-Status]][FOSSA-Status]

</div>

`Luna AI` is a virtual AI streamer built on state-of-the-art AI technology. At its core is a wide range of LLMs and platforms — `GPT, Claude, langchain, ChatGLM, Zhipu AI, Alibaba Bailian (Qwen, Baichuan, Moonshot, Yi, MiniMax), Baidu Qianfan (ERNIE Bot), Gemini, Kimi Chat, FastGPT, Ollama, One-API, AnythingLLM, LLM_TPU, Dify, Volcengine (Doubao)` — running either locally or via cloud services. To ground conversations in the real world, Luna AI also integrates multimodal models (`Gemini`, `glm-4v`) for image recognition: it can capture your screen and talk about what it sees.

Luna AI's appearance is powered by `Live2D, VTube Studio, xuniren, UE5 + Audio2Face, EasyAIVtuber, digital-human video players (Easy-Wav2Lip, SadTalker, GeneFace++, MuseTalk, AniTalker, local video), metahuman-stream (ernerf, musetalk, wav2lip), DH_live, live2d-TTS-LLM-GPT-SoVITS-Vtuber`, providing a lively, interactive virtual avatar. This lets Luna AI stream and interact in real time on platforms such as `Bilibili, Douyin, Kuaishou, WeChat Channels, Pinduoduo, 1688, Douyu, Taobao, YouTube, Twitch and TikTok` — or simply chat with you locally.

> Danmaku (live comments) for `Pinduoduo, 1688, Douyu, Taobao, Kuaishou2` are not pulled from those platforms directly. Instead, the 「Live Danmaku Monitor Assistant」 (a Tampermonkey userscript) pushes them to Luna AI over a local websocket, so they share a single entry `直播弹幕监听助手 (Live Danmaku Monitor Assistant)` in the platform dropdown (the legacy platform names in `config.json` still work — no manual migration needed). The listening address is configured under `通用配置 → 功能管理 → 平台相关 → 直播弹幕监听助手` (the `live_monitor_assistant` section of `config.json`, default `127.0.0.1:5001`); which room to monitor is decided on the assistant side, so leave `直播间号` empty. This channel currently handles comments and gifts (`type` = `comment` / `gift`); `like` events have no handler and are ignored, and entrance/follow events do not flow through it. Gifts scraped this way only carry the gift name (no count or price), so they are recorded as `1 × ¥0` — to trigger gift-thank broadcasts on this channel, set `感谢 → 礼物感谢最低值` to `0`. Gift-name based integrations (points, key mapping, custom commands) are unaffected.

For natural-sounding speech, Luna AI combines NLP with text-to-speech systems such as `Edge-TTS, VITS-Fast, elevenlabs, VALL-E-X, Reecho AI, OpenVoice, GPT-SoVITS, clone-voice, Azure TTS, fish-speech, ChatTTS, CosyVoice, F5-TTS, MultiTTS, MeloTTS`, and can further change its voice via `so-vits-svc` and `DDSP-SVC` to fit different scenes and characters.

Luna AI can also collaborate with `Stable Diffusion` to paint on request, and can loop custom copywriting playlists for any occasion.

```
Free for personal use. Commercial use requires the author's authorization (10% revenue share).
If you find a reskinned copy of this program for sale, it is pirated — please stay away.
```

<a href="//space.bilibili.com/3709626/channel/collectiondetail?sid=1422512" target="_blank">▶︎ Video Tutorials (Bilibili)</a>
<span> | </span>
<a href="//ikaros521.eu.org/site">📄 Online Docs</a>
<span> | </span>
<a href="//github.com/Ikaros-521/AI-Vtuber" target="_blank">🍉 GitHub</a>
<span> | </span>
<a href="//gitee.com/ikaros-521/AI-Vtuber" target="_blank">🍓 Gitee</a>
<span> | </span>
<a href="http://qm.qq.com/cgi-bin/qm/qr?_wv=1027&k=Q9vzZr7a2BUt3Nk0LDKZOVFaQ7lYUYEn&authKey=ze2sFJ7v5S6ffgpXoRh80H4c5%2FejPXc2OydSg%2FuAS4YZey6VuKxS%2FyUK0SuEHYjH&noverify=0&group_code=996470582" target="_blank">🐧 QQ Group</a>

![Mind Map](./docs/xmind.png)

## 💡 How to Ask Questions

Before opening an issue, please read this first:

https://lug.ustc.edu.cn/wiki/doc/smart-questions (Chinese; see also [How To Ask Questions The Smart Way](http://www.catb.org/~esr/faqs/smart-questions.html))

## 🀅 Development & Project

Backend layering and key design decisions: [docs/backend-architecture.md](./docs/backend-architecture.md) (entry layer / app services / the six `luna` domain packages, the config singleton, threading model, and how to add an LLM/TTS provider). A docs index lives at [docs/README.md](./docs/README.md).

You can develop online with GitHub Codespaces:

[![][github-codespace-shield]][github-codespace-link]  

### Starting the WebUI

The WebUI is `webui_server` (FastAPI backend) + `webui_react` (React frontend), served from a single port:

```bash
python -m webui_server          # reads webui.ip / webui.port from config.json by default
WEBUI_V3_PORT=8082 python -m webui_server   # override the port via env when it is taken
```

- The browser **opens automatically** once the server is ready; set `WEBUI_V3_NO_OPEN=1` to disable (automation/testing).
- A stale instance from a previous forced exit would hold the port: on startup Luna detects it and, if it is a leftover `webui_server`, **reclaims it together with its child processes** (main.py etc.); if the port is held by something else, the PID is logged and nothing is killed — pick another port or close it yourself.
- Manual URL: `http://127.0.0.1:<webui.port>`; `Scripts/1.双击我启动程序.bat` points to webui_server.
- The frontend build (`webui_react/dist/`) ships with the repo — **no Node required** for normal use.

Node is only needed when changing frontend code (development only):

```bash
cd webui_react
npm install && npm run build    # rebuild; output in dist/ (hashed filenames, committed to the repo)
npm run dev                     # dev mode: port 5173, /api proxied to the local webui_server
```

> The `/set_config` `/sys_cmd` `/send` `/callback` `/tts` `/llm` endpoints of main.py are served
> as-is by `webui_server` — external scripts keep working unchanged.

### Dependency Layers

`requirements/` is grouped by feature. The core group is all you need to run; add groups as you enable features:

| Group | Contents | When needed |
| --- | --- | --- |
| `core.txt` | WebUI (FastAPI backend + React frontend), local chat, edge-tts, mic capture, text processing | Always (61 packages) |
| `llm.txt` | SDKs for Zhipu / Qwen / Qianfan / Gemini / Volcengine / Dify etc. | When using the matching `chat_type` |
| `tts.txt` | elevenlabs, Azure TTS, gradio_client | When using the matching TTS |
| `asr.txt` | FunASR, Faster-Whisper (pulls in torch) | Local speech recognition |
| `platform.txt` | Bilibili / Douyin / Kuaishou / TikTok / YouTube danmaku & reverse-engineered protocols | Matching live platforms |
| `visual.txt` | OpenCV, Pillow, virtual camera, SD, pyautogui | Digital humans / painting / desktop automation |
| `chat-with-file.txt` | Chat with files: OpenAI embeddings + faiss retrieval | Enabling `chat_with_file` |

The Bilibili danmaku library `blivedm` is not installed from pip: upstream 1.1.2 pins `aiohttp`/`yarl` to `~=3.9`/`~=1.9`, which conflicts at dependency-resolution level with the `aiohttp>=3.14` required by the core group — and it only uses aiohttp APIs that have not changed in years. It is therefore vendored at `vendor/blivedm/` (MIT, original license included, code unmodified). See the README in that directory.

`pyproject.toml` merely mirrors these groups as Poetry dependency groups (`[tool.poetry.group.*]`) for Poetry tooling; `requirements/` remains the source of truth for installation, and wins on any mismatch.

```bash
# Minimal install: use the lock file — you get the exact environment the repo was verified with
uv venv --python 3.10 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements/core.lock.txt

# Add a feature group on top of core
uv pip install --python .venv/Scripts/python.exe -r requirements/llm.txt

# Full install (equivalent to the old requirements.txt)
pip install -r requirements.txt
```

`core.lock.txt` and `core+<group>.lock.txt` are generated with uv (Python 3.10). **Always resolve in a clean virtualenv**: `uv pip compile --python <venv>` prefers versions already installed in that environment, so resolving in a used environment silently pins transitive dependencies to old versions.

```bash
# Recreate a clean interpreter environment before each re-resolve
uv venv --python 3.10 .venv-res

uv pip compile requirements/core.txt --python .venv-res/Scripts/python.exe -o requirements/core.lock.txt

# Groups containing gitee fork packages need --no-build-isolation (those forks import requests in setup.py)
uv pip compile requirements/core.txt requirements/llm.txt --python .venv-res/Scripts/python.exe --no-build-isolation -o requirements/core+llm.lock.txt
```

The `platform` group lock is generated too (`requirements/core+platform.lock.txt`): since `bilibili-api-python` 17.4.2 no longer caps `requests`/`httpx`/`aiohttp`/`brotli`, it resolves cleanly with core. Note that 17.x switched login to the async `login_v2` and removed the GeeTest-captcha password login — use `cookie` or `QR code` login for Bilibili.

#### Still-Pinned Packages

| Package | Version | Why pinned |
| --- | --- | --- |
| `pydub` | 0.25.1 | Latest on PyPI; upstream has not published in years |
| `jieba` / `langid` / `profanity` | last releases | Upstreams unmaintained but still working |
| `grpclib` | 0.3.2 | Pinned by `betterproto 2.0.0b1`; 0.4 needs a betterproto stable release |

Constraints that used to bite but are resolved — don't treat them as limits anymore: `fastapi`/`starlette` (nicegui 1.x pinned `fastapi<0.110`, unlocked with nicegui 3.18, later removed entirely), `aiohttp`/`yarl` (blivedm pinned `~=3.9`/`~=1.9`, resolved by vendoring it), `numpy`/`opencv` (numpy 2 was feared to break faiss-cpu/opencv ABI; in practice faiss 1.15.1 needs only `numpy>=1.25` and opencv 5 works with numpy 2.2.6 — both upgraded). `websockets` 16 requires `gradio_client>=2.7` (1.10.3 pinned `<16`).

### Unit Tests

Runnable with just the `core` group — no model keys, no internet:

```bash
uv pip install --python .venv/Scripts/python.exe -r requirements/dev.txt
python -m pytest
```

Tests live in `tests/unit/`, covering: the interaction pipeline and filters, the local QA database, limited-time deduplication, shared-state lock concurrency, the config singleton, HTTP-client proxy normalization, audio queue/playback, the LLM provider registry, and the internal API + WebUI backend (FastAPI TestClient). `tests/manual/` holds manual integration scripts per platform/model (real keys and internet required) — never collected by pytest; `testpaths` is pinned to `tests/unit` in `pyproject.toml`.

GitHub Actions runs `pytest` + the smoke test on every push — see `.github/workflows/ci.yml`.

### Smoke Test

After changing dependencies or core code, run this first to confirm the main chain still works:

```bash
python tools/smoke_test.py               # config check + core module imports + platform registry + boot the WebUI and request the home page
python tools/smoke_test.py --skip-webui   # static checks only (incl. platform registry)
```

The test points `LUNA_CONFIG_PATH` at a temporary copy and uses a free port — it never touches your `config.json` and does not require stopping a running instance.

### Simple Flow Charts

![image](./docs/simple_flowchart.png)
![image](./docs/chart.jpg)

## License

[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2FIkaros-521%2FAI-Vtuber.svg?type=large&issueType=license)](https://app.fossa.com/projects/git%2BIkaros-521%2FAI-Vtuber?ref=badge_large&issueType=license) 

## ⭐️ Star History

[![Star History Chart](https://api.star-history.com/svg?repos=Ikaros-521/AI-Vtuber&type=Date)](https://star-history.com/#Ikaros-521/AI-Vtuber&Date)

## 🤝 Contributing

### 🎉 Contributors

Thanks to everyone who has contributed to this project:

<a href="https://github.com/Ikaros-521/AI-Vtuber/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=Ikaros-521/AI-Vtuber" />
</a>

### 💸 Investors

![image](./docs/投资人/invest.png)

### 🌏 Partners

AIHubMix: [aihubmix.com](https://aihubmix.com/register?aff=1BMI) — LLM API proxy for OpenAI, Google, Qwen and more

Xunlei Accelerator: [jsq.xunlei.com](https://jsq.xunlei.com/) — new users can redeem code `ikaros` for free acceleration.

### 🙌 Sponsor

<div>
  <img src="https://images.cnblogs.com/cnblogs_com/ikaros-521/2328032/o_230719075908_%E6%94%AF%E4%BB%98%E5%AE%9D.png" style="width: 200px;">
  <img src="https://images.cnblogs.com/cnblogs_com/ikaros-521/2328032/o_230719075908_%E5%BE%AE%E4%BF%A1.png" style="width: 230px;">
</div>

[FOSSA-Status]: https://app.fossa.com/api/projects/git%2Bgithub.com%2FIkaros-521%2FAI-Vtuber.svg?type=shield&labelColor=black&issueType=license
[python]: https://img.shields.io/badge/python-3.10+-blue.svg?labelColor=black
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
[github-stars-link]: https://github.com/Ikaros-521/AI-Vtuber/network/stargazers
[github-stars-shield]: https://img.shields.io/github/stars/Ikaros-521/AI-Vtuber?color=ffcb47&labelColor=black&style=flat-square
