"""Llama API client utilities."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from .config import OrganizerPaths

DEFAULT_LLAMA_BASE_URL = "https://api.llama-api.com"
DEFAULT_MODEL = "llama3-8b-instruct"


class LlamaAPIError(RuntimeError):
    """Raised when the Llama API SDK fails or returns an unexpected payload."""


@dataclass
class LlamaCredentials:
    """Access credentials for the Llama API."""

    api_key: str
    base_url: str = DEFAULT_LLAMA_BASE_URL


def _default_sdk_factory(api_key: str, base_url: str) -> Any:
    try:
        from llama_api_client import LlamaAPIClient
    except ImportError as exc:  # pragma: no cover - surfaced when dependency missing
        raise LlamaAPIError(
            "The 'llama-api-client' package is required. Install with `pip install llama-api-client`."
        ) from exc

    if base_url.rstrip("/") != DEFAULT_LLAMA_BASE_URL.rstrip("/"):
        raise LlamaAPIError("Custom Llama API endpoints are not supported by the SDK")

    client = LlamaAPIClient()
    if hasattr(client, "set_api_key") and callable(client.set_api_key):
        client.set_api_key(api_key)
    elif hasattr(client, "api_key"):
        setattr(client, "api_key", api_key)
    else:  # pragma: no cover - fails fast if SDK contract changes
        raise LlamaAPIError("Unable to configure API key on LlamaAPIClient")
    return client


class LlamaClient:
    """Wrapper around the official Llama API Python SDK."""

    def __init__(
        self,
        paths: OrganizerPaths,
        *,
        base_url: str = DEFAULT_LLAMA_BASE_URL,
        sdk_factory: Callable[[str, str], Any] | None = None,
        allow_env_fallback: bool = True,
    ) -> None:
        self._paths = paths
        self._base_url = base_url.rstrip("/")
        self._sdk_factory = sdk_factory or _default_sdk_factory
        self._cached_key: str | None = None
        self._sdk_client: Any | None = None
        self._allow_env_fallback = allow_env_fallback

    # ------------------------------------------------------------------
    # Credential helpers
    # ------------------------------------------------------------------
    def set_api_key(self, api_key: str, *, persist: bool = True) -> None:
        """Store ``api_key`` for future requests."""

        normalized = api_key.strip()
        if not normalized:
            raise ValueError("API key must be non-empty")

        if persist:
            target = self._paths.llama_api_key_file
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = target.with_suffix(target.suffix + ".tmp")
            with tmp_path.open("w", encoding="utf-8") as handle:
                handle.write(normalized)
                handle.flush()
            tmp_path.replace(target)

        self._cached_key = normalized
        self._sdk_client = None

    def clear_cached_key(self) -> None:
        """Forget cached credentials and SDK instances."""

        self._cached_key = None
        self._sdk_client = None

    def load_credentials(self) -> LlamaCredentials:
        """Return credentials pulled from env vars or persisted state."""

        api_key = self._resolve_api_key()
        return LlamaCredentials(api_key=api_key, base_url=self._base_url)

    def _resolve_api_key(self) -> str:
        if self._cached_key:
            return self._cached_key

        disk_path = self._paths.llama_api_key_file
        if disk_path.exists():
            with disk_path.open("r", encoding="utf-8") as handle:
                content = handle.read().strip()
            if content:
                self._cached_key = content
                return self._cached_key

        if self._allow_env_fallback:
            env_key = os.getenv("LLAMA_API_KEY")
            if env_key:
                self._cached_key = env_key.strip()
                return self._cached_key

        raise LlamaAPIError(
            "No Llama API key configured. Set LLAMA_API_KEY or call set_api_key()."
        )

    def _ensure_sdk_client(self) -> Any:
        if self._sdk_client is None:
            credentials = self.load_credentials()
            self._sdk_client = self._sdk_factory(credentials.api_key, credentials.base_url)
        return self._sdk_client

    # ------------------------------------------------------------------
    # API calls
    # ------------------------------------------------------------------
    def complete(
        self,
        prompt: str,
        *,
        model: str = DEFAULT_MODEL,
        temperature: float = 0.2,
        max_tokens: int = 512,
        extra_params: Mapping[str, Any] | None = None,
    ) -> str:
        """Generate a completion using ``prompt`` via the Llama API."""

        if not prompt.strip():
            raise ValueError("prompt must be non-empty")
        if max_tokens <= 0:
            raise ValueError("max_tokens must be positive")

        sdk = self._ensure_sdk_client()
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": float(temperature),
            "max_tokens": int(max_tokens),
        }
        if extra_params:
            payload.update(extra_params)

        try:
            response = sdk.run(payload)
        except Exception as exc:  # pragma: no cover - passthrough for real SDK errors
            raise LlamaAPIError(f"Llama API request failed: {exc}") from exc

        choices = response.get("choices") if isinstance(response, Mapping) else None
        if not choices:
            raise LlamaAPIError("Llama API response missing choices")

        message = choices[0].get("message", {})
        text = message.get("content")
        if not isinstance(text, str):
            raise LlamaAPIError("Llama API response missing message content")

        return text


__all__ = ["DEFAULT_MODEL", "LlamaAPIError", "LlamaClient", "LlamaCredentials"]
