"""CodexReset 配置实例（网页控制台可改，实时生效）。"""

from gsuid_core.data_store import get_res_path
from gsuid_core.utils.plugins_config.gs_config import StringConfig

from .config_default import CONFIG_DEFAULT

CODEX_CONFIG = StringConfig(
    "CodexReset",
    get_res_path("CodexReset") / "config.json",
    CONFIG_DEFAULT,
)
