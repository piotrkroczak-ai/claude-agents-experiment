"""
Generate documentation/token_report.html — an interactive token usage dashboard.

Usage:
    uv run python examples/usage_report.py

Reads:  documentation/token_usage.jsonl  (written by log_usage() in each agent)
Writes: documentation/token_report.html  (open in any browser)
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT       = Path(__file__).parent.parent
JSONL_PATH = ROOT / "documentation" / "token_usage.jsonl"
HTML_PATH  = ROOT / "documentation" / "token_report.html"


# ---------------------------------------------------------------------------
# Data loading + aggregation
# ---------------------------------------------------------------------------

def load_records() -> list[dict]:
    if not JSONL_PATH.exists():
        return []
    records = []
    with JSONL_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def build_data(records: list[dict]) -> dict:
    by_agent: dict = defaultdict(lambda: {"calls": 0, "input": 0, "output": 0, "cost": 0.0})
    by_model: dict = defaultdict(lambda: {"calls": 0, "tokens": 0, "cost": 0.0})
    by_run:   dict = defaultdict(lambda: {"calls": 0, "cost": 0.0, "ts": ""})

    for r in records:
        a = by_agent[r["agent"]]
        a["calls"] += 1
        a["input"]  += r["input"]
        a["output"] += r["output"]
        a["cost"]    = round(a["cost"] + r["cost_usd"], 8)

        m = by_model[r["model"]]
        m["calls"]  += 1
        m["tokens"] += r["input"] + r["output"]
        m["cost"]    = round(m["cost"] + r["cost_usd"], 8)

        run_key = r.get("run_id") or r["ts"][:19]
        run = by_run[run_key]
        run["calls"] += 1
        run["cost"]   = round(run["cost"] + r["cost_usd"], 8)
        if not run["ts"]:
            run["ts"] = r["ts"]

    runs_sorted = sorted(by_run.values(), key=lambda x: x["ts"])

    cache_savings = 0.0
    for r in records:
        cr = r.get("cache_read", 0)
        model = r.get("model", "")
        rate = 5.0 if "opus" in model else 1.0 if "haiku" in model else 3.0
        cache_savings += cr * rate * 0.9 / 1_000_000

    return {
        "records":  records,
        "by_agent": {k: dict(v) for k, v in by_agent.items()},
        "by_model": {k: dict(v) for k, v in by_model.items()},
        "runs":     runs_sorted,
        "totals": {
            "calls":         len(records),
            "runs":          len(by_run),
            "input":         sum(r["input"]  for r in records),
            "output":        sum(r["output"] for r in records),
            "cost":          round(sum(r["cost_usd"] for r in records), 8),
            "cache_savings": round(cache_savings, 8),
        },
    }


# ---------------------------------------------------------------------------
# HTML template (self-contained, Chart.js via CDN)
# ---------------------------------------------------------------------------

_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Token Usage Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:system-ui,-apple-system,sans-serif;background:#0f172a;color:#e2e8f0;padding:24px}
  h1{font-size:1.4rem;font-weight:700;margin-bottom:4px}
  .sub{color:#64748b;font-size:.8rem;margin-bottom:28px}
  .stats{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:24px}
  .stat{background:#1e293b;border-radius:8px;padding:18px}
  .stat-label{font-size:.7rem;color:#64748b;text-transform:uppercase;letter-spacing:.06em}
  .stat-value{font-size:1.6rem;font-weight:700;margin-top:4px}
  .charts{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:24px}
  .chart-full{grid-column:span 2}
  .card{background:#1e293b;border-radius:8px;padding:18px}
  .card h2{font-size:.7rem;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:.06em;margin-bottom:14px}
  canvas{max-height:240px}
  table{width:100%;border-collapse:collapse;font-size:.78rem}
  th{text-align:left;color:#64748b;font-weight:500;padding:7px 10px;border-bottom:1px solid #334155}
  td{padding:7px 10px;border-bottom:1px solid #0f172a;white-space:nowrap}
  tr:last-child td{border-bottom:none}
  tr:hover td{background:#0f172a}
  .badge{display:inline-block;padding:1px 7px;border-radius:4px;font-size:.68rem;font-weight:600}
  .bs{background:#1d4ed8;color:#bfdbfe}
  .bh{background:#065f46;color:#a7f3d0}
  .bo{background:#92400e;color:#fde68a}
  .empty{text-align:center;color:#475569;padding:32px}
</style>
</head>
<body>

<h1>Token Usage Dashboard</h1>
<div class="sub">Generated __GENERATED_AT__ &nbsp;·&nbsp; __TOTAL_CALLS__ API calls &nbsp;·&nbsp; __TOTAL_RUNS__ runs</div>

<div class="stats">
  <div class="stat">
    <div class="stat-label">Total Cost</div>
    <div class="stat-value" style="color:#34d399">$__TOTAL_COST__</div>
  </div>
  <div class="stat">
    <div class="stat-label">Input Tokens</div>
    <div class="stat-value">__TOTAL_INPUT__</div>
  </div>
  <div class="stat">
    <div class="stat-label">Output Tokens</div>
    <div class="stat-value">__TOTAL_OUTPUT__</div>
  </div>
  <div class="stat">
    <div class="stat-label">Cache Savings</div>
    <div class="stat-value" style="color:#fbbf24">$__CACHE_SAVINGS__</div>
  </div>
</div>

<div class="charts">
  <div class="card">
    <h2>Cost by Agent</h2>
    <canvas id="agentChart"></canvas>
  </div>
  <div class="card">
    <h2>Token Mix by Model</h2>
    <canvas id="modelChart"></canvas>
  </div>
  <div class="card chart-full">
    <h2>Cumulative Cost per Run</h2>
    <canvas id="runChart"></canvas>
  </div>
</div>

<div class="card">
  <h2>Recent Calls (last 50)</h2>
  <table>
    <thead>
      <tr>
        <th>Time</th><th>Run ID</th><th>Agent</th><th>Call</th>
        <th>Model</th><th>Input</th><th>Output</th><th>Cost</th>
      </tr>
    </thead>
    <tbody id="tbody"></tbody>
  </table>
</div>

<script>
const D = __DATA_JSON__;
const COLORS = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#ec4899','#06b6d4'];
const gridColor = '#1e293b', tickColor = '#64748b';

// Recent calls table
const tbody = document.getElementById('tbody');
if (!D.records.length) {
  tbody.innerHTML = '<tr><td colspan="8" class="empty">No data yet — run an agent first.</td></tr>';
} else {
  [...D.records].reverse().slice(0, 50).forEach(r => {
    const cls = r.model.includes('haiku') ? 'bh' : r.model.includes('opus') ? 'bo' : 'bs';
    const mShort = r.model.includes('haiku') ? 'Haiku 4.5' : r.model.includes('opus') ? 'Opus 4.7' : 'Sonnet 4.6';
    tbody.innerHTML += `<tr>
      <td>${r.ts.slice(11,19)}</td>
      <td style="font-family:monospace;color:#475569;font-size:.72rem">${r.run_id||'—'}</td>
      <td>${r.agent}</td>
      <td>${r.call}</td>
      <td><span class="badge ${cls}">${mShort}</span></td>
      <td>${r.input.toLocaleString()}</td>
      <td>${r.output.toLocaleString()}</td>
      <td style="color:#34d399">$${r.cost_usd.toFixed(6)}</td>
    </tr>`;
  });
}

// Cost by agent — horizontal bar
const agentLabels = Object.keys(D.by_agent);
const agentCosts  = agentLabels.map(a => +D.by_agent[a].cost.toFixed(6));
new Chart(document.getElementById('agentChart'), {
  type: 'bar',
  data: {
    labels: agentLabels,
    datasets: [{
      data: agentCosts,
      backgroundColor: agentLabels.map((_, i) => COLORS[i % COLORS.length]),
    }]
  },
  options: {
    indexAxis: 'y',
    plugins: { legend: { display: false } },
    scales: {
      x: { ticks: { color: tickColor, callback: v => '$' + v.toFixed(4) }, grid: { color: gridColor } },
      y: { ticks: { color: tickColor }, grid: { display: false } },
    }
  }
});

// Token mix by model — doughnut
const mLabels = Object.keys(D.by_model).map(
  m => m.includes('haiku') ? 'Haiku 4.5' : m.includes('opus') ? 'Opus 4.7' : 'Sonnet 4.6'
);
const mTokens = Object.keys(D.by_model).map(m => D.by_model[m].tokens);
const mColors = Object.keys(D.by_model).map(
  m => m.includes('haiku') ? '#10b981' : m.includes('opus') ? '#f59e0b' : '#3b82f6'
);
new Chart(document.getElementById('modelChart'), {
  type: 'doughnut',
  data: {
    labels: mLabels,
    datasets: [{ data: mTokens, backgroundColor: mColors, borderWidth: 2, borderColor: '#1e293b' }]
  },
  options: { plugins: { legend: { labels: { color: tickColor } } } }
});

// Cumulative cost line chart
let cum = 0;
const runLabels = D.runs.map((_, i) => 'Run ' + (i + 1));
const cumCosts  = D.runs.map(r => +(cum += r.cost).toFixed(6));
new Chart(document.getElementById('runChart'), {
  type: 'line',
  data: {
    labels: runLabels,
    datasets: [{
      label: 'Cumulative Cost (USD)',
      data: cumCosts,
      borderColor: '#3b82f6',
      backgroundColor: 'rgba(59,130,246,0.08)',
      fill: true,
      tension: 0.3,
      pointRadius: D.runs.length < 40 ? 4 : 0,
    }]
  },
  options: {
    plugins: { legend: { labels: { color: tickColor } } },
    scales: {
      x: { ticks: { color: tickColor, maxTicksLimit: 20 }, grid: { color: '#334155' } },
      y: { ticks: { color: tickColor, callback: v => '$' + v.toFixed(4) }, grid: { color: '#334155' } },
    }
  }
});
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

def generate() -> None:
    records = load_records()
    data = build_data(records)
    t = data["totals"]

    # Safely embed JSON (prevent </script> injection)
    data_json = json.dumps(data, default=str).replace("</script>", r"<\/script>")

    html = _HTML
    html = html.replace("__GENERATED_AT__",  datetime.now().strftime("%Y-%m-%d %H:%M"))
    html = html.replace("__TOTAL_CALLS__",   str(t["calls"]))
    html = html.replace("__TOTAL_RUNS__",    str(t["runs"]))
    html = html.replace("__TOTAL_COST__",    f"{t['cost']:.6f}")
    html = html.replace("__TOTAL_INPUT__",   f"{t['input']:,}")
    html = html.replace("__TOTAL_OUTPUT__",  f"{t['output']:,}")
    html = html.replace("__CACHE_SAVINGS__", f"{t['cache_savings']:.6f}")
    html = html.replace("__DATA_JSON__",     data_json)

    HTML_PATH.write_text(html, encoding="utf-8")
    print(f"Report: {HTML_PATH}")
    print(f"Cost:   ${t['cost']:.6f}  |  Calls: {t['calls']}  |  Runs: {t['runs']}")
    if not records:
        print("(No data yet — run an agent to populate token_usage.jsonl)")


if __name__ == "__main__":
    generate()
