from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from html import escape
from statistics import mean
from typing import Any

from . import logging_config
from .metrics import percentile


def _timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _records_for_last_hour() -> list[dict[str, Any]]:
    if not logging_config.LOG_PATH.exists():
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=60)
    records: list[dict[str, Any]] = []
    for line in logging_config.LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = _timestamp(record.get("ts"))
        if ts is not None and ts >= cutoff:
            records.append(record)
    return records


def _numbers(records: list[dict[str, Any]], event: str, field: str) -> list[float]:
    values: list[float] = []
    for record in records:
        value = record.get(field)
        if record.get("event") == event and isinstance(value, (int, float)):
            values.append(float(value))
    return values


def _card(title: str, value: str, detail: str, threshold: str, status: str) -> str:
    safe_status = status if status in {"good", "warn", "empty"} else "empty"
    return f"""
      <article class="panel {safe_status}">
        <div class="panel-head"><h2>{escape(title)}</h2><span>{escape(status.upper())}</span></div>
        <div class="value">{escape(value)}</div>
        <p>{escape(detail)}</p>
        <div class="threshold">Threshold · {escape(threshold)}</div>
      </article>
    """


def render_dashboard(records: list[dict[str, Any]] | None = None) -> str:
    records = _records_for_last_hour() if records is None else records
    received = [record for record in records if record.get("event") == "request_received"]
    responses = [record for record in records if record.get("event") == "response_sent"]
    failures = [record for record in records if record.get("event") == "request_failed"]

    latencies = [int(value) for value in _numbers(records, "response_sent", "latency_ms")]
    ttfts = [int(value) for value in _numbers(records, "response_sent", "ttft_ms")]
    p50 = percentile(latencies, 50)
    p95 = percentile(latencies, 95)
    p99 = percentile(latencies, 99)
    ttft_p95 = percentile(ttfts, 95)

    error_rate = 100 * len(failures) / len(received) if received else 0.0
    tool_results = [
        bool(record["tool_success"])
        for record in records
        if record.get("tool_name") == "retrieval" and record.get("tool_success") is not None
    ]
    retrieval_success = 100 * sum(tool_results) / len(tool_results) if tool_results else 0.0
    error_types: dict[str, int] = {}
    for record in failures:
        error_type = str(record.get("error_type", "unknown"))
        error_types[error_type] = error_types.get(error_type, 0) + 1

    costs = _numbers(records, "response_sent", "cost_usd")
    tokens_in = sum(_numbers(records, "response_sent", "tokens_in"))
    tokens_out = sum(_numbers(records, "response_sent", "tokens_out"))
    quality = _numbers(records, "response_sent", "quality_score")
    quality_avg = mean(quality) if quality else 0.0
    request_times = [
        ts
        for record in received
        if (ts := _timestamp(record.get("ts"))) is not None
    ]
    active_minutes = (
        max(1.0, (max(request_times) - min(request_times)).total_seconds() / 60)
        if request_times
        else 1.0
    )
    request_rate = len(received) / active_minutes

    has_data = bool(records)
    empty_status = "empty" if not has_data else "good"
    cards = [
        _card(
            "Latency & TTFT",
            f"P95 {p95:.0f} ms",
            f"P50 {p50:.0f} · P99 {p99:.0f} · TTFT P95 {ttft_p95:.0f} ms",
            "P95 ≤ 3,000 ms",
            "empty" if not latencies else ("good" if p95 <= 3000 else "warn"),
        ),
        _card(
            "Request traffic",
            f"{len(received)} requests",
            f"{request_rate:.2f} requests/min during the active workload",
            "Rate ≥ 1 request/min during active workload",
            "empty" if not received else ("good" if request_rate >= 1 else "warn"),
        ),
        _card(
            "Errors & retrieval",
            f"{error_rate:.1f}% errors",
            f"Retrieval success {retrieval_success:.1f}% · breakdown {error_types or {'none': 0}}",
            "Errors ≤ 2% · retrieval ≥ 90%",
            "empty"
            if not received
            else ("good" if error_rate <= 2 and retrieval_success >= 90 else "warn"),
        ),
        _card(
            "Cost",
            f"${sum(costs):.4f}",
            f"Average ${mean(costs):.6f}/response" if costs else "No completed responses",
            "Total ≤ $2.50",
            "empty" if not costs else ("good" if sum(costs) <= 2.5 else "warn"),
        ),
        _card(
            "Tokens",
            f"{tokens_in + tokens_out:,.0f}",
            f"Input {tokens_in:,.0f} · output {tokens_out:,.0f}",
            "Total ≤ 50,000 tokens",
            "empty"
            if not responses
            else ("good" if tokens_in + tokens_out <= 50000 else "warn"),
        ),
        _card(
            "Quality proxy",
            f"{quality_avg:.2f} / 1.00",
            f"Mean heuristic score across {len(quality)} responses",
            "Mean ≥ 0.75",
            "empty" if not quality else ("good" if quality_avg >= 0.75 else "warn"),
        ),
    ]

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="refresh" content="30">
  <title>K4-L3A LLMOps Dashboard</title>
  <style>
    :root {{ color-scheme: dark; --bg:#08111f; --card:#111d2f; --ink:#e8f0ff; --muted:#91a4c4; --line:#263752; --cyan:#31d7c6; --amber:#ffbb55; }}
    * {{ box-sizing:border-box }}
    body {{ margin:0; min-height:100vh; background:radial-gradient(circle at 20% 0,#102849 0,transparent 42%),var(--bg); color:var(--ink); font:15px/1.5 Inter,Segoe UI,sans-serif; }}
    main {{ width:min(1180px,calc(100% - 40px)); margin:0 auto; padding:42px 0 64px; }}
    header {{ display:flex; justify-content:space-between; gap:24px; align-items:flex-end; margin-bottom:26px; }}
    h1 {{ font-size:clamp(28px,5vw,48px); margin:0; letter-spacing:-.04em; }}
    header p {{ margin:8px 0 0; color:var(--muted); }}
    .meta {{ text-align:right; color:var(--muted); white-space:nowrap; }}
    .grid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }}
    .panel {{ min-height:220px; padding:22px; border:1px solid var(--line); border-radius:18px; background:linear-gradient(160deg,rgba(255,255,255,.04),transparent 58%),var(--card); box-shadow:0 16px 50px rgba(0,0,0,.2); }}
    .panel.good {{ border-top:3px solid var(--cyan); }} .panel.warn {{ border-top:3px solid var(--amber); }} .panel.empty {{ border-top:3px solid #5f708d; }}
    .panel-head {{ display:flex; justify-content:space-between; gap:12px; align-items:center; }}
    h2 {{ margin:0; font-size:15px; text-transform:uppercase; letter-spacing:.08em; color:#b9c8df; }}
    .panel-head span {{ font-size:11px; color:var(--muted); }}
    .value {{ font-size:34px; font-weight:750; margin:28px 0 8px; letter-spacing:-.03em; }}
    .panel p {{ min-height:46px; color:var(--muted); margin:0 0 22px; }}
    .threshold {{ border-top:1px solid var(--line); padding-top:14px; font-size:13px; color:#c8d5e9; }}
    footer {{ margin-top:22px; color:var(--muted); }}
    @media (max-width:850px) {{ .grid {{ grid-template-columns:1fr 1fr }} }}
    @media (max-width:560px) {{ .grid {{ grid-template-columns:1fr }} header {{ align-items:flex-start; flex-direction:column }} .meta {{ text-align:left }} }}
  </style>
</head>
<body><main>
  <header><div><h1>LLMOps control room</h1><p>Metrics → Logs → Traces · K4-L3A Day 13</p></div><div class="meta">Last 60 minutes<br>Refresh 30s<br>{escape(generated)}</div></header>
  <section class="grid">{''.join(cards)}</section>
  <footer>Source: data/logs.jsonl · Correlation IDs remain in structured logs for trace lookup.</footer>
</main></body></html>"""
