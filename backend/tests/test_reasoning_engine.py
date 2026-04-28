"""Unit tests for the ReasoningEngine service.

Validates HF API integration, template fallback, 200-word truncation,
source field correctness, and prompt construction.

Requirements: 13.1, 13.2, 13.3, 13.4, 13.5
"""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.models.api import ExplainResponse
from app.models.optimization import RouteOption
from app.services.reasoning_engine import ReasoningEngine, _truncate


# ── Fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def engine() -> ReasoningEngine:
    """Return a ReasoningEngine with default settings."""
    return ReasoningEngine()


@pytest.fixture
def recommended_route() -> RouteOption:
    """A sample recommended route."""
    return RouteOption(
        route_id="route-1",
        waypoints=["shanghai_port", "singapore_port", "rotterdam_port"],
        label="cheapest",
        cost_usd=3000.0,
        eta_hours=264.0,
        carbon_kg=770.0,
        risk_score=25.0,
        score=0.3500,
        is_recommended=True,
    )


@pytest.fixture
def alternative_routes() -> list[RouteOption]:
    """Sample alternative routes."""
    return [
        RouteOption(
            route_id="route-2",
            waypoints=["shanghai_port", "la_port", "ny_dc"],
            label="fastest",
            cost_usd=4700.0,
            eta_hours=291.0,
            carbon_kg=1030.0,
            risk_score=35.0,
            score=0.5200,
            is_recommended=False,
        ),
        RouteOption(
            route_id="route-3",
            waypoints=["shanghai_port", "busan_port", "la_port"],
            label="safest",
            cost_usd=3800.0,
            eta_hours=300.0,
            carbon_kg=950.0,
            risk_score=32.0,
            score=0.4800,
            is_recommended=False,
        ),
    ]


# ── Initialization tests ────────────────────────────────────────────


class TestInit:
    def test_default_model_id(self) -> None:
        engine = ReasoningEngine()
        assert engine._model_id == "google/gemma-4-31B-it"

    def test_default_timeout(self) -> None:
        engine = ReasoningEngine()
        assert engine._timeout == 20

    def test_custom_model_id(self) -> None:
        engine = ReasoningEngine(model_id="custom/model")
        assert engine._model_id == "custom/model"

    def test_custom_timeout(self) -> None:
        engine = ReasoningEngine(timeout=30)
        assert engine._timeout == 30

    def test_model_id_stored(self) -> None:
        engine = ReasoningEngine(model_id="google/gemma-4-31B-it")
        assert engine._model_id == "google/gemma-4-31B-it"


# ── HF API success tests (Req 13.1) ─────────────────────────────────


class TestHFAPISuccess:
    @pytest.mark.asyncio
    async def test_returns_model_source_on_success(
        self,
        engine: ReasoningEngine,
        recommended_route: RouteOption,
        alternative_routes: list[RouteOption],
    ) -> None:
        """When HF API succeeds, source should be 'model' (Req 13.1)."""
        mock_response = httpx.Response(
            200,
            json={"choices":[{"message":{"content":"This route is optimal because it balances cost and time."}}]},
            request=httpx.Request("POST", "https://router.huggingface.co/v1/chat/completions"),
        )
        with patch("app.services.reasoning_engine.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await engine.explain(recommended_route, alternative_routes)

        assert isinstance(result, ExplainResponse)
        assert result.source == "model"

    @pytest.mark.asyncio
    async def test_returns_generated_text(
        self,
        engine: ReasoningEngine,
        recommended_route: RouteOption,
        alternative_routes: list[RouteOption],
    ) -> None:
        """The explanation should contain the model's generated text."""
        expected_text = "The recommended route offers the best balance of cost and delivery time."
        mock_response = httpx.Response(
            200,
            json={"choices": [{"message": {"content": expected_text}}]},
            request=httpx.Request("POST", "https://router.huggingface.co/v1/chat/completions"),
        )
        with patch("app.services.reasoning_engine.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await engine.explain(recommended_route, alternative_routes)

        assert result.explanation == expected_text


# ── Fallback tests (Req 13.4) ───────────────────────────────────────


class TestFallback:
    @pytest.mark.asyncio
    async def test_fallback_on_timeout(
        self,
        engine: ReasoningEngine,
        recommended_route: RouteOption,
        alternative_routes: list[RouteOption],
    ) -> None:
        """When HF API times out, source should be 'fallback' (Req 13.3, 13.4)."""
        with patch("app.services.reasoning_engine.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await engine.explain(recommended_route, alternative_routes)

        assert result.source == "fallback"

    @pytest.mark.asyncio
    async def test_fallback_on_http_error(
        self,
        engine: ReasoningEngine,
        recommended_route: RouteOption,
        alternative_routes: list[RouteOption],
    ) -> None:
        """When HF API returns an HTTP error, source should be 'fallback'."""
        mock_response = httpx.Response(
            503,
            json={"error": "Model is loading"},
            request=httpx.Request("POST", "https://router.huggingface.co/v1/chat/completions"),
        )
        with patch("app.services.reasoning_engine.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await engine.explain(recommended_route, alternative_routes)

        assert result.source == "fallback"

    @pytest.mark.asyncio
    async def test_fallback_on_connection_error(
        self,
        engine: ReasoningEngine,
        recommended_route: RouteOption,
        alternative_routes: list[RouteOption],
    ) -> None:
        """When HF API is unreachable, source should be 'fallback'."""
        with patch("app.services.reasoning_engine.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.ConnectError("unreachable"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await engine.explain(recommended_route, alternative_routes)

        assert result.source == "fallback"

    @pytest.mark.asyncio
    async def test_fallback_contains_route_metrics(
        self,
        engine: ReasoningEngine,
        recommended_route: RouteOption,
        alternative_routes: list[RouteOption],
    ) -> None:
        """Fallback explanation should include key route metrics (Req 13.2)."""
        with patch("app.services.reasoning_engine.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await engine.explain(recommended_route, alternative_routes)

        explanation = result.explanation
        # Should contain cost, ETA, carbon, risk
        assert "$3000" in explanation
        assert "264.0h" in explanation
        assert "770.0kg CO2" in explanation
        assert "25/100" in explanation

    @pytest.mark.asyncio
    async def test_fallback_contains_waypoints(
        self,
        engine: ReasoningEngine,
        recommended_route: RouteOption,
        alternative_routes: list[RouteOption],
    ) -> None:
        """Fallback explanation should include waypoints."""
        with patch("app.services.reasoning_engine.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await engine.explain(recommended_route, alternative_routes)

        assert "shanghai_port" in result.explanation
        assert "rotterdam_port" in result.explanation

    @pytest.mark.asyncio
    async def test_fallback_with_no_alternatives(
        self,
        engine: ReasoningEngine,
        recommended_route: RouteOption,
    ) -> None:
        """Fallback should work even with an empty alternatives list."""
        with patch("app.services.reasoning_engine.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await engine.explain(recommended_route, [])

        assert result.source == "fallback"
        assert "$3000" in result.explanation


# ── Truncation tests (Req 13.5) ─────────────────────────────────────


class TestTruncation:
    def test_short_text_unchanged(self) -> None:
        """Text under 200 words should not be truncated."""
        text = "This is a short explanation."
        assert _truncate(text) == text

    def test_exactly_200_words_unchanged(self) -> None:
        """Text of exactly 200 words should not be truncated."""
        text = " ".join(["word"] * 200)
        assert _truncate(text) == text

    def test_over_200_words_truncated(self) -> None:
        """Text over 200 words should be truncated to 200 words (Req 13.5)."""
        text = " ".join(["word"] * 250)
        result = _truncate(text)
        assert len(result.split()) == 200

    @pytest.mark.asyncio
    async def test_model_response_truncated(
        self,
        engine: ReasoningEngine,
        recommended_route: RouteOption,
        alternative_routes: list[RouteOption],
    ) -> None:
        """Long model responses should be truncated to 200 words."""
        long_text = " ".join(["explanation"] * 250)
        mock_response = httpx.Response(
            200,
            json={"choices": [{"message": {"content": long_text}}]},
            request=httpx.Request("POST", "https://router.huggingface.co/v1/chat/completions"),
        )
        with patch("app.services.reasoning_engine.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await engine.explain(recommended_route, alternative_routes)

        assert len(result.explanation.split()) <= 200
        assert result.source == "model"


# ── Prompt construction tests (Req 13.2) ─────────────────────────────


class TestPromptConstruction:
    def test_prompt_includes_route_metrics(
        self,
        recommended_route: RouteOption,
        alternative_routes: list[RouteOption],
    ) -> None:
        """Prompt should include cost, ETA, carbon, and risk (Req 13.2)."""
        prompt = ReasoningEngine._build_prompt(recommended_route, alternative_routes)
        assert "$3000" in prompt
        assert "264.0" in prompt
        assert "770.0" in prompt
        assert "25/100" in prompt

    def test_prompt_includes_alternatives(
        self,
        recommended_route: RouteOption,
        alternative_routes: list[RouteOption],
    ) -> None:
        """Prompt should list alternative routes for comparison."""
        prompt = ReasoningEngine._build_prompt(recommended_route, alternative_routes)
        assert "fastest" in prompt
        assert "safest" in prompt

    def test_prompt_includes_waypoints(
        self,
        recommended_route: RouteOption,
        alternative_routes: list[RouteOption],
    ) -> None:
        """Prompt should include the route waypoints."""
        prompt = ReasoningEngine._build_prompt(recommended_route, alternative_routes)
        assert "shanghai_port" in prompt
        assert "rotterdam_port" in prompt

    def test_prompt_with_empty_alternatives(
        self,
        recommended_route: RouteOption,
    ) -> None:
        """Prompt should handle empty alternatives gracefully."""
        prompt = ReasoningEngine._build_prompt(recommended_route, [])
        assert "None" in prompt


# ── Timeout configuration test (Req 13.3) ────────────────────────────


class TestTimeoutConfiguration:
    def test_default_timeout_is_15_seconds(self) -> None:
        """Default timeout must be 20 seconds (updated for Mistral model)."""
        engine = ReasoningEngine()
        assert engine._timeout == 20

    @pytest.mark.asyncio
    async def test_timeout_passed_to_httpx(
        self,
        recommended_route: RouteOption,
        alternative_routes: list[RouteOption],
    ) -> None:
        """The configured timeout should be passed to the httpx client."""
        engine = ReasoningEngine(timeout=15)
        with patch("app.services.reasoning_engine.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = httpx.Response(
                200,
                json={"choices":[{"message":{"content":"ok"}}]},
                request=httpx.Request("POST", "https://router.huggingface.co/v1/chat/completions"),
            )
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            await engine.explain(recommended_route, alternative_routes)

            mock_client_cls.assert_called_once_with(timeout=15)


# ── ExplainResponse model tests ──────────────────────────────────────


class TestExplainResponseModel:
    @pytest.mark.asyncio
    async def test_response_is_explain_response(
        self,
        engine: ReasoningEngine,
        recommended_route: RouteOption,
        alternative_routes: list[RouteOption],
    ) -> None:
        """The return type must be ExplainResponse."""
        with patch("app.services.reasoning_engine.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            result = await engine.explain(recommended_route, alternative_routes)

        assert isinstance(result, ExplainResponse)
        assert isinstance(result.explanation, str)
        assert result.source in ("model", "fallback")

