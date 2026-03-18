"""Singapore Nutri-Grade scoring for beverages.

Adapted from the HPB standard; thresholds are scaled to a ~350 ml reference
serving since per-100ml volume data is unavailable.
Sugar proxy = net carbs (carbs − fiber).  Saturated fat proxied by total fat.
Final grade = worst of the sugar grade and the fat grade.
"""
from __future__ import annotations

import pandas as pd

GRADE_STYLE: dict[str, str] = {
    "A": "background-color: #00803D; color: #ffffff; font-weight: 700; border-radius: 4px; text-align: center",
    "B": "background-color: #86BC25; color: #ffffff; font-weight: 700; border-radius: 4px; text-align: center",
    "C": "background-color: #F7A833; color: #ffffff; font-weight: 700; border-radius: 4px; text-align: center",
    "D": "background-color: #B71918; color: #ffffff; font-weight: 700; border-radius: 4px; text-align: center",
}


def _sugar_grade(net_carb_g: float) -> str:
    if net_carb_g <= 3.5:  return "A"   # ≤ 1 g/100 ml × 3.5
    if net_carb_g <= 17.5: return "B"   # ≤ 5 g/100 ml × 3.5
    if net_carb_g <= 35:   return "C"   # ≤ 10 g/100 ml × 3.5
    return "D"


def _fat_grade(fat_g: float) -> str:
    if fat_g <= 2.45: return "A"        # ≤ 0.7 g/100 ml × 3.5
    if fat_g <= 4.2:  return "B"        # ≤ 1.2 g/100 ml × 3.5
    if fat_g <= 9.8:  return "C"        # ≤ 2.8 g/100 ml × 3.5
    return "D"


def score(row: pd.Series) -> str:
    """Return the Nutri-Grade (A–D) for a single drink row."""
    net_carb = max(float(row.get("carb_g") or 0) - float(row.get("fiber_g") or 0), 0)
    fat      = float(row.get("fat_g") or 0)
    return max(_sugar_grade(net_carb), _fat_grade(fat))
