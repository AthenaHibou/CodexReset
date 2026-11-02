"""CodexReset 轮询状态持久化（去重名单与概率预警闸位）。"""

import json
from asyncio import to_thread
from typing import List, Optional, TypedDict

from gsuid_core.data_store import get_res_path

STATE_PATH = get_res_path("CodexReset") / "state.json"
MAX_SEEN_IDS = 300


class PollState(TypedDict):
    seen_ids: List[str]
    prob_fired: List[int]
    prob_last_reset: Optional[str]


def _load_state() -> PollState:
    if not STATE_PATH.exists():
        return {"seen_ids": [], "prob_fired": [], "prob_last_reset": None}
    raw = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    seen_raw: List[str] = []
    fired_raw: List[int] = []
    last_reset_raw: Optional[str] = None
    if isinstance(raw, dict):
        if "seen_ids" in raw and isinstance(raw["seen_ids"], list):
            seen_raw = [str(i) for i in raw["seen_ids"]]
        if "prob_fired" in raw and isinstance(raw["prob_fired"], list):
            fired_raw = [int(i) for i in raw["prob_fired"] if isinstance(i, (int, float))]
        if "prob_last_reset" in raw and isinstance(raw["prob_last_reset"], str):
            last_reset_raw = raw["prob_last_reset"]
    return {
        "seen_ids": seen_raw[:MAX_SEEN_IDS],
        "prob_fired": fired_raw,
        "prob_last_reset": last_reset_raw,
    }


def _save_state(state: PollState) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


async def load_state() -> PollState:
    return await to_thread(_load_state)


async def save_state(state: PollState) -> None:
    await to_thread(_save_state, state)
