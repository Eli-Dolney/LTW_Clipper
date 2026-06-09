"""Minimal Ollama HTTP client - stdlib only, 100% local.

Why not a third-party SDK? Ollama exposes a stable JSON HTTP API on
``http://localhost:11434`` and we only need three endpoints (health, list,
generate). Keeping it stdlib-only means zero extra install weight and zero
cloud fallback paths.

This client is strictly optional. If Ollama isn't running, ``is_available()``
returns False and callers should fall back to the heuristic/template path.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any
from urllib import error, request

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class OllamaConfig:
    host: str = "http://localhost:11434"
    model: str = "llama3.1:8b"
    request_timeout: int = 120


class OllamaClient:
    """Thin wrapper over Ollama's HTTP API.

    Exposes:
    - ``is_available()`` - health + model presence check
    - ``generate(prompt, schema=None)`` - single-shot completion, optional JSON mode
    """

    def __init__(self, config: OllamaConfig | None = None) -> None:
        self.config = config or OllamaConfig()

    # ---- Health ------------------------------------------------------------

    def is_available(self) -> bool:
        """True if Ollama is running and the configured model is pulled."""
        try:
            tags = self._get("/api/tags")
        except Exception as exc:
            log.debug("Ollama not reachable at %s: %s", self.config.host, exc)
            return False

        models = [m.get("name", "") for m in tags.get("models", [])]
        if not models:
            return False
        # Accept either exact match or base-name match (e.g. "llama3.1:8b" ~ "llama3.1").
        target = self.config.model
        return any(name == target or name.split(":")[0] == target.split(":")[0] for name in models)

    # ---- Generation --------------------------------------------------------

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        json_mode: bool = False,
        temperature: float = 0.4,
    ) -> str:
        """Generate a single response. Returns raw string."""
        payload: dict[str, Any] = {
            "model": self.config.model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system
        if json_mode:
            payload["format"] = "json"

        result = self._post("/api/generate", payload)
        return result.get("response", "")

    def generate_json(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> Any:
        """Generate and parse JSON. Raises ``ValueError`` on parse failure."""
        raw = self.generate(prompt, system=system, json_mode=True, temperature=temperature)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Ollama returned invalid JSON: {raw[:200]}...") from exc

    # ---- HTTP helpers ------------------------------------------------------

    def _get(self, path: str) -> dict:
        url = self.config.host.rstrip("/") + path
        req = request.Request(url, method="GET")
        with request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))

    def _post(self, path: str, payload: dict) -> dict:
        url = self.config.host.rstrip("/") + path
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with request.urlopen(req, timeout=self.config.request_timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:  # pragma: no cover - network edge cases
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama HTTP {exc.code}: {detail}") from exc
