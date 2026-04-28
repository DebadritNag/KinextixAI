"""Reasoning Engine for generating natural language route explanations.

Uses the HF Router API (router.huggingface.co/v1/chat/completions)
with google/gemma-4-31B-it. Falls back to a template when unavailable.

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
"""

import os
from pathlib import Path

import httpx

from app.models.api import ExplainResponse
from app.models.optimization import RouteOption

# ── Load .env ────────────────────────────────────────────────────────

def _load_env() -> None:
    # Try both: relative to this file (backend/app/services/ -> backend/.env)
    # and relative to cwd
    candidates = [
        Path(__file__).resolve().parent.parent.parent / ".env",  # backend/.env
        Path(".env"),
        Path("backend/.env"),
    ]
    for env_path in candidates:
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
            break

_load_env()

# ── Constants ────────────────────────────────────────────────────────

_HF_ROUTER_URL = "https://router.huggingface.co/v1/chat/completions"
_DEFAULT_MODEL  = "google/gemma-4-31B-it"
_MAX_WORDS      = 200
_DEFAULT_TIMEOUT = 45


# ── ReasoningEngine ──────────────────────────────────────────────────

class ReasoningEngine:
    """Generates natural language explanations for route recommendations."""

    def __init__(self, model_id: str = _DEFAULT_MODEL, timeout: int = _DEFAULT_TIMEOUT) -> None:
        self._model_id  = model_id
        self._timeout   = timeout
        self._hf_token: str | None = os.environ.get("HF_API_TOKEN")

    # ── Public ───────────────────────────────────────────────────────

    async def explain(
        self,
        route: RouteOption,
        alternatives: list[RouteOption],
    ) -> ExplainResponse:
        try:
            text = await self._call_hf_api(route, alternatives)
            if not text.strip():
                raise ValueError("empty")
            return ExplainResponse(explanation=_truncate(text), source="model")
        except Exception:
            return ExplainResponse(
                explanation=_truncate(self._build_fallback(route, alternatives)),
                source="fallback",
            )

    # ── HF Router call ───────────────────────────────────────────────

    async def _call_hf_api(
        self,
        route: RouteOption,
        alternatives: list[RouteOption],
    ) -> str:
        if not self._hf_token:
            raise ValueError("HF_API_TOKEN not set")

        headers = {
            "Authorization": f"Bearer {self._hf_token}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._model_id,
            "messages": [{"role": "user", "content": self._build_prompt(route, alternatives)}],
            "max_tokens": 250,
            "temperature": 0.4,
        }

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(_HF_ROUTER_URL, json=payload, headers=headers)
            response.raise_for_status()

        return response.json()["choices"][0]["message"]["content"].strip()

    # ── Prompt ───────────────────────────────────────────────────────

    @staticmethod
    def _build_prompt(route: RouteOption, alternatives: list[RouteOption]) -> str:
        alt_lines = [
            f"- {a.label}: cost ${a.cost_usd:.0f}, ETA {a.eta_hours:.1f}h, "
            f"carbon {a.carbon_kg:.1f}kg CO2, risk {a.risk_score:.0f}/100"
            for a in alternatives
        ]
        alt_block = "\n".join(alt_lines) if alt_lines else "None"

        return (
            "You are a logistics analyst AI. In 3-4 concise sentences, "
            "explain why the following route is recommended over the alternatives. "
            "Focus on cost savings, time efficiency, carbon impact, and risk.\n\n"
            f"RECOMMENDED ROUTE ({route.label}):\n"
            f"  Path: {' → '.join(route.waypoints)}\n"
            f"  Cost: ${route.cost_usd:.0f}\n"
            f"  ETA: {route.eta_hours:.1f} hours\n"
            f"  Carbon: {route.carbon_kg:.1f} kg CO2\n"
            f"  Risk score: {route.risk_score:.0f}/100\n\n"
            f"ALTERNATIVES:\n{alt_block}\n\n"
            "Provide a direct, professional explanation without bullet points."
        )

    # ── Fallback ─────────────────────────────────────────────────────

    @staticmethod
    def _build_fallback(route: RouteOption, alternatives: list[RouteOption]) -> str:
        waypoints_str = " → ".join(route.waypoints)
        cost_diff_str = ""
        if alternatives:
            best_alt = min(alternatives, key=lambda a: a.score)
            diff = best_alt.cost_usd - route.cost_usd
            if diff > 0:
                cost_diff_str = f" (saves ${diff:.0f} vs next option)"
            elif diff < 0:
                cost_diff_str = f" (${abs(diff):.0f} more than cheapest alternative)"
        return (
            f"Route via {waypoints_str} is recommended. "
            f"Cost: ${route.cost_usd:.0f}{cost_diff_str}. "
            f"ETA: {route.eta_hours:.1f}h. "
            f"Carbon: {route.carbon_kg:.1f}kg CO2. "
            f"Risk score: {route.risk_score:.0f}/100."
        )


# ── Utility ──────────────────────────────────────────────────────────

def _truncate(text: str, max_words: int = _MAX_WORDS) -> str:
    words = text.split()
    return text if len(words) <= max_words else " ".join(words[:max_words])
