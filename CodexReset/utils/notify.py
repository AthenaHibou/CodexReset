"""CodexReset 推送：按会话分组发送，群内 @ 订阅用户。"""

from typing import Dict, List, Set, Tuple

from gsuid_core.logger import logger
from gsuid_core.models import Message
from gsuid_core.segment import MessageSegment
from gsuid_core.subscribe import gs_subscribe
from gsuid_core.utils.database.models import Subscribe

SUBSCRIBE_TASK = "[CodexReset] 重置提醒"
MUTE_TASK = "[CodexReset] 会话推送静默"


def _session_key(sub: Subscribe) -> Tuple[str, str, str, str]:
    if sub.user_type == "group":
        return (str(sub.bot_id), str(sub.WS_BOT_ID), "group", str(sub.group_id))
    return (str(sub.bot_id), str(sub.WS_BOT_ID), "direct", str(sub.user_id))


def _mute_key(sub: Subscribe) -> Tuple[str, str]:
    return (str(sub.bot_id), str(sub.group_id))


async def _get_muted_groups() -> Set[Tuple[str, str]]:
    """收集处于「推送静默」状态的群（bot_id, group_id）。"""
    muted_subs = await gs_subscribe.get_subscribe(task_name=MUTE_TASK)
    if not muted_subs:
        return set()
    return {_mute_key(m) for m in muted_subs if m.user_type == "group"}


async def push_reset_notice(body: str) -> int:
    """向所有订阅会话推送提醒，返回发送成功的会话数。

    群聊：同一群只发一条消息，@ 行在最上方（每个订阅用户一行），
    @ 行与正文之间空一行；只要群内有一人订阅即发送；
    若群被管理员「cxcz取消推送」静默，则整群跳过（不影响用户注册）。
    私聊：直接发送正文。
    """
    subs = await gs_subscribe.get_subscribe(task_name=SUBSCRIBE_TASK)
    if not subs:
        return 0

    muted = await _get_muted_groups()
    sessions: Dict[Tuple[str, str, str, str], List[Subscribe]] = {}
    for sub in subs:
        sessions.setdefault(_session_key(sub), []).append(sub)

    sent = 0
    for key, group in sessions.items():
        user_type = key[2]
        if user_type == "group":
            first = group[0]
            if (str(first.bot_id), str(first.group_id)) in muted:
                continue
        try:
            if user_type == "group":
                at_users: List[str] = []
                at_lines: List[Message] = []
                for sub in group:
                    uid = str(sub.user_id) if sub.user_id else ""
                    if uid and uid not in at_users:
                        at_users.append(uid)
                        at_lines.append(MessageSegment.at(uid))
                msg_list = at_lines + [MessageSegment.text("\n" + body)]
                await group[0].send(msg_list, sep="\n")
            else:
                await group[0].send(body)
            sent += 1
        except Exception as e:
            logger.warning(f"[CodexReset] 推送会话 {key} 失败: {e}")
    return sent
