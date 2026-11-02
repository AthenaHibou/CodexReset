"""CodexReset 用户命令：开启提醒 / 取消提醒 / 查看记录。"""

from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.subscribe import gs_subscribe
from gsuid_core.sv import SV

from ..cxcz_config import CODEX_CONFIG
from ..utils.api import fetch_timeline, format_timeline
from ..utils.notify import MUTE_TASK, SUBSCRIBE_TASK

sv = SV("Codex重置提醒", pm=6, area="ALL")

# 群管理员专用：控制本群是否接收推送，与用户 @ 提醒注册互不影响
sv_switch = SV("Codex推送开关", pm=3, area="GROUP")


@sv_switch.on_fullmatch(("取消推送", "关闭推送"))
async def mute_codex_push(bot: Bot, ev: Event) -> None:
    await gs_subscribe.add_subscribe("session", MUTE_TASK, ev)
    await bot.send(
        "🔇 本群 Codex 推送已静默。\n"
        "已注册的 @ 提醒不受影响，发送「cxcz开启推送」可随时恢复。"
    )


@sv_switch.on_fullmatch("开启推送")
async def unmute_codex_push(bot: Bot, ev: Event) -> None:
    await gs_subscribe.delete_subscribe("session", MUTE_TASK, ev)
    await bot.send("🔊 本群 Codex 推送已恢复，已注册的 @ 提醒继续生效。")


@sv.on_fullmatch(
    ("开启提醒", "开启重置提醒", "开启重置推送"),
    to_ai="""为当前用户开启 Codex 重置提醒订阅。
    当用户想要开启/订阅 codex 重置提醒、codex 重置推送、codex 重置通知时调用。
    群聊中按用户单独订阅，私聊中直接订阅；无需任何参数。
    订阅成功后，检测到官方重置公告、重置信号或重置概率越过预警梯度（默认 50%/80%）时会推送提醒。

    Args:
        text: 无需参数，留空即可
    """,
)
async def open_codex_reminder(bot: Bot, ev: Event) -> None:
    await gs_subscribe.add_subscribe("single", SUBSCRIBE_TASK, ev)
    await bot.send(
        "✅ Codex 重置提醒已开启！\n"
        "检测到官方重置公告、重置信号，或 24 小时重置概率越过预警梯度（默认 50%/80%）时会提醒你。\n"
        "发送「cxcz取消提醒」可随时取消。"
    )


@sv.on_fullmatch(
    ("取消提醒", "取消重置提醒", "取消重置推送"),
    to_ai="""为当前用户取消 Codex 重置提醒订阅。
    当用户想要取消/退订 codex 重置提醒、不想再接收重置推送时调用。
    无需参数，自动取消当前用户的订阅。

    Args:
        text: 无需参数，留空即可
    """,
)
async def close_codex_reminder(bot: Bot, ev: Event) -> None:
    subs = await gs_subscribe.get_subscribe(
        SUBSCRIBE_TASK,
        user_id=ev.user_id,
        bot_id=ev.bot_id,
        user_type=ev.user_type,
    )
    if not subs:
        await bot.send("你还没有开启 Codex 重置提醒。发送「cxcz开启提醒」即可订阅。")
        return
    await gs_subscribe.delete_subscribe("single", SUBSCRIBE_TASK, ev)
    await bot.send("✅ 已取消 Codex 重置提醒。")


@sv.on_fullmatch(
    ("查看记录", "重置记录", "重置历史"),
    to_ai="""查看 Codex 限额重置的历史记录（最近若干条）。
    当用户想查看 codex 重置记录、重置历史、以前重置过几次时调用。
    内容包含每次重置的日期、类型、状态与原文链接。

    Args:
        text: 无需参数，留空即可
    """,
)
async def view_codex_records(bot: Bot, ev: Event) -> None:
    limit = int(CODEX_CONFIG.get_config("timeline_count").data)
    timeline = await fetch_timeline()
    await bot.send(format_timeline(timeline, limit))
