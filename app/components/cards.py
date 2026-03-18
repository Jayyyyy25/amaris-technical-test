"""Shared metric card HTML component."""
from __future__ import annotations


def metric_card(
    title: str,
    icon: str,
    value: str,
    unit: str,
    note: str = "",
    note_positive: bool = True,
) -> str:
    delta_cls = "metric-delta-pos" if note_positive else "metric-delta-neu"
    note_html = f'<div class="{delta_cls}">{note}</div>' if note else ""
    return f"""
<div class="metric-card">
  <div class="metric-card-title">{title}<span class="metric-card-icon">{icon}</span></div>
  <div class="metric-values">
    <div class="metric-col">
      <span class="metric-value">{value}<span class="metric-unit"> {unit}</span></span>
    </div>
  </div>
  {note_html}
</div>
"""
