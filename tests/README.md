# tests/

- `unit/` — 单元测试（`python -m pytest` 只收集这里，CI 跑的也是这些）
- `manual/` — 各 provider 的手工联调例程（需要真实 key / 外网 / 音频设备，
  按需单独运行，不进 CI、不进 ruff）
