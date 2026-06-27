"""
Management OS — Leadership Insight Generator
Demonstrates AI-native development using the Claude API.

Given structured business metrics, this tool surfaces:
  - What changed
  - What it means
  - Where to lead next

Usage:
    python insight_generator.py
    python insight_generator.py --demo          # run with sample data
    python insight_generator.py --json output   # pipe JSON metrics in
"""

import anthropic
import json
import argparse
import sys
from typing import Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

SAMPLE_METRICS = {
    "period": "Week of June 23, 2026",
    "revenue": {
        "current": 187_400,
        "previous": 210_300,
        "target": 220_000,
    },
    "pipeline": {
        "new_opportunities": 14,
        "closed_won": 3,
        "closed_lost": 7,
        "avg_deal_size": 24_500,
    },
    "team": {
        "headcount": 8,
        "quota_attainment_pct": 62,
        "top_performer": "Jordan M.",
        "reps_below_50_pct": 4,
    },
    "churn": {
        "accounts_at_risk": 2,
        "mrr_at_risk": 9_800,
    },
}


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are the analytical engine inside Management OS — 
an AI-native operating system for founders and revenue leaders.

Your job is to help a leader answer three questions from raw business metrics:
1. What changed? (facts, deltas, signals — concise)
2. What does it mean? (root causes, risks, opportunities)
3. Where should I lead next? (3–5 prioritized, actionable next steps)

Rules:
- Be direct. Leaders are busy. No filler.
- Flag risks first, then opportunities.
- Ground every claim in the numbers provided.
- Format output in three clearly labelled sections.
- Keep the whole response under 350 words.
"""


def build_user_prompt(metrics: dict) -> str:
    return (
        "Here are this week's business metrics. "
        "Generate a leadership insight brief.\n\n"
        f"```json\n{json.dumps(metrics, indent=2)}\n```"
    )


# ---------------------------------------------------------------------------
# Core function
# ---------------------------------------------------------------------------

def generate_insight(
    metrics: dict,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 600,
) -> str:
    """
    Send business metrics to Claude and return a structured leadership brief.

    Args:
        metrics:    Dict of business KPIs (see SAMPLE_METRICS for schema).
        model:      Anthropic model ID.
        max_tokens: Upper bound on response length.

    Returns:
        A plain-text leadership insight brief.

    Raises:
        anthropic.APIError: on network or auth failures.
        ValueError: if metrics is empty or malformed.
    """
    if not metrics:
        raise ValueError("metrics dict must not be empty")

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from environment

    message = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": build_user_prompt(metrics)},
        ],
    )

    return message.content[0].text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a leadership insight brief from business metrics."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--demo",
        action="store_true",
        help="Run with built-in sample data (no input required).",
    )
    group.add_argument(
        "--json",
        dest="json_file",
        metavar="FILE",
        help="Path to a JSON file containing metrics (use '-' for stdin).",
    )
    return parser.parse_args()


def load_metrics(args: argparse.Namespace) -> dict:
    if args.demo or (not args.json_file):
        print("[ demo mode — using sample metrics ]\n")
        return SAMPLE_METRICS

    if args.json_file == "-":
        raw = sys.stdin.read()
    else:
        with open(args.json_file) as fh:
            raw = fh.read()

    return json.loads(raw)


def main() -> None:
    args = parse_args()
    metrics = load_metrics(args)

    print("Generating leadership insight brief…\n")
    print("=" * 60)

    try:
        brief = generate_insight(metrics)
        print(brief)
    except anthropic.AuthenticationError:
        print("ERROR: ANTHROPIC_API_KEY is missing or invalid.", file=sys.stderr)
        sys.exit(1)
    except anthropic.APIError as exc:
        print(f"ERROR: Claude API call failed — {exc}", file=sys.stderr)
        sys.exit(1)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)


if __name__ == "__main__":
    main()
