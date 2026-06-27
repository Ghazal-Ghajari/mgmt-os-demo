"""
Management OS — Integration Health Checker
Simulates the kind of integration-testing work described in the internship role:
run connectivity checks across external services, document what breaks.

Usage:
    python integration_checker.py                  # check all integrations
    python integration_checker.py --service hubspot
    python integration_checker.py --report          # save report to docs/
"""

import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CheckResult:
    service: str
    endpoint: str
    status: str          # "ok" | "degraded" | "unreachable" | "auth_required"
    latency_ms: Optional[float]
    note: str
    checked_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Integration definitions
# ---------------------------------------------------------------------------
# In a real environment these would pull env vars / OAuth tokens.
# Here we probe public health / status endpoints so the script runs without
# credentials and still demonstrates real network behaviour.

INTEGRATIONS = [
    {
        "service": "Anthropic API",
        "url": "https://api.anthropic.com",
        "auth_header": "x-api-key",
        "auth_env": "ANTHROPIC_API_KEY",
        "expect_status": [200, 404],   # 404 on root is normal; proves reachable
    },
    {
        "service": "Stripe API",
        "url": "https://api.stripe.com/v1",
        "auth_header": "Authorization",
        "auth_env": "STRIPE_SECRET_KEY",
        "expect_status": [200, 401],   # 401 = reachable, just no key
    },
    {
        "service": "HubSpot API",
        "url": "https://api.hubapi.com/crm/v3/objects/contacts",
        "auth_header": "Authorization",
        "auth_env": "HUBSPOT_TOKEN",
        "expect_status": [200, 401],
    },
    {
        "service": "Supabase (example project)",
        "url": "https://supabase.com",
        "auth_header": None,
        "auth_env": None,
        "expect_status": [200],
    },
    {
        "service": "Vercel API",
        "url": "https://api.vercel.com/v2/teams",
        "auth_header": "Authorization",
        "auth_env": "VERCEL_TOKEN",
        "expect_status": [200, 401, 403],
    },
    {
        "service": "Clerk API",
        "url": "https://api.clerk.com/v1/clients",
        "auth_header": "Authorization",
        "auth_env": "CLERK_SECRET_KEY",
        "expect_status": [200, 401, 403],
    },
]


# ---------------------------------------------------------------------------
# Check runner
# ---------------------------------------------------------------------------

TIMEOUT = 6  # seconds


def check_integration(cfg: dict) -> CheckResult:
    url = cfg["url"]
    service = cfg["service"]
    auth_env = cfg.get("auth_env")
    auth_header = cfg.get("auth_header")
    expected = cfg.get("expect_status", [200])

    headers = {"User-Agent": "mgmt-os-integration-checker/1.0"}

    # Attach auth token if available in environment
    if auth_header and auth_env:
        token = os.environ.get(auth_env, "")
        if token:
            if "Authorization" in auth_header:
                headers[auth_header] = f"Bearer {token}"
            else:
                headers[auth_header] = token

    req = urllib.request.Request(url, headers=headers)
    start = time.perf_counter()

    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            latency = round((time.perf_counter() - start) * 1000, 1)
            code = resp.status
    except urllib.error.HTTPError as exc:
        latency = round((time.perf_counter() - start) * 1000, 1)
        code = exc.code
    except urllib.error.URLError:
        latency = None
        return CheckResult(
            service=service,
            endpoint=url,
            status="unreachable",
            latency_ms=None,
            note="Network error — DNS failure or connection refused.",
        )
    except TimeoutError:
        return CheckResult(
            service=service,
            endpoint=url,
            status="degraded",
            latency_ms=None,
            note=f"Request timed out after {TIMEOUT}s.",
        )

    if code in expected:
        # Reachable but no valid credentials → auth_required
        if code in (401, 403):
            env_hint = f"Set ${auth_env}" if auth_env else "No auth configured."
            return CheckResult(
                service=service,
                endpoint=url,
                status="auth_required",
                latency_ms=latency,
                note=f"Endpoint reachable (HTTP {code}). {env_hint} to test fully.",
            )
        return CheckResult(
            service=service,
            endpoint=url,
            status="ok",
            latency_ms=latency,
            note=f"HTTP {code} — healthy.",
        )

    return CheckResult(
        service=service,
        endpoint=url,
        status="degraded",
        latency_ms=latency,
        note=f"Unexpected HTTP {code}.",
    )


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

STATUS_ICON = {
    "ok": "✅",
    "auth_required": "🔑",
    "degraded": "⚠️",
    "unreachable": "❌",
}


def print_result(r: CheckResult) -> None:
    icon = STATUS_ICON.get(r.status, "?")
    latency = f"{r.latency_ms} ms" if r.latency_ms is not None else "—"
    print(f"  {icon}  {r.service:<28} {r.status:<14} {latency:<10}  {r.note}")


def save_report(results: list[CheckResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Integration Health Report",
        f"\n_Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}_\n",
        "| Service | Status | Latency | Note |",
        "|---------|--------|---------|------|",
    ]
    for r in results:
        icon = STATUS_ICON.get(r.status, "?")
        lat = f"{r.latency_ms} ms" if r.latency_ms else "—"
        lines.append(f"| {r.service} | {icon} {r.status} | {lat} | {r.note} |")

    summary = {s: sum(1 for r in results if r.status == s) for s in STATUS_ICON}
    lines += [
        "\n## Summary",
        f"- ✅ OK: {summary['ok']}",
        f"- 🔑 Auth required: {summary['auth_required']}",
        f"- ⚠️  Degraded: {summary['degraded']}",
        f"- ❌ Unreachable: {summary['unreachable']}",
        "\n## Raw JSON\n",
        "```json",
        json.dumps([asdict(r) for r in results], indent=2),
        "```",
    ]

    path.write_text("\n".join(lines))
    print(f"\n  Report saved → {path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check connectivity to Management OS integration endpoints."
    )
    parser.add_argument(
        "--service",
        metavar="NAME",
        help="Check a single service by name (case-insensitive substring match).",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Save a Markdown report to docs/integration-report.md",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    integrations = INTEGRATIONS
    if args.service:
        integrations = [
            i for i in INTEGRATIONS
            if args.service.lower() in i["service"].lower()
        ]
        if not integrations:
            print(f"No integration matched '{args.service}'.", file=sys.stderr)
            sys.exit(1)

    print(f"\nManagement OS — Integration Health Check")
    print(f"{'─' * 70}")
    print(f"  {'Service':<28} {'Status':<14} {'Latency':<10}  Note")
    print(f"{'─' * 70}")

    results = []
    for cfg in integrations:
        result = check_integration(cfg)
        results.append(result)
        print_result(result)

    print(f"{'─' * 70}")

    ok = sum(1 for r in results if r.status == "ok")
    auth = sum(1 for r in results if r.status == "auth_required")
    bad = sum(1 for r in results if r.status in ("degraded", "unreachable"))
    print(f"\n  {ok} ok · {auth} auth_required · {bad} need attention\n")

    if args.report:
        save_report(results, Path("docs/integration-report.md"))


if __name__ == "__main__":
    main()
