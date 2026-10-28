# AI Vtuber WebUI v3（React）

v3 分支的新版 WebUI 前端：React 19 + TypeScript + Vite + Tailwind CSS 4。
后端是独立的 FastAPI 服务（仓库根目录的 `webui_server/`），不再用 NiceGUI 服务端渲染。

## 开发

```bash
cd webui_react
npm install

# 终端 1：起后端（开发端口 8082，避免和 v2 的 webui.py 抢 webui.port）
cd .. && WEBUI_V3_PORT=8082 python -m webui_server

# 终端 2：起前端（5173，/api 自动代理到 8082）
cd webui_react && npm run dev
```

打开 http://127.0.0.1:5173 。Windows 下建议用 `LUNA_CONFIG_PATH` 指到一份测试配置，
别拿正式 config.json 做开发（v2 webui.py 也是这么干的）。

## 构建与部署

```bash
npm run build    # tsc 类型检查 + vite 构建，产物在 dist/（带 hash 文件名，已提交仓库）
python -m webui_server   # 后端自动托管 dist/，单端口即可用
```

`dist/` 随仓库分发，普通使用者不需要 Node；改了前端代码才需要重新构建并把产物一起提交。

## 架构

- **schema 驱动表单**：每个工作区是一份数据描述（`src/schema/workspaces/`），
  通用渲染器（`WorkspacePage` / `SectionCard` / `FieldControl`）负责画表单。
  移植 v2 页面 = 把 `webui_app/pages/*.py` 里的控件翻译成 schema 字段。
- **diff 保存**：前端持有 config 草稿，保存时只把改动列表发到
  `POST /api/config/save`，服务端在最新文件上打补丁（外部脚本改过的配置不会被覆盖），
  带 sha256 冲突检测与保存前校验。
- **对 v2 兼容**：`webui_server/compat_api.py` 原样保留 `/set_config` `/sys_cmd`
  `/send` `/callback` `/tts` `/llm`，main.py 与外部脚本无需改动。

## 迁移进度

**9 大工作区已全部迁移完成**（总览/聊天/直播接入/人设与大脑/声音与表现/弹幕与礼仪/互动与玩法/外设与联动/运维与系统）。

仍留在 v2 的交互件：登录页（login.enable）、数据分析 echart 图表、TTS 试听播放器、声卡设备枚举、vits「检索说话人」/MeloTTS「加载模型」按钮——对应的配置字段均可在 v3 修改。
