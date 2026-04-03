"""Generate an interactive HTML chart of historical regime scores."""

import json
from .historical_scores import compute_historical_scores


def generate_chart_html(output_path="regime_chart.html"):
    """Generate an interactive HTML chart with Chart.js."""

    data = compute_historical_scores()
    dates = [d["date"] for d in data]
    scores = [d["score"] for d in data]
    raw_scores = [d["raw_score"] for d in data]
    fd_active = [d["fd_active"] for d in data]

    # Signal breakdown for tooltips
    signal_data = {
        "Breadth": [d["s1_breadth"] for d in data],
        "Valuation": [d["s2_valuation"] for d in data],
        "Credit": [d["s3_credit"] for d in data],
        "Sentiment": [d["s4_sentiment"] for d in data],
        "Macro": [d["s5_macro"] for d in data],
        "Leverage": [d["s6_leverage"] for d in data],
        "Term Premium": [d["s7_term_premium"] for d in data],
    }

    # Key market events for annotations
    events = [
        {"date": "2007-10", "label": "GFC Begins", "color": "#e74c3c"},
        {"date": "2008-09", "label": "Lehman", "color": "#e74c3c"},
        {"date": "2009-03", "label": "Market Bottom", "color": "#27ae60"},
        {"date": "2011-08", "label": "US Downgrade", "color": "#e67e22"},
        {"date": "2015-08", "label": "China Deval", "color": "#e67e22"},
        {"date": "2018-12", "label": "Fed Pivot", "color": "#e67e22"},
        {"date": "2020-03", "label": "COVID Crash", "color": "#e74c3c"},
        {"date": "2021-11", "label": "Peak Bubble", "color": "#e74c3c"},
        {"date": "2022-01", "label": "Rate Hikes Begin", "color": "#e67e22"},
        {"date": "2025-01", "label": "Fiscal Dominance", "color": "#9b59b6"},
    ]

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Market Topping Regime Score - 20 Year History</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3.1.0/dist/chartjs-plugin-annotation.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #0a0e17;
    color: #e0e0e0;
    padding: 20px;
  }}
  h1 {{
    text-align: center;
    font-size: 1.6rem;
    margin-bottom: 5px;
    color: #fff;
  }}
  .subtitle {{
    text-align: center;
    font-size: 0.85rem;
    color: #888;
    margin-bottom: 20px;
  }}
  .chart-container {{
    position: relative;
    width: 100%;
    max-width: 1400px;
    margin: 0 auto;
    height: 500px;
  }}
  .signal-charts {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
    gap: 16px;
    max-width: 1400px;
    margin: 30px auto 0;
  }}
  .signal-chart-box {{
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 8px;
    padding: 12px;
  }}
  .signal-chart-box h3 {{
    font-size: 0.85rem;
    color: #9ca3af;
    margin-bottom: 8px;
  }}
  .signal-chart-inner {{
    height: 180px;
  }}
  .legend-bar {{
    display: flex;
    justify-content: center;
    gap: 24px;
    margin: 16px 0;
    flex-wrap: wrap;
  }}
  .legend-item {{
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.8rem;
    color: #9ca3af;
  }}
  .legend-swatch {{
    width: 14px;
    height: 14px;
    border-radius: 3px;
  }}
  .fd-indicator {{
    max-width: 1400px;
    margin: 20px auto 0;
    background: #1a1025;
    border: 1px solid #6b21a8;
    border-radius: 8px;
    padding: 16px;
  }}
  .fd-indicator h3 {{
    color: #a855f7;
    margin-bottom: 8px;
  }}
  .fd-indicator p {{
    font-size: 0.85rem;
    color: #c4b5fd;
    line-height: 1.5;
  }}
</style>
</head>
<body>

<h1>Market Topping Regime Score</h1>
<p class="subtitle">7-Signal Composite with Fiscal Dominance Modifier &middot; Monthly &middot; Jan 2006 &ndash; Mar 2026</p>

<div class="legend-bar">
  <div class="legend-item"><div class="legend-swatch" style="background:#f59e0b"></div> Adjusted Score (with FD modifier)</div>
  <div class="legend-item"><div class="legend-swatch" style="background:rgba(245,158,11,0.25);border:1px dashed #f59e0b"></div> Raw Score</div>
  <div class="legend-item"><div class="legend-swatch" style="background:rgba(168,85,247,0.15);border:1px solid #7c3aed"></div> Fiscal Dominance Active</div>
  <div class="legend-item"><div class="legend-swatch" style="background:rgba(239,68,68,0.12)"></div> Extreme Zone (80+)</div>
  <div class="legend-item"><div class="legend-swatch" style="background:rgba(251,191,36,0.08)"></div> High Zone (60-80)</div>
</div>

<div class="chart-container">
  <canvas id="mainChart"></canvas>
</div>

<div class="fd-indicator">
  <h3>Fiscal Dominance Flag</h3>
  <p>When active (purple shading), the flag adds +10 to the composite score and reweights signals.
  Activates when 3 of 4 conditions are met: deficit &gt;5% GDP (non-recession), interest/revenue &gt;15%,
  Fed easing while inflation &gt;target, curve steepening with rising term premium.
  The flag was briefly active during 2009-2010 (post-crisis deficits) and became persistently active from late 2024
  as structural fiscal dominance emerged.</p>
</div>

<div class="signal-charts">
  <div class="signal-chart-box">
    <h3>Signal 1: Breadth Divergence &amp; Concentration Risk</h3>
    <div class="signal-chart-inner"><canvas id="chart_s1"></canvas></div>
  </div>
  <div class="signal-chart-box">
    <h3>Signal 2: Valuation (CAPE)</h3>
    <div class="signal-chart-inner"><canvas id="chart_s2"></canvas></div>
  </div>
  <div class="signal-chart-box">
    <h3>Signal 3: Credit Complacency (HY Spreads)</h3>
    <div class="signal-chart-inner"><canvas id="chart_s3"></canvas></div>
  </div>
  <div class="signal-chart-box">
    <h3>Signal 4: Sentiment (VIX)</h3>
    <div class="signal-chart-inner"><canvas id="chart_s4"></canvas></div>
  </div>
  <div class="signal-chart-box">
    <h3>Signal 5: Macro Deterioration (ISM)</h3>
    <div class="signal-chart-inner"><canvas id="chart_s5"></canvas></div>
  </div>
  <div class="signal-chart-box">
    <h3>Signal 6: Margin Debt / Leverage</h3>
    <div class="signal-chart-inner"><canvas id="chart_s6"></canvas></div>
  </div>
  <div class="signal-chart-box">
    <h3>Signal 7: Term Premium / Fiscal Stress</h3>
    <div class="signal-chart-inner"><canvas id="chart_s7"></canvas></div>
  </div>
  <div class="signal-chart-box">
    <h3>Fiscal Dominance: Conditions Met (of 4)</h3>
    <div class="signal-chart-inner"><canvas id="chart_fd"></canvas></div>
  </div>
</div>

<script>
const dates = {json.dumps(dates)};
const scores = {json.dumps(scores)};
const rawScores = {json.dumps(raw_scores)};
const fdActive = {json.dumps(fd_active)};
const signalData = {json.dumps(signal_data)};
const fdConditions = {json.dumps([d["fd_conditions"] for d in data])};

const events = {json.dumps(events)};

// Build annotation objects for events
const annotations = {{}};
events.forEach((ev, i) => {{
  const idx = dates.indexOf(ev.date);
  if (idx >= 0) {{
    annotations['event' + i] = {{
      type: 'line',
      xMin: ev.date,
      xMax: ev.date,
      borderColor: ev.color,
      borderWidth: 1,
      borderDash: [4, 4],
      label: {{
        display: true,
        content: ev.label,
        position: i % 2 === 0 ? 'start' : 'end',
        backgroundColor: ev.color + '22',
        color: ev.color,
        font: {{ size: 10 }},
        padding: 3,
      }}
    }};
  }}
}});

// Zone bands
annotations['extremeZone'] = {{
  type: 'box',
  yMin: 80, yMax: 100,
  backgroundColor: 'rgba(239, 68, 68, 0.07)',
  borderWidth: 0,
}};
annotations['highZone'] = {{
  type: 'box',
  yMin: 60, yMax: 80,
  backgroundColor: 'rgba(251, 191, 36, 0.04)',
  borderWidth: 0,
}};

// Fiscal dominance shading: find contiguous blocks
let fdStart = null;
let fdIdx = 0;
for (let i = 0; i < fdActive.length; i++) {{
  if (fdActive[i] && fdStart === null) fdStart = i;
  if ((!fdActive[i] || i === fdActive.length - 1) && fdStart !== null) {{
    annotations['fd_' + fdIdx++] = {{
      type: 'box',
      xMin: dates[fdStart],
      xMax: dates[i],
      backgroundColor: 'rgba(168, 85, 247, 0.08)',
      borderColor: 'rgba(124, 58, 237, 0.3)',
      borderWidth: 1,
    }};
    fdStart = null;
  }}
}}

// Main chart
const mainCtx = document.getElementById('mainChart').getContext('2d');
new Chart(mainCtx, {{
  type: 'line',
  data: {{
    labels: dates,
    datasets: [
      {{
        label: 'Adjusted Score',
        data: scores,
        borderColor: '#f59e0b',
        backgroundColor: 'rgba(245, 158, 11, 0.1)',
        borderWidth: 2,
        fill: true,
        pointRadius: 0,
        pointHoverRadius: 4,
        tension: 0.3,
      }},
      {{
        label: 'Raw Score',
        data: rawScores,
        borderColor: 'rgba(245, 158, 11, 0.3)',
        borderWidth: 1,
        borderDash: [5, 5],
        fill: false,
        pointRadius: 0,
        pointHoverRadius: 3,
        tension: 0.3,
      }},
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    interaction: {{
      mode: 'index',
      intersect: false,
    }},
    scales: {{
      x: {{
        type: 'category',
        ticks: {{
          maxTicksLimit: 20,
          color: '#6b7280',
          font: {{ size: 11 }},
        }},
        grid: {{ color: 'rgba(75, 85, 99, 0.2)' }},
      }},
      y: {{
        min: 0,
        max: 100,
        ticks: {{
          stepSize: 10,
          color: '#6b7280',
          callback: v => v + '',
        }},
        grid: {{ color: 'rgba(75, 85, 99, 0.2)' }},
      }}
    }},
    plugins: {{
      legend: {{ display: false }},
      annotation: {{ annotations }},
      tooltip: {{
        backgroundColor: '#1f2937',
        titleColor: '#f9fafb',
        bodyColor: '#d1d5db',
        borderColor: '#374151',
        borderWidth: 1,
        callbacks: {{
          afterBody: function(context) {{
            const idx = context[0].dataIndex;
            const lines = [];
            if (fdActive[idx]) lines.push('\\n⚠ Fiscal Dominance ACTIVE');
            lines.push('');
            Object.entries(signalData).forEach(([name, vals]) => {{
              lines.push(name + ': ' + vals[idx]);
            }});
            return lines;
          }}
        }}
      }}
    }}
  }}
}});

// Signal sub-charts
const signalColors = {{
  'Breadth': '#3b82f6',
  'Valuation': '#ef4444',
  'Credit': '#f59e0b',
  'Sentiment': '#10b981',
  'Macro': '#8b5cf6',
  'Leverage': '#ec4899',
  'Term Premium': '#06b6d4',
}};

const signalKeys = Object.keys(signalData);
signalKeys.forEach((key, i) => {{
  const ctx = document.getElementById('chart_s' + (i + 1));
  if (!ctx) return;
  new Chart(ctx.getContext('2d'), {{
    type: 'line',
    data: {{
      labels: dates,
      datasets: [{{
        data: signalData[key],
        borderColor: signalColors[key],
        backgroundColor: signalColors[key] + '15',
        borderWidth: 1.5,
        fill: true,
        pointRadius: 0,
        tension: 0.3,
      }}]
    }},
    options: {{
      responsive: true,
      maintainAspectRatio: false,
      scales: {{
        x: {{
          ticks: {{ maxTicksLimit: 8, color: '#6b7280', font: {{ size: 9 }} }},
          grid: {{ display: false }},
        }},
        y: {{
          min: 0, max: 100,
          ticks: {{ stepSize: 25, color: '#6b7280', font: {{ size: 9 }} }},
          grid: {{ color: 'rgba(75, 85, 99, 0.15)' }},
        }}
      }},
      plugins: {{ legend: {{ display: false }}, tooltip: {{ enabled: true }} }},
    }}
  }});
}});

// FD conditions chart
const fdCtx = document.getElementById('chart_fd').getContext('2d');
new Chart(fdCtx, {{
  type: 'bar',
  data: {{
    labels: dates,
    datasets: [{{
      data: fdConditions,
      backgroundColor: fdConditions.map(c => c >= 3 ? '#7c3aed' : '#374151'),
      borderWidth: 0,
      barPercentage: 1.0,
      categoryPercentage: 1.0,
    }}]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    scales: {{
      x: {{
        ticks: {{ maxTicksLimit: 8, color: '#6b7280', font: {{ size: 9 }} }},
        grid: {{ display: false }},
      }},
      y: {{
        min: 0, max: 4,
        ticks: {{ stepSize: 1, color: '#6b7280', font: {{ size: 9 }} }},
        grid: {{ color: 'rgba(75, 85, 99, 0.15)' }},
      }}
    }},
    plugins: {{
      legend: {{ display: false }},
      annotation: {{
        annotations: {{
          threshold: {{
            type: 'line',
            yMin: 3, yMax: 3,
            borderColor: '#a855f7',
            borderWidth: 1,
            borderDash: [4, 4],
            label: {{
              display: true,
              content: 'Activation Threshold',
              position: 'end',
              color: '#a855f7',
              font: {{ size: 9 }},
              backgroundColor: 'transparent',
            }}
          }}
        }}
      }}
    }},
  }}
}});
</script>

</body>
</html>"""

    with open(output_path, "w") as f:
        f.write(html)

    return output_path


if __name__ == "__main__":
    path = generate_chart_html()
    print(f"Chart generated: {path}")
