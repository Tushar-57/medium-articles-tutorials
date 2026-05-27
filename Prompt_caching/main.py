#!/usr/bin/env python3
"""
Prompt Caching Demo CLI
─────────────────────────────────────────────────────────────────────────────
Shows real token counts, latency, and cost — before and after prompt caching.

OpenAI automatically caches prompt prefixes longer than 1,024 tokens.
Every query here reuses the same large system prompt, so from query 2 onward
those tokens cost 50% less and arrive faster.

Run:
    cp .env.example .env   # add your OPENAI_API_KEY
    pip install -r requirements.txt
    python main.py

Commands while running:
    <any question>          → ask the support bot, see live stats
    !compare <question>     → run same query twice, side-by-side comparison
    !stats                  → session summary with at-scale projection
    !exit / Ctrl+C          → quit
─────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import time
from dotenv import load_dotenv

load_dotenv()

# ── validate env before heavy imports ────────────────────────────────────────
if not os.getenv("OPENAI_API_KEY"):
    print("\n[ERROR] OPENAI_API_KEY not set. Copy .env.example → .env and add your key.\n")
    sys.exit(1)

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich import box

console = Console()

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# ── Pricing per token (as of mid-2025) ───────────────────────────────────────
PRICING = {
    "gpt-4o": {
        "input":        2.50 / 1_000_000,   # $2.50  per 1M tokens
        "cached_input": 1.25 / 1_000_000,   # $1.25  per 1M tokens (50% off)
        "output":      10.00 / 1_000_000,   # $10.00 per 1M tokens
    },
    "gpt-4o-mini": {
        "input":        0.150 / 1_000_000,  # $0.15  per 1M tokens
        "cached_input": 0.075 / 1_000_000,  # $0.075 per 1M tokens (50% off)
        "output":       0.600 / 1_000_000,  # $0.60  per 1M tokens
    },
}

# ── System prompt (~1,800 tokens) ────────────────────────────────────────────
# This is deliberately large and static — exactly the kind of context that
# companies inject on every API call: product docs, policies, knowledge base.
# OpenAI caches prefixes > 1,024 tokens automatically; everything below this
# line is the part that gets cached from the second query onward.
# ─────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """
You are a senior support engineer for DataFlow Pro — an enterprise data-analytics
platform used by 5,000+ companies worldwide. Answer questions clearly and concisely.
If something is outside your knowledge, say so honestly and suggest next steps.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRODUCT OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DataFlow Pro is a cloud-native data-analytics platform that helps businesses
transform raw data into actionable insights. Founded in 2018, it serves companies
from early-stage startups to Fortune 500 enterprises across 40 countries.

Core capabilities:
• Real-time data ingestion from 200+ connectors:
  Salesforce, HubSpot, Stripe, Shopify, Zendesk, PostgreSQL, MySQL, MongoDB,
  DynamoDB, Redis, S3, GCS, Azure Blob, BigQuery, Snowflake, Redshift, Databricks,
  Kafka, RabbitMQ, Google Analytics 4, Facebook Ads, TikTok Ads, LinkedIn Ads,
  Mixpanel, Amplitude, Segment, Twilio, SendGrid, Slack, Jira, GitHub, and more.
• Visual pipeline builder with drag-and-drop interface, no SQL required for basics.
• ML-powered anomaly detection, forecasting, and cohort analysis.
• Custom dashboard builder with 50+ chart types (line, bar, funnel, sankey, heatmap,
  geo-map, table, KPI card, gauge, scatter, histogram, waterfall, and more).
• Automated reporting: schedule dashboards as PDF/CSV emails or Slack messages.
• Role-based access control (RBAC) with SSO via Okta, Auth0, Azure AD, Google Workspace.
• SOC 2 Type II certified, GDPR-ready, HIPAA-eligible (Business+ plans).
• 99.95% uptime SLA on Business and Enterprise plans.
• Data residency options: US, EU, APAC.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PRICING TIERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STARTER — $49 / month (billed monthly) or $39 / month (billed annually)
  • Up to 5 data sources
  • 10 GB storage
  • 3 seats
  • Community forum support only
  • Basic connectors (databases, flat files)
  • 5 dashboards, 3 automated reports
  • Data refresh: every 24 hours

PROFESSIONAL — $299 / month (or $249 / month annually)
  • Up to 25 data sources
  • 100 GB storage
  • 15 seats
  • Email support, 48-hour business-day SLA
  • All 200+ connectors
  • Unlimited dashboards and reports
  • Data refresh: every 1 hour
  • API access: 1,000 requests / day, 10 req / min
  • Custom branding on reports

BUSINESS — $899 / month (or $749 / month annually)
  • Up to 100 data sources
  • 1 TB storage
  • Unlimited seats
  • Priority email + chat support, 4-hour SLA
  • Advanced ML features (forecasting, anomaly alerts)
  • API access: 50,000 requests / day, 100 req / min
  • White-label option
  • Custom integrations via webhook
  • SSO (SAML 2.0)
  • Data refresh: every 15 minutes
  • HIPAA Business Associate Agreement available

ENTERPRISE — Custom pricing (contact sales@dataflowpro.io)
  • Unlimited data sources and storage
  • Dedicated customer success manager
  • 1-hour SLA, 24/7 on-call support
  • On-premise or private-cloud deployment
  • Custom data residency
  • Unlimited API access
  • Professional services: onboarding, training, custom development
  • SLA credits: 10% per hour of downtime exceeding SLA

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TROUBLESHOOTING GUIDE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

ISSUE: Pipeline fails — "Connection timeout"
  Cause: Firewall blocking DataFlow Pro egress IPs, or stale credentials.
  Fix:
    1. Whitelist IPs: 34.120.0.0/16 and 35.191.0.0/16 in your firewall.
    2. Rotate the connector credentials in Settings > Connectors > [Source] > Edit.
    3. For database sources, verify max_connections allows at least 5 concurrent connections.
    4. Re-run the pipeline. If still failing, share the Pipeline Log ID with support.

ISSUE: Dashboard loads slowly (>5 seconds)
  Cause: Query over too many rows, or no date-range filter applied.
  Fix:
    1. Enable dashboard query caching: Dashboard > Settings > Performance > Cache: ON.
    2. Add a Date Range filter widget and set a default range (e.g., last 30 days).
    3. For datasets >1 M rows, create a pre-aggregated summary table and point the
       dashboard at it instead.
    4. Check if another user's heavy export is running concurrently — it shares compute.

ISSUE: Data sync delayed or stuck
  Cause: Source API rate-limit, large initial backfill, or transient source outage.
  Fix:
    1. Open Pipeline Logs (Pipelines > [Name] > Logs) and note the error code.
    2. Error 429 from source → you've hit the source's rate limit; wait 1 hour and retry.
    3. Stuck >2 hours with no error → click Pipelines > [Name] > Actions > Force Restart.
    4. Salesforce specifically: check API limit usage in Salesforce Setup > System Overview.
    5. If data is >30 days stale, contact support with the pipeline ID — we may need to
       manually reset the sync cursor.

ISSUE: Users can't log in after SSO configuration
  Cause: Attribute mapping mismatch, or SP metadata not refreshed in the IdP.
  Fix:
    1. In DataFlow Pro: Settings > SSO > download SP metadata (fresh copy).
    2. Re-upload the SP metadata XML to your IdP (Okta, Azure AD, etc.).
    3. Verify the email attribute name matches exactly — DataFlow Pro expects
       "email" or "http://schemas.xmlsoap.org/ws/2005/05/identity/claims/emailaddress".
    4. Redirect URI must be exactly: https://app.dataflowpro.io/auth/callback
    5. Test with one pilot user before rolling out to the whole team.

ISSUE: API returning HTTP 429
  Cause: Daily or per-minute rate limit exceeded for your plan.
  Fix:
    1. Implement exponential backoff with jitter (start at 1s, max 32s).
    2. Switch to bulk endpoints instead of looping single-record endpoints where possible.
    3. Cache API responses client-side for read-heavy operations.
    4. Upgrade plan if you consistently hit limits.

ISSUE: Missing data in a connector after a source schema change
  Cause: DataFlow Pro cached the old schema; new columns aren't mapped.
  Fix:
    1. Pipelines > [Name] > Settings > Schema > Refresh Schema.
    2. Map any new columns in the field mapper.
    3. Trigger a manual sync to backfill from the point of schema change.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
API QUICK REFERENCE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Base URL: https://api.dataflowpro.io/v2
Auth:     Authorization: Bearer <YOUR_API_KEY>

Pipelines:
  GET    /pipelines                List all pipelines
  POST   /pipelines                Create pipeline
  GET    /pipelines/{id}/status    Get run status
  POST   /pipelines/{id}/trigger   Trigger manual sync
  DELETE /pipelines/{id}           Delete pipeline

Dashboards:
  GET    /dashboards               List dashboards
  GET    /dashboards/{id}/data     Fetch rendered data (JSON)
  POST   /dashboards               Create dashboard

Reports:
  GET    /reports                  List scheduled reports
  POST   /reports/{id}/run         Run report immediately

Rate limits:
  Professional:  1,000 req/day,  10 req/min
  Business:     50,000 req/day, 100 req/min
  Enterprise:   Unlimited (fair-use)

Error codes:
  400 Bad Request      → check request body / params
  401 Unauthorized     → invalid or expired API key
  403 Forbidden        → feature not available on your plan
  404 Not Found        → resource ID doesn't exist
  429 Too Many Requests → rate limit; Retry-After header contains wait time
  500 Internal Error   → transient; retry with backoff; contact support if persists

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUPPORT POLICIES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Response SLAs (business hours unless noted):
  Starter:     Community forum, no guaranteed response
  Professional: 48 hours
  Business:    4 hours
  Enterprise:  1 hour, 24/7

Escalation path:  L1 Support → L2 Engineering → Product → VP Engineering

Critical issues (data loss, full outage): email critical@dataflowpro.io — monitored 24/7.
Enterprise customers: use the dedicated on-call pager in your Enterprise portal.

Billing:
  • 30-day money-back guarantee for new subscriptions.
  • Annual plans: pro-rated credit if downgrading mid-term; no cash refund.
  • Billing contact: billing@dataflowpro.io

Data retention:
  • Pipeline run history: 90 days (Professional), 1 year (Business+)
  • Audit logs: same as above
  • Deleted data: permanently purged within 30 days of deletion request.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RESPONSE GUIDELINES FOR SUPPORT ENGINEERS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Be empathetic and solution-focused. Acknowledge frustration before diving into steps.
• If the fix differs by plan tier, ask which plan the customer is on before advising.
• Billing/refund issues → escalate to billing@dataflowpro.io; do not promise outcomes.
• Never confirm unannounced roadmap features. Reference the public changelog only.
• Data-loss issues → escalate immediately to critical@dataflowpro.io, do not attempt DIY fixes.
• Always end your reply with one clear next action for the customer.
""".strip()


# ── Helpers ───────────────────────────────────────────────────────────────────

def get_pricing(model: str) -> dict:
    return PRICING.get(model, PRICING["gpt-4o-mini"])


def calc_cost(input_tokens: int, cached_tokens: int, output_tokens: int) -> dict:
    p = get_pricing(MODEL)
    fresh = input_tokens - cached_tokens

    actual     = fresh * p["input"] + cached_tokens * p["cached_input"] + output_tokens * p["output"]
    no_cache   = input_tokens * p["input"] + output_tokens * p["output"]
    saved      = no_cache - actual
    saved_pct  = (saved / no_cache * 100) if no_cache > 0 else 0.0

    return {"actual": actual, "no_cache": no_cache, "saved": saved, "pct": saved_pct}


def call_api(llm: ChatOpenAI, user_input: str) -> dict:
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=user_input),
    ]
    t0 = time.perf_counter()
    response = llm.invoke(messages)
    elapsed = time.perf_counter() - t0

    usage   = response.response_metadata.get("token_usage", {})
    details = usage.get("prompt_tokens_details") or {}

    return {
        "query":         user_input,
        "response":      response.content,
        "input_tokens":  usage.get("prompt_tokens", 0),
        "cached_tokens": details.get("cached_tokens", 0),
        "output_tokens": usage.get("completion_tokens", 0),
        "elapsed":       elapsed,
    }


# ── Display helpers ───────────────────────────────────────────────────────────

def banner():
    p = get_pricing(MODEL)
    prompt_word_count = len(SYSTEM_PROMPT.split())

    console.print()
    console.print(Panel(
        f"[bold cyan]Prompt Caching Demo[/bold cyan]  [dim]—  real numbers, real savings[/dim]\n\n"
        f"[bold]Model:[/bold] [cyan]{MODEL}[/cyan]   "
        f"[bold]System prompt:[/bold] ~{prompt_word_count:,} words\n\n"
        "[yellow bold]How it works:[/yellow bold]\n"
        "  OpenAI caches prompt prefixes longer than [bold]1,024 tokens[/bold] on their servers.\n"
        "  Your first query pays full price and [bold]warms the cache[/bold].\n"
        "  Every query after that gets [bold green]50% off[/bold green] on all those cached tokens\n"
        "  — and the model responds faster because it skips re-processing them.\n\n"
        f"[dim]Cached-input price: ${p['cached_input']*1_000_000:.3f}/1M tokens  "
        f"(vs ${p['input']*1_000_000:.3f}/1M full price)[/dim]\n\n"
        "[bold]Commands:[/bold]  "
        "<question>   [dim]ask anything[/dim]   "
        "[cyan]!compare <question>[/cyan]   [dim]side-by-side run[/dim]   "
        "[cyan]!stats[/cyan]   [dim]session totals[/dim]   "
        "[cyan]!exit[/cyan]",
        border_style="cyan",
        padding=(1, 2),
    ))


def show_result(r: dict, n: int):
    cached   = r["cached_tokens"]
    total_in = r["input_tokens"]
    cache_pct = (cached / total_in * 100) if total_in > 0 else 0
    cost = calc_cost(r["input_tokens"], r["cached_tokens"], r["output_tokens"])

    # ── response panel ────────────────────────────────────────────────────────
    console.print(Panel(
        r["response"],
        title=f"[bold cyan]Response #{n}[/bold cyan]",
        border_style="cyan",
        padding=(0, 1),
    ))

    # ── stats table ───────────────────────────────────────────────────────────
    t = Table(box=box.ROUNDED, border_style="dim", show_header=False,
              padding=(0, 1), min_width=60)
    t.add_column("Metric", style="bold", min_width=22)
    t.add_column("Value",  justify="right", min_width=14)
    t.add_column("Details", style="dim")

    t.add_row("Latency", f"[bold]{r['elapsed']:.2f}s[/bold]", "wall-clock time")
    t.add_row("Input tokens (total)", f"{total_in:,}",
              "system prompt + your query")

    if cached > 0:
        t.add_row(
            "[green]↳ Cached tokens[/green]",
            f"[bold green]{cached:,}[/bold green]",
            f"[green]{cache_pct:.0f}% of input — billed at 50% price[/green]",
        )
        t.add_row(
            "↳ Fresh tokens",
            f"{total_in - cached:,}",
            "your query, processed at full price",
        )
    else:
        t.add_row(
            "[yellow]↳ Cached tokens[/yellow]",
            "[yellow]0[/yellow]",
            "[yellow]first call — cache warming now[/yellow]",
        )

    t.add_row("Output tokens", f"{r['output_tokens']:,}", "response length")
    t.add_row(Rule(), Rule(), Rule())

    t.add_row("Cost this query",  f"[bold]${cost['actual']:.5f}[/bold]", "with caching")
    t.add_row("Cost without cache", f"${cost['no_cache']:.5f}", "what you'd normally pay")

    if cached > 0:
        t.add_row(
            "[bold green]You saved[/bold green]",
            f"[bold green]${cost['saved']:.5f}[/bold green]",
            f"[green]{cost['pct']:.1f}% off this query[/green]",
        )

    console.print(t)


def show_comparison(r1: dict, r2: dict):
    c1 = calc_cost(r1["input_tokens"], r1["cached_tokens"], r1["output_tokens"])
    c2 = calc_cost(r2["input_tokens"], r2["cached_tokens"], r2["output_tokens"])

    # Dynamic column headers based on actual cache state
    r1_col = "Run 1  (cold cache)" if r1["cached_tokens"] == 0 else f"Run 1  ({r1['cached_tokens']:,} cached)"
    r2_col = "Run 2  (cached)"     if r2["cached_tokens"] > 0  else "Run 2  (cache miss)"

    lat_delta = r1["elapsed"] - r2["elapsed"]
    lat_label = (
        f"[green]{lat_delta:.2f}s faster[/green]"  if lat_delta >  0.05
        else f"[red]{abs(lat_delta):.2f}s slower[/red]" if lat_delta < -0.05
        else "[dim]similar[/dim]"
    )

    # Cost delta between the two runs (not vs baseline)
    run_delta = c1["actual"] - c2["actual"]
    if run_delta > 0.000001:
        cost_label = f"[green]{run_delta/c1['actual']*100:.1f}% cheaper than Run 1[/green]"
    elif r1["cached_tokens"] > 0:
        cost_label = "[dim]both runs already cached — same cost[/dim]"
    else:
        cost_label = "[yellow]cache miss on Run 2[/yellow]"

    t = Table(
        title="[bold yellow]Cache effect: Run 1 vs Run 2[/bold yellow]",
        box=box.DOUBLE_EDGE,
        border_style="yellow",
        padding=(0, 1),
        min_width=70,
    )
    t.add_column("Metric",  style="bold",     min_width=22)
    t.add_column(r1_col,    justify="right",  style="red",   min_width=22)
    t.add_column(r2_col,    justify="right",  style="green", min_width=22)
    t.add_column("Δ",       justify="right",  min_width=28)

    # Cached tokens — show actual values for both runs
    new_cached  = r2["cached_tokens"] - r1["cached_tokens"]
    cache_delta = (
        f"[green]+{new_cached:,} newly cached[/green]" if new_cached > 0
        else "[dim]same[/dim]"
    )
    t.add_row(
        "Cached tokens",
        f"{r1['cached_tokens']:,}",
        f"{r2['cached_tokens']:,}",
        cache_delta,
    )

    t.add_row(
        "Latency",
        f"{r1['elapsed']:.2f}s",
        f"{r2['elapsed']:.2f}s",
        lat_label,
    )

    t.add_row(
        "Actual cost",
        f"${c1['actual']:.5f}",
        f"${c2['actual']:.5f}",
        cost_label,
    )

    # Savings vs full-price baseline for each run
    s1 = f"${c1['saved']:.5f} ({c1['pct']:.0f}% off)" if c1["pct"] > 0 else "—"
    s2 = f"${c2['saved']:.5f} ({c2['pct']:.0f}% off)" if c2["pct"] > 0 else "—"
    t.add_row("Saved vs full price", s1, s2, "")

    console.print()
    console.print(t)

    # at-scale projection — use whichever run saved more
    best_saved = max(c1["saved"], c2["saved"])
    if best_saved > 0:
        per_day_1k  = best_saved * 1_000
        per_day_10k = best_saved * 10_000
        console.print(Panel(
            f"[bold]At scale — caching this system prompt saves:[/bold]\n\n"
            f"  [cyan]1,000 queries/day[/cyan]  →  [bold green]${per_day_1k:.2f}/day[/bold green] saved"
            f"  ([dim]${per_day_1k*30:.0f}/month[/dim])\n"
            f"  [cyan]10,000 queries/day[/cyan] →  [bold green]${per_day_10k:.2f}/day[/bold green] saved"
            f"  ([dim]${per_day_10k*30:.0f}/month[/dim])\n\n"
            "[dim]Real-world system prompts are often 10–100× bigger than this demo.\n"
            "The bigger your static context, the more dramatic the savings.[/dim]",
            border_style="green",
            title="[green bold]Extrapolated savings[/green bold]",
            padding=(0, 2),
        ))


def show_stats(history: list):
    if not history:
        console.print("[dim]No queries yet.[/dim]")
        return

    total_actual   = sum(calc_cost(r["input_tokens"], r["cached_tokens"], r["output_tokens"])["actual"]   for r in history)
    total_no_cache = sum(calc_cost(r["input_tokens"], r["cached_tokens"], r["output_tokens"])["no_cache"] for r in history)
    total_saved    = total_no_cache - total_actual
    cache_hits     = sum(1 for r in history if r["cached_tokens"] > 0)
    avg_latency    = sum(r["elapsed"] for r in history) / len(history)

    t = Table(
        title="[bold cyan]Session Summary[/bold cyan]",
        box=box.ROUNDED,
        border_style="cyan",
        padding=(0, 1),
    )
    t.add_column("Metric",  style="bold")
    t.add_column("Value",   justify="right")

    t.add_row("Total queries",      str(len(history)))
    t.add_row("Cache hits",         f"{cache_hits} / {len(history)}")
    t.add_row("Avg latency",        f"{avg_latency:.2f}s")
    t.add_row("Spent (with cache)", f"${total_actual:.5f}")
    t.add_row("Would have spent",   f"${total_no_cache:.5f}")
    t.add_row("[bold green]Total saved[/bold green]",
              f"[bold green]${total_saved:.5f}[/bold green]")

    if total_saved > 0:
        daily_1k  = total_saved / len(history) * 1_000
        daily_10k = total_saved / len(history) * 10_000
        t.add_row("[dim]At 1K queries/day[/dim]",  f"[dim]~${daily_1k:.2f} saved/day[/dim]")
        t.add_row("[dim]At 10K queries/day[/dim]", f"[dim]~${daily_10k:.2f} saved/day[/dim]")

    console.print(t)


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    banner()

    llm     = ChatOpenAI(model=MODEL, temperature=0)
    history = []
    n       = 0

    console.print(
        "\n[dim]Tip: start with any question — e.g. "
        '"What plans do you offer?" or "How do I fix a connection timeout?"[/dim]\n'
    )

    while True:
        try:
            user_input = console.input("[bold cyan]You ›[/bold cyan] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Interrupted.[/dim]")
            show_stats(history)
            break

        if not user_input:
            continue

        cmd = user_input.lower()

        # ── exit ─────────────────────────────────────────────────────────────
        if cmd in {"!exit", "/exit", "exit", "quit", "q"}:
            show_stats(history)
            console.print("[dim]Goodbye.[/dim]")
            break

        # ── stats ─────────────────────────────────────────────────────────────
        if cmd in {"!stats", "/stats"}:
            show_stats(history)
            continue

        # ── compare mode ──────────────────────────────────────────────────────
        if cmd.startswith("!compare") or cmd.startswith("/compare"):
            # both "!compare" and "/compare" are 8 chars
            query = user_input[8:].strip() or "What plans do you offer and which one is best for a 10-person startup?"
            console.print(f"\n[bold yellow]Running same query twice to show caching effect…[/bold yellow]")
            console.print(f"[dim]Query: {query}[/dim]\n")

            console.print("[dim]─── Run 1: cache may be cold ───[/dim]")
            with console.status("[green]Calling API (run 1)…[/green]"):
                r1 = call_api(llm, query)
            n += 1
            history.append(r1)

            console.print(f"[dim]Run 1 done — {r1['cached_tokens']:,} cached tokens, {r1['elapsed']:.2f}s[/dim]")
            console.print("[dim]─── Run 2: cache should be warm ───[/dim]")
            with console.status("[green]Calling API (run 2)…[/green]"):
                r2 = call_api(llm, query)
            n += 1
            history.append(r2)

            console.print(f"[dim]Run 2 done — {r2['cached_tokens']:,} cached tokens, {r2['elapsed']:.2f}s[/dim]\n")
            show_comparison(r1, r2)
            continue

        # ── regular query ─────────────────────────────────────────────────────
        try:
            with console.status("[green]Thinking…[/green]"):
                result = call_api(llm, user_input)
        except Exception as e:
            console.print(f"[red]API error:[/red] {e}")
            continue

        n += 1
        history.append(result)
        show_result(result, n)

        if n == 1:
            console.print(
                "[dim]Cache is now warm. Ask another question or run "
                "[cyan]!compare <question>[/cyan] to see the difference.[/dim]\n"
            )


if __name__ == "__main__":
    main()
