"""CodexReset AI 集成：纯数据工具注册 + 知识库与别名。"""

from gsuid_core.ai_core.models import KnowledgePoint
from gsuid_core.ai_core.register import ai_alias, ai_entity, ai_tools

from ..utils.api import (
    fetch_feed,
    fetch_forecast,
    fetch_status_history,
    fetch_timeline,
    format_feed,
    format_forecast,
    format_status,
    format_timeline,
)


@ai_tools(category="common")
async def get_codex_reset_forecast() -> str:
    """获取 Codex 使用限额重置的概率预测。
    当用户询问 codex 什么时候重置、重置概率多大、还有多久可能重置、预测情况时调用。无需参数。
    """
    return format_forecast(await fetch_forecast())


@ai_tools(category="common")
async def get_codex_reset_timeline(limit: int = 10) -> str:
    """获取 Codex 限额重置的历史记录时间线。
    当用户询问以前重置过几次、重置历史、上次重置是什么时候时调用。

    Args:
        limit: 返回最近多少条记录，默认 10，最大 30
    """
    limit = max(1, min(limit, 30))
    return format_timeline(await fetch_timeline(), limit)


@ai_tools(category="common")
async def get_codex_service_status() -> str:
    """获取 Codex 各端（Web/API/CLI/VS Code/桌面端）当前服务运行状态与近期事故。
    当用户询问 codex 是不是挂了、codex 服务状态、有没有事故时调用。无需参数。
    """
    return format_status(await fetch_status_history())


@ai_tools(category="common")
async def get_codex_reset_feed(limit: int = 5) -> str:
    """获取 codex-reset.com 监控的 Tibo (@thsottiaux) X 时间线与当前活跃重置信号。
    当用户询问最新动态、官方有没有说要重置、Tibo 说了什么时调用。

    Args:
        limit: 返回最近多少条推文，默认 5，最大 20
    """
    limit = max(1, min(limit, 20))
    return format_feed(await fetch_feed(), limit)


ai_entity(
    KnowledgePoint(
        id="codexreset_usage_guide",
        plugin="CodexReset",
        title="Codex 重置提醒插件使用指南",
        content=(
            "# Codex 重置提醒插件\n\n"
            "监控 codex-reset.com 的 Codex 使用限额重置情报"
            "（官方公告、重置信号、概率预测、服务状态）。\n\n"
            "## 用户命令\n"
            "- `cxcz开启提醒` — 订阅重置提醒（群聊按用户订阅，推送时 @ 订阅者；私聊直接推送）\n"
            "- `cxcz取消提醒` — 取消订阅\n"
            "- `cxcz查看记录` — 查看最近的重置历史\n"
            "- `cxcz取消推送` —（群管理员）静默本群推送，已注册的 @ 提醒保留\n"
            "- `cxcz开启推送` —（群管理员）恢复本群推送，已注册的 @ 提醒继续生效\n\n"
            "## 可调用的数据工具\n"
            "- get_codex_reset_forecast — 重置概率预测\n"
            "- get_codex_reset_timeline — 重置历史时间线\n"
            "- get_codex_service_status — Codex 服务状态\n"
            "- get_codex_reset_feed — X 最新动态与活跃重置信号\n\n"
            "## 背景知识\n"
            "Codex 重置不是固定周期，由官方（Tibo @thsottiaux）在 X 上临时公告；"
            "重置类型分「限额重置」和「赠送重置额度（banked reset）」；"
            "概率预测来自 codex-reset.com 的统计模型（rate-v3），非官方数据。"
        ),
        tags=["Codex", "codex重置", "重置", "重置提醒", "推送", "cxcz", "订阅", "提醒"],
    )
)

ai_alias("codex重置", ["cxcz", "codex reset", "CodexReset", "重置提醒", "codex重置提醒"])
