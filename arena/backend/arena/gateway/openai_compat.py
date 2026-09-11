"""OpenAI-compatible Chat Completions adapter.

One adapter covers OpenAI, DeepSeek, xAI (Grok) and Google's
OpenAI-compatibility endpoint (Gemini), since they share the wire protocol.
"""
from __future__ import annotations

import httpx

from config import ProviderProfile
from .base import GatewayError, ModelGateway, ModelResponse, TurnRequest, parse_structured_output, timed


class OpenAICompatGateway(ModelGateway):
    def __init__(self, profile: ProviderProfile, timeout: float = 60.0) -> None:
        self.profile = profile
        self.timeout = timeout

    async def generate(self, req: TurnRequest, key: str | None = None) -> ModelResponse:
        if not key:
            raise GatewayError(f"missing API key for {self.profile.label}")

        url = f"{self.profile.base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        messages = [
            {"role": "system", "content": req.system_prompt},
            {"role": "user", "content": req.user_prompt},
        ]
        body: dict = {
            "model": req.player.model or self.profile.default_model,
            "messages": messages,
            "temperature": req.temperature,
        }
        start = timed()
        last_err: Exception | None = None
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            # First attempt: ask for strict JSON. Retry without response_format
            # for providers/proxies that reject it, then one plain retry.
            for attempt, use_json_mode in enumerate((True, False, False)):
                b = dict(body)
                if use_json_mode:
                    b["response_format"] = {"type": "json_object"}
                try:
                    resp = await client.post(url, headers=headers, json=b)
                    if resp.status_code >= 400:
                        last_err = GatewayError(f"HTTP {resp.status_code}: {resp.text[:300]}")
                        # JSON mode unsupported -> retry immediately without it.
                        if resp.status_code in (400, 404, 422) and use_json_mode:
                            continue
                        if attempt < 2:
                            continue
                        raise last_err
                    data = resp.json()
                    text = data["choices"][0]["message"]["content"] or ""
                    usage = data.get("usage", {})
                    obj = parse_structured_output(text)
                    action = obj.get("action")
                    if isinstance(action, str):
                        action = action.strip()
                    return ModelResponse(
                        reasoning=str(obj.get("reasoning", "")).strip(),
                        action=action,
                        raw=text,
                        tokens_in=usage.get("prompt_tokens", 0),
                        tokens_out=usage.get("completion_tokens", 0),
                        latency_ms=int((timed() - start) * 1000),
                        retries=attempt,
                    )
                except (httpx.HTTPError, KeyError) as exc:
                    last_err = exc
                    continue
        raise GatewayError(f"{self.profile.id} request failed: {last_err}")
