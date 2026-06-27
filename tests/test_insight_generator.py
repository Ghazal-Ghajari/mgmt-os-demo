"""
Tests for insight_generator.py

Covers:
  - Input validation
  - Prompt construction
  - Claude API integration (mocked)
  - CLI argument parsing
  - Edge cases

Run:
    pytest tests/test_insight_generator.py -v
"""

import json
import pytest
from unittest.mock import MagicMock, patch

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from insight_generator import (
    build_user_prompt,
    generate_insight,
    load_metrics,
    SAMPLE_METRICS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def minimal_metrics():
    return {
        "period": "Test week",
        "revenue": {"current": 100_000, "previous": 90_000, "target": 110_000},
    }


@pytest.fixture
def mock_anthropic_response():
    """Fake a successful Claude API response."""
    mock_content = MagicMock()
    mock_content.text = (
        "## What Changed\nRevenue dipped 11% week-over-week.\n\n"
        "## What It Means\nClose rate is down; pipeline quality needs review.\n\n"
        "## Where to Lead Next\n1. Review lost deals with reps.\n"
        "2. Protect at-risk accounts.\n3. Double down on top performer."
    )
    mock_message = MagicMock()
    mock_message.content = [mock_content]
    return mock_message


# ---------------------------------------------------------------------------
# build_user_prompt
# ---------------------------------------------------------------------------

class TestBuildUserPrompt:
    def test_contains_metrics_json(self, minimal_metrics):
        prompt = build_user_prompt(minimal_metrics)
        assert "100000" in prompt or "100_000" in prompt or json.dumps(minimal_metrics) in prompt

    def test_contains_instruction(self, minimal_metrics):
        prompt = build_user_prompt(minimal_metrics)
        assert "leadership insight" in prompt.lower()

    def test_period_included(self, minimal_metrics):
        prompt = build_user_prompt(minimal_metrics)
        assert "Test week" in prompt

    def test_returns_string(self, minimal_metrics):
        result = build_user_prompt(minimal_metrics)
        assert isinstance(result, str)
        assert len(result) > 0


# ---------------------------------------------------------------------------
# generate_insight — input validation
# ---------------------------------------------------------------------------

class TestGenerateInsightValidation:
    def test_empty_metrics_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            generate_insight({})

    def test_none_metrics_raises(self):
        with pytest.raises((ValueError, AttributeError)):
            generate_insight(None)


# ---------------------------------------------------------------------------
# generate_insight — mocked API calls
# ---------------------------------------------------------------------------

class TestGenerateInsightAPI:
    @patch("insight_generator.anthropic.Anthropic")
    def test_returns_string(self, mock_client_class, minimal_metrics, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_client_class.return_value = mock_client

        result = generate_insight(minimal_metrics)
        assert isinstance(result, str)
        assert len(result) > 10

    @patch("insight_generator.anthropic.Anthropic")
    def test_calls_correct_model(self, mock_client_class, minimal_metrics, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_client_class.return_value = mock_client

        generate_insight(minimal_metrics, model="claude-sonnet-4-6")

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["model"] == "claude-sonnet-4-6"

    @patch("insight_generator.anthropic.Anthropic")
    def test_system_prompt_passed(self, mock_client_class, minimal_metrics, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_client_class.return_value = mock_client

        generate_insight(minimal_metrics)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert "system" in call_kwargs
        assert len(call_kwargs["system"]) > 0

    @patch("insight_generator.anthropic.Anthropic")
    def test_response_contains_expected_sections(
        self, mock_client_class, minimal_metrics, mock_anthropic_response
    ):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_client_class.return_value = mock_client

        result = generate_insight(minimal_metrics)
        assert "What Changed" in result
        assert "What It Means" in result
        assert "Where to Lead" in result

    @patch("insight_generator.anthropic.Anthropic")
    def test_max_tokens_respected(self, mock_client_class, minimal_metrics, mock_anthropic_response):
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_anthropic_response
        mock_client_class.return_value = mock_client

        generate_insight(minimal_metrics, max_tokens=300)

        call_kwargs = mock_client.messages.create.call_args.kwargs
        assert call_kwargs["max_tokens"] == 300


# ---------------------------------------------------------------------------
# load_metrics
# ---------------------------------------------------------------------------

class TestLoadMetrics:
    def test_demo_flag_returns_sample(self):
        args = MagicMock()
        args.demo = True
        args.json_file = None
        result = load_metrics(args)
        assert result == SAMPLE_METRICS

    def test_no_flags_returns_sample(self, capsys):
        args = MagicMock()
        args.demo = False
        args.json_file = None
        result = load_metrics(args)
        assert result == SAMPLE_METRICS

    def test_json_file_loads_correctly(self, tmp_path, minimal_metrics):
        json_file = tmp_path / "metrics.json"
        json_file.write_text(json.dumps(minimal_metrics))

        args = MagicMock()
        args.demo = False
        args.json_file = str(json_file)

        result = load_metrics(args)
        assert result == minimal_metrics

    def test_invalid_json_raises(self, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("not valid json {{")

        args = MagicMock()
        args.demo = False
        args.json_file = str(bad_file)

        with pytest.raises(json.JSONDecodeError):
            load_metrics(args)


# ---------------------------------------------------------------------------
# Sample metrics schema sanity check
# ---------------------------------------------------------------------------

class TestSampleMetrics:
    def test_has_required_keys(self):
        for key in ("period", "revenue", "pipeline", "team", "churn"):
            assert key in SAMPLE_METRICS

    def test_revenue_has_delta(self):
        rev = SAMPLE_METRICS["revenue"]
        assert rev["current"] != rev["previous"], "Sample data should show a change"

    def test_team_has_at_risk_reps(self):
        assert SAMPLE_METRICS["team"]["reps_below_50_pct"] > 0
