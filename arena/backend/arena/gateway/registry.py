"""Maps a PlayerConfig to the right adapter instance and key."""
from __future__ import annotations

from config import PROVIDERS, VAULT
from .anthropic import AnthropicGateway
from .base import ModelGateway
from .mock import PERSONAS, MockGateway
from .openai_compat import OpenAICompatGateway


class GatewayRegistry:
    def __init__(self) -> None:
        self._mock = MockGateway()
        self._live: dict[str, ModelGateway] = {}

    def gateway_for(self, provider_id: str) -> tuple[ModelGateway, str | None]:
        profile = PROVIDERS.get(provider_id)
        if profile is None or profile.kind == "mock":
            return self._mock, None
        gw = self._live.get(provider_id)
        if gw is None:
            if profile.kind == "anthropic":
                gw = AnthropicGateway(profile)
            else:
                gw = OpenAICompatGateway(profile)
            self._live[provider_id] = gw
        return gw, VAULT.get_key(provider_id)

    def persona_catalog(self) -> dict[str, dict]:
        return {
            pid: {"id": p.id, "label": p.label, "blurb": p.blurb,
                  "depth_range": list(p.depth), "noise": p.noise,
                  "bluff": p.bluff}
            for pid, p in PERSONAS.items()
        }


REGISTRY = GatewayRegistry()
