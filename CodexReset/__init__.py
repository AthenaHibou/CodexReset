"""CodexReset - Codex 重置提醒插件。

数据源: https://codex-reset.com/
用户命令统一使用 cxcz 前缀。
"""

from gsuid_core.sv import Plugins

Plugins(
    name="CodexReset",
    force_prefix=["cxcz"],
    allow_empty_prefix=False,
    alias=["codex重置"],
)
