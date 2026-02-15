"""Dashboard summary view for customer data — HTML output."""

import html
import logging
import os
import webbrowser
from collections import Counter
from datetime import datetime

logger = logging.getLogger(__name__)


def _pct(count: int, total: int) -> float:
    """Return percentage of count/total."""
    return count / total * 100 if total else 0.0


def _bar_html(count: int, total: int) -> str:
    """Render an HTML progress bar."""
    pct = _pct(count, total)
    return (
        f'<div class="bar-bg">'
        f'<div class="bar-fill" style="width:{pct:.1f}%"></div>'
        f'</div>'
    )


def _top_section_html(title: str, counter: Counter, total: int, limit: int = 10) -> str:
    """Build an HTML card with a ranked breakdown table."""
    rows = ""
    for value, count in counter.most_common(limit):
        label = html.escape(value) if value else "<em>(blank)</em>"
        pct = _pct(count, total)
        rows += (
            f"<tr>"
            f"<td class='label'>{label}</td>"
            f"<td class='num'>{count:,}</td>"
            f"<td class='num'>{pct:.1f}%</td>"
            f"<td class='bar-cell'>{_bar_html(count, total)}</td>"
            f"</tr>\n"
        )
    extra = ""
    if len(counter) > limit:
        extra = f"<p class='extra'>… and {len(counter) - limit} more</p>"

    return f"""
    <div class="card">
      <h2>{html.escape(title)}</h2>
      <table>
        <thead><tr><th>Name</th><th>Count</th><th>%</th><th></th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
      {extra}
    </div>"""


def _coverage_row_html(label: str, count: int, total: int) -> str:
    """Build a single coverage metric row."""
    pct = _pct(count, total)
    return (
        f"<tr>"
        f"<td class='label'>{html.escape(label)}</td>"
        f"<td class='num'>{count:,} / {total:,}</td>"
        f"<td class='num'>{pct:.1f}%</td>"
        f"<td class='bar-cell'>{_bar_html(count, total)}</td>"
        f"</tr>"
    )


def _build_html(customers: list[dict]) -> str:
    """Build the full HTML dashboard string."""
    total = len(customers)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Compute metrics
    group_counts = Counter(c.get("CustomerGroupId", "") or "" for c in customers)
    currency_counts = Counter(c.get("SalesCurrencyCode", "") or "" for c in customers)
    company_counts = Counter(c.get("DataAreaId", "") or "" for c in customers)
    has_email = sum(1 for c in customers if c.get("PrimaryContactEmail"))
    has_phone = sum(1 for c in customers if c.get("PrimaryContactPhone"))

    # Build sections
    group_section = _top_section_html("By Customer Group", group_counts, total)
    currency_section = _top_section_html("By Currency", currency_counts, total)
    company_section = _top_section_html("By Company", company_counts, total)

    coverage_rows = _coverage_row_html("Email", has_email, total)
    coverage_rows += _coverage_row_html("Phone", has_phone, total)
    coverage_section = f"""
    <div class="card">
      <h2>Contact Coverage</h2>
      <table>
        <thead><tr><th>Channel</th><th>Coverage</th><th>%</th><th></th></tr></thead>
        <tbody>{coverage_rows}</tbody>
      </table>
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>D365 F&amp;O Customer Dashboard</title>
<style>
  :root {{
    --primary: #0078d4;
    --primary-light: #deecf9;
    --bg: #f4f6f8;
    --card-bg: #ffffff;
    --text: #1a1a1a;
    --muted: #6b7280;
    --border: #e5e7eb;
    --bar-bg: #e5e7eb;
    --bar-fill: #0078d4;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.5;
    padding: 2rem;
  }}
  .header {{
    text-align: center;
    margin-bottom: 2rem;
  }}
  .header h1 {{
    font-size: 1.75rem;
    color: var(--primary);
    margin-bottom: 0.25rem;
  }}
  .header .subtitle {{
    color: var(--muted);
    font-size: 0.9rem;
  }}
  .kpi-row {{
    display: flex;
    gap: 1.5rem;
    justify-content: center;
    flex-wrap: wrap;
    margin-bottom: 2rem;
  }}
  .kpi {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.25rem 2rem;
    text-align: center;
    min-width: 160px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }}
  .kpi .value {{
    font-size: 2rem;
    font-weight: 700;
    color: var(--primary);
  }}
  .kpi .label {{
    color: var(--muted);
    font-size: 0.85rem;
    margin-top: 0.25rem;
  }}
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(420px, 1fr));
    gap: 1.5rem;
    max-width: 1200px;
    margin: 0 auto;
  }}
  .card {{
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 1.5rem;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
  }}
  .card h2 {{
    font-size: 1.1rem;
    margin-bottom: 1rem;
    color: var(--text);
    border-bottom: 2px solid var(--primary-light);
    padding-bottom: 0.5rem;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.9rem;
  }}
  thead th {{
    text-align: left;
    color: var(--muted);
    font-weight: 600;
    font-size: 0.8rem;
    text-transform: uppercase;
    padding: 0.4rem 0.5rem;
    border-bottom: 1px solid var(--border);
  }}
  tbody tr:hover {{
    background: var(--primary-light);
  }}
  td {{
    padding: 0.5rem 0.5rem;
    border-bottom: 1px solid #f0f0f0;
  }}
  td.label {{
    font-weight: 500;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  td.num {{
    text-align: right;
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }}
  td.bar-cell {{
    width: 35%;
  }}
  .bar-bg {{
    background: var(--bar-bg);
    border-radius: 4px;
    height: 18px;
    overflow: hidden;
  }}
  .bar-fill {{
    background: var(--bar-fill);
    height: 100%;
    border-radius: 4px;
    transition: width 0.3s ease;
  }}
  .extra {{
    color: var(--muted);
    font-size: 0.8rem;
    margin-top: 0.5rem;
    font-style: italic;
  }}
  .footer {{
    text-align: center;
    color: var(--muted);
    font-size: 0.8rem;
    margin-top: 2rem;
  }}
</style>
</head>
<body>

<div class="header">
  <h1>D365 F&amp;O Customer Dashboard</h1>
  <p class="subtitle">Generated {html.escape(now)}</p>
</div>

<div class="kpi-row">
  <div class="kpi">
    <div class="value">{total:,}</div>
    <div class="label">Total Customers</div>
  </div>
  <div class="kpi">
    <div class="value">{len(group_counts)}</div>
    <div class="label">Customer Groups</div>
  </div>
  <div class="kpi">
    <div class="value">{len(currency_counts)}</div>
    <div class="label">Currencies</div>
  </div>
  <div class="kpi">
    <div class="value">{_pct(has_email, total):.0f}%</div>
    <div class="label">Email Coverage</div>
  </div>
</div>

<div class="grid">
  {group_section}
  {currency_section}
  {company_section}
  {coverage_section}
</div>

<div class="footer">
  D365 F&amp;O Customer Management Tool &middot; {html.escape(now)}
</div>

</body>
</html>"""


def display_dashboard(customers: list[dict]) -> None:
    """Generate an HTML dashboard and open it in the default browser."""
    total = len(customers)

    if total == 0:
        print("  No customer data to display.\n")
        return

    html_content = _build_html(customers)

    # Write to a temp file that persists after closing
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "dashboard.html")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

    abs_path = os.path.abspath(output_path)
    print(f"\n📊 Dashboard generated: {abs_path}")

    try:
        webbrowser.open(f"file://{abs_path}")
        print("🌐 Opened in default browser.\n")
    except Exception:
        logger.warning("Could not open browser automatically.")
        print(f"   Open this file in your browser to view the dashboard.\n")
