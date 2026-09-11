"""Runtime configuration: provider registry profiles and the API key vault.

Keys resolve with precedence: runtime override (dashboard Settings, in-memory
only) > environment variable. Keys are never serialized to disk or returned
to the browser — only masked availability is exposed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class ProviderProfile:
    id: str
    label: str
    env_var: str
    default_model: str
    models: tuple[str, ...]
    kind: str = "openai_compat"   # or "anthropic" / "mock"
    base_url: str | None = None
    docs: str = ""


PROVIDERS: dict[str, ProviderProfile] = {
    "mock": ProviderProfile(
        id="mock",
        label="Simulated Persona (no key)",
        env_var="",
        default_model="chatgpt-sim",
        models=("chatgpt-sim", "claude-sim", "gemini-sim", "deepseek-sim", "grok-sim"),
        kind="mock",
    ),
    "openai": ProviderProfile(
        id="openai",
        label="OpenAI (ChatGPT)",
        env_var="OPENAI_API_KEY",
        default_model="gpt-4o-mini",
        models=("gpt-4o-mini", "gpt-4o", "o4-mini"),
        base_url="https://api.openai.com/v1",
        docs="platform.openai.com",
    ),
    "anthropic": ProviderProfile(
        id="anthropic",
        label="Anthropic (Claude)",
        env_var="ANTHROPIC_API_KEY",
        default_model="claude-haiku-4-5-20251001",
        models=(
            "claude-haiku-4-5-20251001",
            "claude-sonnet-4-6-20250620",
            "claude-opus-4-6-202509-29",
        ),
        kind="anthropic",
        docs="console.anthropic.com",
    ),
    "gemini": ProviderProfile(
        id="gemini",
        label="Google (Gemini)",
        env_var="GEMINI_API_KEY",
        default_model="gemini-2.0-flash",
        models=("gemini-2.0-flash", "gemini-2.5-pro", "gemini-2.5-flash"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        docs="aistudio.google.com",
    ),
    "deepseek": ProviderProfile(
        id="deepseek",
        label="DeepSeek",
        env_var="DEEPSEEK_API_KEY",
        default_model="deepseek-chat",
        models=("deepseek-chat", "deepseek-reasoner"),
        base_url="https://api.deepseek.com/v1",
        docs="platform.deepseek.com",
    ),
    "xai": ProviderProfile(
        id="xai",
        label="xAI (Grok)",
        env_var="XAI_API_KEY",
        default_model="grok-4-mini",
        models=("grok-4-mini", "grok-4", "grok-3-mini"),
        base_url="https://api.x.ai/v1",
        docs="console.x.ai",
    ),
}


class KeyVault:
    def __init__(self) -> None:
        self._runtime: dict[str, str] = {}

    def set_key(self, provider_id: str, key: str) -> None:
        if provider_id not in PROVIDERS:
            raise KeyError(f"unknown provider {provider_id}")
        key = key.strip()
        if key:
            self._runtime[provider_id] = key
        else:
            self._runtime.pop(provider_id, None)

    def get_key(self, provider_id: str) -> str | None:
        if provider_id in self._runtime:
            return self._runtime[provider_id]
        env_var = PROVIDERS[provider_id].env_var
        return os.environ.get(env_var) or None

    def is_configured(self, provider_id: str) -> bool:
        return bool(self.get_key(provider_id))

    def status(self) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for pid, prof in PROVIDERS.items():
            key = self.get_key(pid) if prof.kind != "mock" else None
            out[pid] = {
                "label": prof.label,
                "configured": prof.kind == "mock" or bool(key),
                "source": ("runtime" if pid in self._runtime else "env" if key else "none"),
                "masked": (f"{key[:6]}…{key[-4:]}" if key and len(key) > 12 else ("✓" if key else "")),
            }
        return out


VAULT = KeyVault()
