# blivedm（内置副本）

- 上游：https://github.com/xfgryujk/blivedm ，版本 1.1.2（取自 gitee 分叉 `ikaros-521/blivedm` rev `8c5f6a910d9f755ef01a6b099b7da2e2d4453fa6`）
- 许可：MIT，见 `LICENSE`（原作者 xfgryujk，版权与许可声明原样保留）

## 为什么内置而不是 pip 依赖

上游 1.1.2 的依赖声明是：

```
aiohttp~=3.9.0
yarl~=1.9.3
Brotli~=1.1.0
```

而 nicegui 3 要求 `aiohttp>=3.14.3`，aiohttp 3.14.5 又要求 `yarl>=1.25.1`。
这三条 `~=` 让 blivedm 与 nicegui 3 **在解析器层面严格互斥**——不是版本太旧不能用，
只是声明卡得太死。

实测 blivedm 用到的 aiohttp API 只有 `ClientSession`、`ClientTimeout`、
`ClientWebSocketResponse`、`WSMessage`、`WSMsgType.BINARY`、`ClientConnectionError`，
外加 `yarl.URL` 和 `brotli.decompress`，这些在新版本里签名和行为都没变。

所以做法是：把源码内置进来、**不装 pip 包**，依赖改由 `requirements/platform.txt` 直接声明
（`brotli` 不再钉死 1.1.0）。上游若有更新，需要人工比对同步。

## 改动

代码本身**未做任何修改**，与 1.1.2 原样一致。只有本 README 和 LICENSE 是新加的。
