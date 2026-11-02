"""CodexReset 默认配置项。"""

from typing import Dict

from gsuid_core.utils.plugins_config.models import GSC, GsBoolConfig, GsIntConfig, GsListConfig

CONFIG_DEFAULT: Dict[str, GSC] = {
    "poll_interval": GsIntConfig(
        title="轮询间隔（分钟）",
        desc="检测 codex-reset.com 新公告的间隔，最小 1 分钟",
        data=3,
    ),
    "prob_levels": GsListConfig(
        title="概率预警梯度（%）",
        desc="24 小时重置概率逐档越过时各推送一次预警（升序），回落或新周期后重新武装",
        data=[50, 80],
    ),
    "timeline_count": GsIntConfig(
        title="记录条数",
        desc="查看记录时显示的重置历史条数",
        data=10,
    ),
    "include_origin": GsBoolConfig(
        title="提醒附带原文",
        desc="推送提醒时附带官方英文原文摘要",
        data=True,
    ),
    "ai_judge": GsBoolConfig(
        title="AI 判断生效时机",
        desc=(
            "推送「已公告待验证」类提醒时，调用 GsCore AI 分析公告原文推断预计生效时间"
            "（需在控制台启用 AI 服务并配置模型）；AI 不可用或失败时自动回退固定文案"
        ),
        data=True,
    ),
    "ai_notice": GsBoolConfig(
        title="AI 中文提醒",
        desc=(
            "推送时调用 GsCore AI 将公告原文翻译并总结为中文（时间均按北京时间表述，"
            "原帖地址保留；需启用 AI 服务）；关闭则仅显示英文原文"
        ),
        data=True,
    ),
}
