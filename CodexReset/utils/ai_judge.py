"""CodexReset AI 解读：调用 GsCore AI 翻译总结公告并推断预计生效时机。

一次结构化调用同时产出中文总结（summary_cn）与生效时机判断（timing）。
可选增强：AI 服务未启用 / 未配置 / 调用失败时一律返回 None，
调用方回退到 build_event_notice 的固定文案，不构成硬依赖。
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field

from gsuid_core.logger import logger

from .api import CN_TZ, TimelineEvent, _cn_from_utc_str

AI_JUDGE_TIMEOUT = 90
MAX_SUMMARY_LEN = 300

SYSTEM_PROMPT = (
    "你是 OpenAI Codex 重置公告助手。Codex 负责人 Tibo (@thsottiaux) 会不定期在 X 上"
    "公告为全体付费用户重置使用限额（usage limits reset）。请完成两项任务：\n"
    "任务一 summary_cn：把公告原文翻译并总结为简体中文，1~3 句；"
    "保留重置对象、生效时机等关键信息，不添加原文没有的内容；"
    "原文提到的具体时间一律换算为北京时间表述（输入会提供公告时间与当前时间）；"
    "\"Day 21\" 这类周期计数保留原样。\n"
    "任务二：结合当前时间与公告时间，根据公告原文判断本次重置的生效时机：\n"
    '- immediate：公告即生效或几秒几分钟内生效，包括公告说当天就执行重置'
    '（如 "today is a reset"、"have reset"、"It is done"、"Enjoy a reset"、"today/now"）。\n'
    '- window：公告预告了明确的未来生效窗口且能估算分钟数（如 "within an hour"、'
    '"next 30 minutes"、"later today"、"tomorrow"、"end of Monday"）。\n'
    "- unclear：原文无法判断生效时机（如纯暗示、含糊预告、或内容与重置时机无关）。\n"
    "时机规则：\n"
    '1. 公告中的 today / now 表示当天立即执行重置 → 必须判 immediate，不得判 window。\n'
    "2. delay_minutes 仅当 timing=window 时填写：窗口上限分钟数（\"within an hour\"→60，"
    "\"next 30 minutes\"→30，\"tomorrow\"→按公告时间推算到次日同一时刻，"
    "\"end of Monday\"→按公告时间推算到周一 23:59（公告者当地时间））。"
    "若窗口无法量化为分钟数，应改判 immediate（视为即期生效）或 unclear，"
    "绝不允许输出 timing=window 而 delay_minutes 为空。\n"
    "3. evidence 填原文中最能支撑判断的短语，不超过 30 个字符。\n"
    "4. 无法判断时 timing=unclear，delay_minutes 留空。\n"
    "只输出结构化结果，不要任何解释。"
)


class ResetJudgement(BaseModel):
    """公告 AI 解读结果：中文翻译总结 + 生效时机判断（结构化输出）。"""

    summary_cn: str = Field(default="", description="公告原文的中文翻译与总结，1~3 句")
    timing: Literal["immediate", "window", "unclear"] = "unclear"
    delay_minutes: Optional[int] = Field(
        default=None,
        description="timing=window 时：自公告时间起预计多少分钟内生效（窗口上限）",
    )
    evidence: str = ""


def needs_ai_timing(event: TimelineEvent) -> bool:
    """是否命中 build_event_notice 的兜底分支（非预告、未确认/排除、有原文）。"""
    if event.preview:
        return False
    if event.reset_verification_status in ("confirmed", "rejected"):
        return False
    return bool((event.summary or "").strip())


def format_start_desc(judgement: ResetJudgement) -> Optional[str]:
    """把判断结果转成「预计开始」描述；unclear 返回 None（回退固定文案）。"""
    if judgement.timing == "immediate":
        return "根据公告原文判断：重置已/即将立即生效，请留意账户限额变化"
    if judgement.timing == "window" and judgement.delay_minutes and judgement.delay_minutes > 0:
        hours, minutes = divmod(judgement.delay_minutes, 60)
        span = f"约 {hours} 小时 {minutes} 分钟" if hours else f"约 {minutes} 分钟"
        target = datetime.now(timezone.utc) + timedelta(minutes=judgement.delay_minutes)
        target_cn = target.astimezone(CN_TZ).strftime("%m-%d %H:%M")
        return f"根据公告原文判断：预计{span}内生效（约 {target_cn} 前后），请留意账户限额变化"
    return None


def _ai_ready() -> bool:
    """检查 GsCore AI 服务总开关与高/低级任务模型配置名是否可用。"""
    try:
        from gsuid_core.ai_core.configs.ai_config import ai_config

        if not bool(ai_config.get_config("enable").data):
            return False
        low = str(ai_config.get_config("low_level_provider_config_name").data or "").strip()
        high = str(ai_config.get_config("high_level_provider_config_name").data or "").strip()
        return bool(low or high)
    except Exception as e:
        logger.warning(f"[CodexReset] 读取 AI 配置失败，跳过 AI 解读: {e}")
        return False


_agent = None


def _get_agent():
    """懒创建判断 Agent（纯文本结构化判断，不装配任何工具、不保留历史）。"""
    global _agent
    if _agent is None:
        from gsuid_core.ai_core.configs.ai_config import ai_config
        from gsuid_core.ai_core.gs_agent import create_agent

        low = str(ai_config.get_config("low_level_provider_config_name").data or "").strip()
        _agent = create_agent(
            system_prompt=SYSTEM_PROMPT,
            task_level="low" if low else "high",
            max_tokens=1200,
            max_history=0,
            dynamic_tools=False,
            create_by="CodexReset",
        )
    return _agent


async def judge_event_notice(event: TimelineEvent) -> Optional[ResetJudgement]:
    """用 GsCore AI 翻译总结公告并判断生效时机；AI 不可用或失败时返回 None。"""
    if not _ai_ready():
        return None
    summary = (event.summary or "").strip()
    if not summary:
        return None

    now_cn = datetime.now(CN_TZ).strftime("%Y-%m-%d %H:%M")
    announced_cn = _cn_from_utc_str(event.announced_at) or "未知"
    prompt = (
        f"当前时间（北京时间）：{now_cn}\n"
        f"公告时间（北京时间）：{announced_cn}\n"
        f"公告原文：{summary[:MAX_SUMMARY_LEN]}\n\n"
        "请完成中文翻译总结与生效时机判断两项任务，只输出结构化结果。"
    )
    try:
        agent = _get_agent()
        judgement = await asyncio.wait_for(
            agent.run(
                user_message=prompt,
                output_type=ResetJudgement,
                return_mode="return",
            ),
            timeout=AI_JUDGE_TIMEOUT,
        )
    except Exception as e:
        logger.warning(f"[CodexReset] AI 解读公告失败，回退固定文案: {e}")
        return None

    # 代码级兜底：window 却没给有效分钟数 → 降级 unclear（回退固定文案）
    if judgement.timing == "window" and not (judgement.delay_minutes and judgement.delay_minutes > 0):
        logger.warning(
            f"[CodexReset] AI 判定 window 但无有效 delay_minutes，降级为 unclear: {judgement.evidence!r}"
        )
        judgement.timing = "unclear"

    logger.info(
        f"[CodexReset] AI 解读公告: timing={judgement.timing} "
        f"delay_minutes={judgement.delay_minutes} 依据={judgement.evidence!r} "
        f"总结={judgement.summary_cn[:50]!r}"
    )
    return judgement
