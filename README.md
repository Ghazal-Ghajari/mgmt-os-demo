# mgmt-os-demo

A focused portfolio artifact for the **Management OS Engineering & Product Intern** role.

Two tools that mirror the actual internship work, built with the same stack, the same mindset, and shipped to prove it.

---

## What's here

| File | What it does |
|------|-------------|
| `insight_generator.py` | Sends structured business metrics to the Claude API and returns a three-part leadership brief: *what changed · what it means · where to lead next*, the core value proposition of Management OS |
| `integration_checker.py` | Probes the live endpoints of every service in the Mgmt OS stack (Anthropic, Stripe, HubSpot, Supabase, Vercel, Clerk) and produces a health report |
| `tests/test_insight_generator.py` | 18-test suite covering input validation, prompt construction, mocked API calls, CLI argument parsing, and edge cases |

---

## Quick start

```bash
git clone https://github.com/Ghazal-Ghajari/mgmt-os-demo.git
cd mgmt-os-demo
pip install anthropic pytest
```

### Run the insight generator (demo mode, no API key needed to explore)

```bash
python insight_generator.py --demo
```

### Run with a real API key

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python insight_generator.py --demo
```

### Pipe in your own metrics

```bash
python insight_generator.py --json my_metrics.json
```

### Run the integration health checker

```bash
python integration_checker.py
```

Add service API keys as environment variables to get full coverage:

```bash
export HUBSPOT_TOKEN=...
export STRIPE_SECRET_KEY=...
python integration_checker.py --report   # saves docs/integration-report.md
```

### Run the test suite

```bash
pytest tests/ -v
```

Expected output: **18 passed**.

---

## Design decisions

**Why Python, not TypeScript?**
The two tools are pure logic, API calls, HTTP probes, data transformation. Python lets me ship something complete and testable in the time it would take to configure a TypeScript project. The same design ports directly to the Next.js / TypeScript stack.

**Why mock the API in tests?**
Tests should be fast, free, and deterministic. Mocking the Anthropic client isolates the logic I control (prompt construction, error handling, CLI parsing) from network variability. Integration tests against real endpoints are a separate concern, that's what `integration_checker.py` is for.

**Why probe real endpoints in the integration checker?**
Because that's the actual job. The tool surfaces exactly what a new engineer needs to know on day one: which services are reachable, which need credentials, and which are broken.

---

## Sample output

### `insight_generator.py --demo`

```
============================================================
## What Changed
Revenue fell 11% week-over-week to $187K against a $220K target.
Close rate dropped to 30% (3 won, 7 lost). Four of eight reps
are below 50% quota attainment.

## What It Means
This is a pipeline quality problem, not a volume problem.
High loss rate and low attainment signal deal qualification
or competitive pressure. Two at-risk accounts ($9.8K MRR)
compound the revenue risk.

## Where to Lead Next
1. Run a lost-deal debrief with the team this week.
2. Pull at-risk accounts to the top of your agenda.
3. Study Jordan M.'s approach and systematize it.
4. Tighten qualification criteria before adding new pipeline.
5. Reset target expectations with stakeholders if trend holds.
============================================================
```

### `integration_checker.py`

```
Management OS, Integration Health Check
──────────────────────────────────────────────────────────────────
  Service                    Status         Latency    Note
──────────────────────────────────────────────────────────────────
  ✅  Anthropic API           ok             74 ms      HTTP 404, healthy.
  🔑  Stripe API              auth_required  23 ms      Set $STRIPE_SECRET_KEY to test fully.
  🔑  HubSpot API             auth_required  23 ms      Set $HUBSPOT_TOKEN to test fully.
  ✅  Supabase                ok             19 ms      HTTP 200, healthy.
  🔑  Vercel API              auth_required  11 ms      Set $VERCEL_TOKEN to test fully.
  🔑  Clerk API               auth_required  33 ms      Set $CLERK_SECRET_KEY to test fully.
──────────────────────────────────────────────────────────────────
  2 ok · 4 auth_required · 0 need attention
```

---

## About me

PhD candidate in Computer Science (Wright State University).  
Research: Hyperdimensional Computing for IoT anomaly detection · GAN-based sensor synthesis · LLM-assisted security pipelines.  
14 peer-reviewed publications · 59 citations. h-index 5 · Claude API experience in production research pipelines.

I build and ship things. This repo is evidence of that.
