"""Unified gateway interface shared by live LLM adapters and mock personas."""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from ..schemas import PlayerConfig


class GatewayError(RuntimeError):
    pass


@dataclass
class ModelResponse:
    """Every player, live or simulated, returns exactly this shape."""

    reasoning: str
    action: Any
    raw: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: int = 0
    retries: int = 0
    error: Optional[str] = None
    fallback: bool = False


@dataclass
class TurnRequest:
    player: PlayerConfig
    system_prompt: str
    user_prompt: str
    action_hint: str            # human-readable description of the legal action
    action_spec: dict[str, Any] = field(default_factory=dict)
    view: dict[str, Any] = field(default_factory=dict)  # structured player perception
    seed: int = 0               # for deterministic mocks
    temperature: float = 0.8


class ModelGateway:
    """Interface every adapter implements."""

    async def generate(self, req: TurnRequest, key: Optional[str] = None) -> ModelResponse:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Structured-output helpers
# ---------------------------------------------------------------------------

_JSON_FENCE = re.compile(r"\{.*\}", re.DOTALL)


def parse_structured_output(text: str) -> dict[str, Any]:
    """Extract the mandated {"reasoning": ..., "action": ...} object."""
    if not text:
        raise GatewayError("empty response")
    candidates: list[str] = []
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    candidates.extend(fenced)
    candidates.append(text)
    for cand in candidates:
        try:
            obj = json.loads(cand)
            if isinstance(obj, dict) and "action" in obj:
                return obj
        except Exception:
            pass
        m = _JSON_FENCE.search(cand)
        if m:
            try:
                obj = json.loads(m.group(0))
                if isinstance(obj, dict) and "action" in obj:
                    return obj
            except Exception:
                # Last resort: repair common trailing-comma issues.
                cleaned = re.sub(r",\s*([}\]])", r"\1", m.group(0))
                try:
                    obj = json.loads(cleaned)
                    if isinstance(obj, dict) and "action" in obj:
                        return obj
                except Exception:
                    continue
    raise GatewayError("could not parse structured JSON action from response")


def timed() -> float:
    return time.perf_counter()
