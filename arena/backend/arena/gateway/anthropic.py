"""Native Anthropic Messages adapter (Claude)."""
from __future__ import annotations

import httpx

from config import ProviderProfile
from .base import GatewayError, ModelGateway, ModelResponse, TurnRequest, parse_structured_output, timed


class AnthropicGateway(ModelGateway):
    URL = "https://api.anthropic.com/v1/messages"
    VERSION = "2023-06-01"

    def __init__(self, profile: ProviderProfile, timeout: float = 60.0) -> None:
        self.profile = profile
        self.timeout = timeout

    async def generate(self, req: TurnRequest, key: str | None = None) -> ModelResponse:
        if not key:
            raise GatewayError("missing API key for Anthropic")
        headers = {
            "x-api-key": key,
            "anthropic-version": self.VERSION,
            "content-type": "application/json",
        }
        body = {
            "model": req.player.model or self.profile.default_model,
            "max_tokens": 1024,
            "temperature": req.temperature,
            "system": req.system_prompt,
            "messages": [{"role": "user", "content": req.user_prompt}],
        }
        start = timed()
        last_err: Exception | None = None
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for attempt in range(3):
                try:
                    resp = await client.post(self.URL, headers=headers, json=body)
                    if resp.status_code >= 400:
                        last_err = GatewayError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                        continue
                    data = resp.json()
                    parts = [b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"]
                    text = "\n".join(parts)
                    usage = data.get("usage", {})
                    obj = parse_structured_output(text)
                    action = obj.get("action")
                    if isinstance(action, str):
                        action = action.strip()
                    return ModelResponse(
                        reasoning=str(obj.get("reasoning", "")).strip(),
                        action=action,
                        raw=text,
                        tokens_in=usage.get("input_tokens", 0),
                        tokens_out=usage.get("output_tokens", 0),
                        latency_ms=int((timed() - start) * 1000),
                        retries=attempt,
                    )
                except (httpx.HTTPError, KeyError) as exc:
                    last_err = exc
                    continue
        raise GatewayError(f"anthropic request failed: {last_err}")
