"""codex-reset.com 公开 API 客户端与中文格式化。

数据源: https://codex-reset.com/
公开接口: /api/forecast · /api/timeline · /api/status-history · /api/feed
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import httpx
from pydantic import BaseModel, Field

API_BASE = "https://codex-reset.com/api"
SITE_URL = "https://codex-reset.com/"

CN_TZ = timezone(timedelta(hours=8))

CONFIDENCE_MAP = {"low": "低", "medium": "中", "high": "高"}
TYPE_MAP = {"reset": "限额重置", "credits": "赠送重置额度"}
KIND_MAP = {"hard": "硬重置", "soft": "软重置"}
STATE_MAP = {"announced": "已公告", "hinted": "官方暗示", "none": "已公告"}
VERIFY_MAP = {
    "confirmed": "已确认生效",
    "rejected": "未观察到生效",
    "expired": "已过期",
    "pending": "待验证",
}
STATUS_MAP = {
    "none": "正常",
    "operational": "正常",
    "degraded_performance": "性能下降",
    "partial_outage": "部分中断",
    "major_outage": "严重中断",
}
TAG_MAP = {
    "milestone": "里程碑",
    "incident": "事故补偿",
    "promo": "宣传",
    "launch": "模型上新",
    "banked": "重置额度银行",
    "unlock": "解锁",
    "compensation": "补偿",
}


# ─────────────────────────────── 数据模型 ───────────────────────────────


class Probabilities(BaseModel):
    raw_24h: float = 0.0
    raw_48h: float = 0.0
    rounded_24h: int = 0
    rounded_48h: int = 0


class TimeWindow(BaseModel):
    start_hour: int = 0
    end_hour: int = 0
    label: str = ""
    timezone: str = "UTC"


class Cadence(BaseModel):
    recent_median_days: Optional[float] = None
    recent_sample: Optional[int] = None
    weighted_mean_days: Optional[float] = None
    accelerating: Optional[bool] = None


class Forecast(BaseModel):
    updated_at: Optional[str] = None
    probabilities: Probabilities = Field(default_factory=Probabilities)
    confidence: Optional[str] = None
    confidence_note: Optional[str] = None
    last_reset_at: Optional[str] = None
    age_days: Optional[float] = None
    time_window: Optional[TimeWindow] = None
    cadence: Optional[Cadence] = None


class OfficialWindow(BaseModel):
    label: str = ""
    start_at: Optional[str] = None
    end_at: Optional[str] = None


class TimelineEvent(BaseModel):
    id: str
    date: Optional[str] = None
    type: Optional[str] = None
    summary: Optional[str] = None
    url: Optional[str] = None
    announced_at: Optional[str] = None
    official_window: Optional[OfficialWindow] = None
    preview: bool = False
    reset_kind: Optional[str] = None
    reason_tags: List[str] = Field(default_factory=list)
    announcement_state: Optional[str] = None
    reset_verification_status: Optional[str] = None
    confidence: Optional[str] = None


class Timeline(BaseModel):
    updated_at: Optional[str] = None
    events: List[TimelineEvent] = Field(default_factory=list)


class ResetSignal(BaseModel):
    tweet_id: str
    summary: Optional[str] = None
    at: Optional[str] = None
    url: Optional[str] = None
    kind: Optional[str] = None
    active: bool = False


class FeedTweet(BaseModel):
    id: str
    url: Optional[str] = None
    text: Optional[str] = None
    at: Optional[str] = None
    kind: Optional[str] = None
    tibo_lane: Optional[str] = None
    explicit_reset_claim: bool = False


class Feed(BaseModel):
    fetched_at: Optional[str] = None
    stale: bool = False
    signal: Optional[ResetSignal] = None
    tweets: List[FeedTweet] = Field(default_factory=list)


class Surface(BaseModel):
    id: str
    label: str = ""
    status: str = ""


class CurrentStatus(BaseModel):
    indicator: Optional[str] = None
    description: Optional[str] = None
    surfaces: List[Surface] = Field(default_factory=list)
    incident_count: int = 0


class Incident(BaseModel):
    name: Optional[str] = None
    impact: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[str] = None
    resolved_at: Optional[str] = None


class StatusHistory(BaseModel):
    checked_at: Optional[str] = None
    stale: bool = False
    current: Optional[CurrentStatus] = None
    incidents: List[Incident] = Field(default_factory=list)


# ─────────────────────────────── 请求封装 ───────────────────────────────


async def _fetch(path: str, retries: int = 2) -> bytes:
    # 禁用环境代理：codex-reset.com 可直连，走系统代理易因节点抖动导致轮询失败
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(
                timeout=30,
                trust_env=False,
                headers={"User-Agent": "GsCore-CodexReset/0.1"},
            ) as client:
                resp = await client.get(f"{API_BASE}/{path}")
                resp.raise_for_status()
                return resp.content
        except httpx.TransportError:
            if attempt >= retries:
                raise
            await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError("unreachable")


async def fetch_forecast() -> Forecast:
    return Forecast.model_validate_json(await _fetch("forecast"))


async def fetch_timeline() -> Timeline:
    return Timeline.model_validate_json(await _fetch("timeline"))


async def fetch_status_history() -> StatusHistory:
    return StatusHistory.model_validate_json(await _fetch("status-history"))


async def fetch_feed() -> Feed:
    return Feed.model_validate_json(await _fetch("feed"))


# ─────────────────────────────── 时间工具 ───────────────────────────────


def _parse_utc(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _cn(dt: datetime) -> str:
    return dt.astimezone(CN_TZ).strftime("%Y-%m-%d %H:%M")


def _cn_from_utc_str(value: Optional[str]) -> Optional[str]:
    dt = _parse_utc(value)
    if dt is None:
        return None
    return _cn(dt)


def _countdown_cn(target: datetime) -> str:
    minutes = int((target - datetime.now(timezone.utc)).total_seconds() // 60)
    if minutes < 0:
        return "已到预计时间"
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"约 {hours} 小时 {minutes} 分钟后"
    return f"约 {minutes} 分钟后"


def _trim(text: str, max_len: int) -> str:
    text = text.strip().replace("\n", " ")
    if len(text) > max_len:
        return text[:max_len] + "…"
    return text


def _zh(mapping: dict, key: Optional[str]) -> Optional[str]:
    """枚举值中文化；未知枚举原样返回。"""
    if key is None:
        return None
    if key in mapping:
        return mapping[key]
    return key


def _window_cn(forecast: Forecast) -> str:
    tw = forecast.time_window
    if tw is None:
        return "暂无统计"
    start = (tw.start_hour + 8) % 24
    end = (tw.end_hour + 8) % 24
    return f"北京时间 {start:02d}:00 - {end:02d}:00（UTC {tw.label}）"


# ─────────────────────────────── 格式化 ───────────────────────────────


def format_forecast(f: Forecast) -> str:
    p = f.probabilities
    lines = [
        "📊 Codex 重置预测",
        "",
        f"未来 24 小时内重置概率：约 {p.rounded_24h}%",
        f"未来 48 小时内重置概率：约 {p.rounded_48h}%",
        f"预测置信度：{_zh(CONFIDENCE_MAP, f.confidence) or '未知'}",
    ]
    last = _cn_from_utc_str(f.last_reset_at)
    if last is not None:
        age = "" if f.age_days is None else f"（约 {f.age_days:.1f} 天前）"
        lines.append(f"上次重置：{last}（北京时间）{age}")
    lines.append(f"常见重置时段：{_window_cn(f)}")
    cad = f.cadence
    if cad is not None and cad.recent_median_days is not None:
        speed = "（正在加快）" if cad.accelerating else ""
        lines.append(f"近期节奏：约 {cad.recent_median_days:.1f} 天一次{speed}")
    lines.append("")
    lines.append(f"数据来源：{SITE_URL}")
    return "\n".join(lines)


def format_timeline(t: Timeline, limit: int = 10) -> str:
    events = [e for e in t.events if e.type == "reset" or e.type == "credits"]
    events = events[: max(limit, 1)]
    if not events:
        return f"📜 Codex 重置记录\n\n暂无重置记录。\n\n数据来源：{SITE_URL}"
    lines = [f"📜 Codex 重置记录（最近 {len(events)} 条）", ""]
    for idx, e in enumerate(events, start=1):
        title = _zh(TYPE_MAP, e.type) or "重置动态"
        if e.reset_kind is not None:
            title += f"（{_zh(KIND_MAP, e.reset_kind) or e.reset_kind}）"
        state = "官方预告" if e.preview else (_zh(STATE_MAP, e.announcement_state) or "已公告")
        head = f"{idx}. [{e.date or '未知日期'}] {title} · {state}"
        conf = _zh(CONFIDENCE_MAP, e.confidence)
        if conf:
            head += f" · 置信度{conf}"
        if e.reason_tags:
            tags = "、".join(_zh(TAG_MAP, tag) or tag for tag in e.reason_tags)
            head += f" · 标签：{tags}"
        verify = _zh(VERIFY_MAP, e.reset_verification_status)
        if verify:
            head += f" · {verify}"
        lines.append(head)
        if e.summary:
            lines.append(f"   原文：{_trim(e.summary, 100)}")
        if e.url:
            lines.append(f"   链接：{e.url}")
        lines.append("")
    lines.append(f"数据来源：{SITE_URL}")
    return "\n".join(lines)


def format_status(s: StatusHistory) -> str:
    lines = ["🩺 Codex 服务状态", ""]
    cur = s.current
    if cur is not None:
        lines.append(f"总体：{cur.description or '未知'}（{_zh(STATUS_MAP, cur.indicator) or '未知'}）")
        for surface in cur.surfaces:
            lines.append(f"· {surface.label}：{_zh(STATUS_MAP, surface.status) or surface.status}")
        lines.append("")
    recent = s.incidents[:3]
    if recent:
        lines.append(f"近期事故（共收录 {len(s.incidents)} 起）：")
        for inc in recent:
            started = _cn_from_utc_str(inc.started_at) or "未知时间"
            if inc.status == "resolved":
                state = "已恢复"
            else:
                state = "进行中"
            lines.append(f"· [{started}（北京时间）] {inc.name or '未知事故'}（{state}）")
    lines.append("")
    lines.append(f"数据来源：{SITE_URL}")
    return "\n".join(lines)


def format_feed(f: Feed, limit: int = 5) -> str:
    lines = ["📡 Codex 重置动态（@thsottiaux X 监控）", ""]
    sig = f.signal
    if sig is not None:
        state = "活跃" if sig.active else "无活跃信号"
        lines.append(f"当前重置信号：{state}")
        if sig.summary:
            lines.append(f"· 原文：{_trim(sig.summary, 120)}")
        sig_at = _cn_from_utc_str(sig.at)
        if sig_at:
            lines.append(f"· 信号时间：{sig_at}（北京时间）")
        if sig.url:
            lines.append(f"· 链接：{sig.url}")
        lines.append("")
    tweets = f.tweets[: max(limit, 1)]
    if tweets:
        lines.append(f"最新推文（{len(tweets)} 条）：")
        for tw in tweets:
            at = _cn_from_utc_str(tw.at) or "未知时间"
            lines.append(f"· [{at}] {_trim(tw.text or '', 80)}")
            if tw.url:
                lines.append(f"  {tw.url}")
    lines.append("")
    lines.append(f"数据来源：{SITE_URL}")
    return "\n".join(lines)


# ─────────────────────────── 推送提醒文案构建 ───────────────────────────


def build_signal_notice(signal: ResetSignal, include_origin: bool = True) -> str:
    lines = ["📢 Codex 重置提醒", ""]
    if signal.kind == "signal":
        lines.append("类型：重置暗示（官方透露将重置，具体时间未定）")
        start_desc = "具体时间以官方后续公告为准"
    else:
        lines.append("类型：重置信号（官方预告/候选）")
        start_desc = "通常在公告后 1 小时内生效"
    sig_at = _cn_from_utc_str(signal.at)
    if sig_at:
        lines.append(f"公告时间：{sig_at}（北京时间）")
    lines.append(f"预计开始：{start_desc}")
    lines.append("状态：待确认")
    if include_origin and signal.summary:
        lines.append("")
        lines.append(f"原文：{_trim(signal.summary, 160)}")
    if signal.url:
        lines.append(f"来源：{signal.url}")
    return "\n".join(lines)


def build_event_notice(
    event: TimelineEvent,
    include_origin: bool = True,
    ai_start_desc: Optional[str] = None,
    ai_summary: Optional[str] = None,
) -> str:
    title = _zh(TYPE_MAP, event.type) or "重置动态"
    if event.reset_kind is not None:
        title += f"（{_zh(KIND_MAP, event.reset_kind) or event.reset_kind}）"
    if event.preview:
        title += " · 官方预告"
    verify = _zh(VERIFY_MAP, event.reset_verification_status)

    lines = ["📢 Codex 重置提醒", "", f"类型：{title}"]
    announced = _cn_from_utc_str(event.announced_at)
    if announced:
        lines.append(f"公告时间：{announced}（北京时间）")

    ow = event.official_window
    end_dt = _parse_utc(ow.end_at) if ow is not None else None
    start_desc: Optional[str]
    if event.preview:
        if ow is not None and ow.label:
            if end_dt is not None:
                start_desc = (
                    f"官方预计「{ow.label}」，{_countdown_cn(end_dt)}"
                    f"（预计 {_cn(end_dt)} 前）"
                )
            else:
                start_desc = f"官方预计「{ow.label}」"
        else:
            start_desc = "官方未给出具体时间，通常在公告后数小时内生效"
    elif verify == "已确认生效":
        start_desc = "已生效"
    elif verify == "未观察到生效":
        start_desc = "监测尚未观察到实际重置，请以账户限额实际变化为准"
    else:
        # 兜底分支：可传入 AI 判断结果（ai_judge），否则使用固定文案
        start_desc = ai_start_desc or "已进入生效流程，请留意账户限额变化"
    lines.append(f"预计开始：{start_desc}")

    state = "预告中" if event.preview else "已公告"
    if verify:
        state += f"（{verify}）"
    lines.append(f"状态：{state}")

    if event.reason_tags:
        tags = "、".join(_zh(TAG_MAP, tag) or tag for tag in event.reason_tags)
        lines.append(f"标签：{tags}")
    # 内容区：AI 中文总结（ai_notice）在前，英文原文（include_origin）在后
    extra: List[str] = []
    if ai_summary:
        extra.append(f"内容：{_trim(ai_summary, 200)}")
    if include_origin and event.summary:
        extra.append(f"原文：{_trim(event.summary, 160)}")
    if extra:
        lines.append("")
        lines.extend(extra)
    if event.url:
        lines.append(f"来源：{event.url}")
    return "\n".join(lines)


def build_prob_notice(f: Forecast, level: int, pending_levels: Optional[List[int]] = None) -> str:
    p = f.probabilities
    if pending_levels:
        tail = f"概率达到 {pending_levels[0]}% 时会再次提醒"
    else:
        tail = "这是最高档预警：重置随时可能发生，请保持关注官方公告"
    lines = [
        f"📈 Codex 重置概率预警（{level}% 档）",
        "",
        f"未来 24 小时内重置概率约 {p.rounded_24h}%，已越过 {level}% 预警线",
        f"未来 48 小时内重置概率：约 {p.rounded_48h}%",
        f"预测置信度：{_zh(CONFIDENCE_MAP, f.confidence) or '未知'}",
    ]
    last = _cn_from_utc_str(f.last_reset_at)
    if last is not None:
        age = "" if f.age_days is None else f"（约 {f.age_days:.1f} 天前）"
        lines.append(f"上次重置：{last}（北京时间）{age}")
    cad = f.cadence
    if cad is not None and cad.recent_median_days is not None:
        speed = "（正在加快）" if cad.accelerating else ""
        lines.append(f"近期中位间隔：约 {cad.recent_median_days:.1f} 天{speed}")
    lines.append(f"常见重置时段：{_window_cn(f)}")
    lines.append("")
    lines.append(tail)
    lines.append("")
    lines.append(f"数据来源：{SITE_URL}")
    return "\n".join(lines)
