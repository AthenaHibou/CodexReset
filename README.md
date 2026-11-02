# CodexReset

GsCore 插件：监控 Codex 使用限额的**重置公告、概率预测、服务状态与历史记录**，并在重置信号出现时推送提醒。

> 数据来自 [codex-reset.com](https://codex-reset.com/)，非 OpenAI 官方接口。插件只做信息聚合与提醒，不包含任何账号操作。

## 功能

- **重置提醒**：订阅后，检测到官方重置公告、重置信号，或 24 小时重置概率越过阈值时推送。
- **群聊 @ 提醒**：群内按用户单独订阅，推送时 @ 订阅者；私聊直接推送。
- **群级开关**：群管理员可以静默 / 恢复本群推送，不影响用户单独订阅。
- **历史记录**：查看最近的 Codex 重置时间线。
- **AI 集成**：注册了概率预测、历史时间线、服务状态、X 动态四类 AI 工具；可选使用 AI 翻译 / 总结公告。
- **降级可用**：AI 不可用或关闭时，使用固定模板推送，不影响核心提醒。

## 环境要求

- Python >= 3.11
- GsCore 上游 `0.11.x`（主目标），或 `AthenaHibou/gsuid_core` 的 `main`（基于 `0.10.7` + 定制补丁）
- AI Core 可选；开启后可获得 AI 摘要、时机推断和自然语言工具调用

## 安装

### 方式一：core 安装插件（收录到插件列表后）

```text
安装插件CodexReset
```

### 方式二：手动 clone

```bash
cd gsuid_core/gsuid_core/plugins
git clone https://github.com/AthenaHibou/CodexReset
```

然后重启 Core。

## 命令

统一前缀 `cxcz`。

| 命令 | 说明 |
|---|---|
| `cxcz开启提醒` | 订阅重置提醒（群聊按用户单独订阅，私聊直接订阅） |
| `cxcz取消提醒` | 取消自己的订阅 |
| `cxcz查看记录` | 查看最近的 Codex 重置历史 |
| `cxcz取消推送` | 群管理员：静默本群推送（已注册的 @ 提醒保留） |
| `cxcz开启推送` | 群管理员：恢复本群推送 |

别名：`cxcz开启重置提醒` / `cxcz开启重置推送` / `cxcz取消重置提醒` / `cxcz取消重置推送` / `cxcz重置记录` / `cxcz重置历史`。

也可以直接让 AI 处理：例如「codex 什么时候重置」「开一下 codex 重置提醒」。

## 配置

在 Web 控制台「插件配置」中修改：

| 配置项 | 默认值 | 说明 |
|---|---|---|
| `poll_interval` | `3` | 轮询 codex-reset.com 的间隔（分钟，最少 1） |
| `prob_levels` | `[50, 80]` | 24 小时重置概率预警梯度（升序） |
| `timeline_count` | `10` | 查看历史时显示的条数 |
| `include_origin` | `true` | 推送时附带官方英文原文摘要 |
| `ai_judge` | `true` | 用 AI 推断公告的预计生效时间；失败自动回退固定文案 |
| `ai_notice` | `true` | 用 AI 翻译 / 总结公告；关闭则仅显示英文原文 |

## AI 工具

开启 AI Core 后注册如下工具：

- `get_codex_reset_forecast()`：重置概率预测
- `get_codex_reset_timeline(limit=10)`：重置历史时间线
- `get_codex_service_status()`：Web / API / CLI / VS Code / 桌面端服务状态
- `get_codex_reset_feed(limit=5)`：codex-reset.com 监控的 X 动态与活跃重置信号

## 数据源与说明

- [codex-reset.com](https://codex-reset.com/)：重置公告、概率模型、服务状态、X 动态。
- Codex 的重置不是固定周期，官方（Tibo / @thsottiaux）会在 X 上临时公告；重置类型分为「限额重置」和「赠送重置额度（banked reset）」。
- 概率预测来自 codex-reset.com 的统计模型（rate-v3），**非官方数据**，仅供参考。
- 本项目与 OpenAI、codex-reset.com 均无隶属关系。

## 兼容性

- **主目标**：上游 `Genshin-bots/gsuid_core` 的 `master`，当前为 `0.11.2`。
- **Fork 目标**：`AthenaHibou/gsuid_core` 的 `main`，基于 `0.10.7` + 定制补丁；AI Core 行为可能与上游不同。
- 代码按上游 `0.11.2` 的 API 编写；导入与关键符号已做过静态对照，实际运行仍取决于 AI Core 配置和模型状态。
- 使用了 `ai_tools`、`ai_entity`、`ai_alias`、`to_ai`、`create_agent` 等 AI Core 能力；旧核心缺少部分能力时会走降级路径。
- 使用了 `GsListConfig` 配置项与 `gs_subscribe` 订阅系统；核心接口有破坏性变更时需要同步适配。

## License

GPL-3.0-or-later。见 [LICENSE](LICENSE) 与 [NOTICE](NOTICE)。
