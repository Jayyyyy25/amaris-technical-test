"""
HTML component helpers.

All functions return plain HTML strings
No Streamlit import here; components stay framework-agnostic.
"""
from __future__ import annotations


# ---------------------------------------------------------------------------
# Generic layout helpers
# ---------------------------------------------------------------------------

def spacer(px: int = 24) -> str:
    return f"<div style='margin-top:{px}px'></div>"


def page_title(text: str) -> str:
    return (
        f'<h2 style="margin:0 0 4px 0;font-size:26px;font-weight:800;color:#1a1a1a;">'
        f'{text}</h2>'
    )


def section_heading(text: str) -> str:
    return (
        f'<h3 style="font-size:20px;font-weight:700;color:#1a1a1a;margin:0 0 8px 0;">'
        f'{text}</h3>'
    )


def filter_label(text: str) -> str:
    return f'<p class="filter-label">{text}</p>'


def chart_header(title: str, subtitle: str = "") -> str:
    sub_html = f'  <div class="chart-card-subtitle">{subtitle}</div>\n' if subtitle else ""
    return (
        f'<div class="chart-card">\n'
        f'  <div class="chart-card-title">{title}</div>\n'
        f'{sub_html}'
        f'</div>'
    )


# ---------------------------------------------------------------------------
# Dashboard — page header card
# ---------------------------------------------------------------------------

def page_header_card() -> str:
    return """
<div style="display:flex;align-items:center;gap:14px;
            padding:18px 24px;background:#ffffff;border:1px solid #e8eaed;
            border-radius:14px;margin-bottom:16px;">
  <div style="width:52px;height:52px;background:linear-gradient(135deg,#2c8451,#3ab26a);
              border-radius:14px;display:flex;align-items:center;justify-content:center;
              font-size:26px;flex-shrink:0;box-shadow:0 2px 8px rgba(42,136,72,0.25);">
    ☕
  </div>
  <div>
    <p style="margin:0;font-size:22px;font-weight:800;color:#1a1a1a;line-height:1.2;">
      Starbucks Nutrition Dashboard
    </p>
    <p style="margin:2px 0 0 0;font-size:13px;color:#6b7280;">
      Explore nutritional data across the full Starbucks menu
    </p>
  </div>
</div>
"""


def ai_ready_badge() -> str:
    return """
<div style="background:#f0faf5;color:#00704A;border:1px solid #b7dfc8;
            border-radius:20px;padding:6px 14px;font-size:12px;font-weight:600;
            text-align:center;white-space:nowrap;">
  ✦ AI Summary Ready
</div>"""


def ai_powered_badge() -> str:
    return """
<div style="background:#f9fafb;color:#9aa0a6;border:1px solid #e8eaed;
            border-radius:20px;padding:6px 14px;font-size:12px;font-weight:600;
            text-align:center;white-space:nowrap;">
  ✦ AI-Powered
</div>"""


# ---------------------------------------------------------------------------
# Dashboard — AI summary banner (three states)
# ---------------------------------------------------------------------------

def summary_banner_with_content(brief: str) -> str:
    return f"""
<div class="summary-banner">
  <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:16px;">
    <div style="flex:1;">
      <div class="summary-badge">✦ AI Summary</div>
      <p class="summary-title">Nutritional Snapshot</p>
      <p class="summary-text">{brief}</p>
    </div>
  </div>
</div>
"""


def summary_banner_prompt() -> str:
    return """
<div class="summary-banner">
  <div class="summary-badge">✦ AI Summary</div>
  <p class="summary-title">Nutritional Snapshot</p>
  <p class="summary-text" style="opacity:0.85;font-style:italic;">
    Click <strong>✦ Generate</strong> in the top-right to produce an AI-powered nutritional summary.
  </p>
</div>
"""


def summary_banner_disconnected() -> str:
    return """
<div class="summary-banner">
  <div class="summary-badge">✦ AI Summary</div>
  <p class="summary-title">Nutritional Snapshot</p>
  <p class="summary-text" style="opacity:0.7;font-style:italic;">
    Connect the LLM in the sidebar to generate an AI-powered nutritional summary.
  </p>
</div>
"""


# ---------------------------------------------------------------------------
# Drinks / Food pages — AI insight card
# ---------------------------------------------------------------------------

def insight_card(text: str) -> str:
    return f"""
<div class="insight-card">
  <div>
    <div class="insight-title">✦ AI Insights Summary</div>
    <p class="insight-text">{text}</p>
  </div>
</div>
"""
