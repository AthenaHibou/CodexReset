"""CodexReset 轮询任务：检测新重置公告与概率预警并推送。"""

import asyncio
import time
from typing import Dict, List, Optional, Tuple, Union

from gsuid_core.aps import scheduler
from gsuid_core.logger import logger

from ..cxcz_config import CODEX_CONFIG
from ..utils.ai_judge import format_start_desc, judge_event_notice, needs_ai_timing
from ..utils.api import (
    Feed,
    Forecast,
    Timeline,
    TimelineEvent,
    ResetSignal,
    build_event_notice,
    build_prob_notice,
    build_signal_notice,
    fetch_feed,
    fetch_forecast,
    fetch_timeline,
)
from ..utils.notify import push_reset_notice
from ..utils.state import PollState, load_state, save_state

_last_poll_ts: float = 0.0
MAX_PUSH_PER_POLL = 3

Candidate = Tuple[str, str, Union[ResetSignal, TimelineEvent]]


def _collect_candidates(feed: Feed, timeline: Timeline) -> List[Candidate]:
    """收集本轮全部「重置公告」候选：活跃信号 + 时间线重置事件（新在前）。

    返回 (id, kind, obj)，文案延迟到确认是新公告后才构建，
    避免对旧事件反复做 AI 判断。
    """
    candidates: List[Candidate] = []
    signal = feed.signal
    if signal is not None and signal.active:
        candidates.append((signal.tweet_id, "signal", signal))
    for event in timeline.events:
        if event.type == "reset" or event.type == "credits":
            candidates.append((event.id, "event", event))
    return candidates


async def _build_event_notice_ai(event: TimelineEvent, include_origin: bool) -> str:
    """构建事件提醒：AI 翻译总结公告 + 推断生效时机，失败回退原模板。"""
    ai_summary: Optional[str] = None
    ai_start_desc: Optional[str] = None

    want_summary = bool(CODEX_CONFIG.get_config("ai_notice").data)
    want_timing = bool(CODEX_CONFIG.get_config("ai_judge").data) and needs_ai_timing(event)

    if (want_summary or want_timing) and (event.summary or "").strip():
        judgement = await judge_event_notice(event)
        if judgement is not None:
            if want_summary and judgement.summary_cn.strip():
                ai_summary = judgement.summary_cn.strip()
            if want_timing:
                ai_start_desc = format_start_desc(judgement)
    return build_event_notice(
        event,
        include_origin,
        ai_start_desc=ai_start_desc,
        ai_summary=ai_summary,
    )


async def poll_codex_reset() -> None:
    state: PollState = await load_state()
    include_origin = bool(CODEX_CONFIG.get_config("include_origin").data)

    feed, forecast, timeline = await asyncio.gather(
        fetch_feed(),
        fetch_forecast(),
        fetch_timeline(),
    )

    candidates = _collect_candidates(feed, timeline)
    seen = state["seen_ids"]
    seen_set = set(seen)

    fresh: Dict[str, Candidate] = {}
    for cid, kind, obj in candidates:
        if cid not in seen_set and cid not in fresh:
            fresh[cid] = (cid, kind, obj)

    # 无论是否首轮都更新去重名单（候选顺序即新到旧，截断保留最近 N 条）
    state["seen_ids"] = list(dict.fromkeys([cid for cid, _, _ in candidates] + seen))[:300]

    first_run = not seen
    if fresh and not first_run:
        # 候选新→旧，翻转后为旧→新；同一批最多推送最新的 3 条，按时间正序发送
        ordered = list(reversed(list(fresh.values())))
        for _, kind, obj in ordered[-MAX_PUSH_PER_POLL:]:
            if isinstance(obj, ResetSignal):
                text = build_signal_notice(obj, include_origin)
            else:
                text = await _build_event_notice_ai(obj, include_origin)
            count = await push_reset_notice(text)
            logger.info(f"[CodexReset] 重置公告提醒已推送至 {count} 个会话")
            await asyncio.sleep(2)

    # 概率梯度预警：逐档越过时各推一次；概率回落到最低档以下或进入新重置周期后重新武装
    levels = sorted({int(x) for x in CODEX_CONFIG.get_config("prob_levels").data})
    prob = forecast.probabilities.rounded_24h
    last_reset = forecast.last_reset_at or ""

    if not levels:
        pass
    elif first_run:
        state["prob_last_reset"] = last_reset
        state["prob_fired"] = [lv for lv in levels if prob >= lv]
    else:
        if last_reset != state["prob_last_reset"]:
            state["prob_last_reset"] = last_reset
            state["prob_fired"] = []
        elif prob < levels[0]:
            state["prob_fired"] = []
        for lv in levels:
            if prob >= lv and lv not in state["prob_fired"]:
                idx = levels.index(lv)
                count = await push_reset_notice(build_prob_notice(forecast, lv, levels[idx + 1 :]))
                logger.info(f"[CodexReset] {lv}% 档概率预警已推送至 {count} 个会话")
                state["prob_fired"].append(lv)
                break

    await save_state(state)


@scheduler.scheduled_job("interval", minutes=1, id="codexreset_poll")
async def _poll_tick() -> None:
    global _last_poll_ts
    try:
        interval = max(int(CODEX_CONFIG.get_config("poll_interval").data), 1)
        now = time.time()
        if now - _last_poll_ts < interval * 60:
            return
        _last_poll_ts = now
        await poll_codex_reset()
    except Exception:
        logger.exception("[CodexReset] 轮询 codex-reset.com 失败")
