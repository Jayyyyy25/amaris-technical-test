"""Food category classification for the Food Analysis page."""
from __future__ import annotations

_KEYWORDS: dict[str, list[str]] = {
    "Bakery": [
        "muffin", "scone", "croissant", "cake", "cookie", "brownie",
        "danish", "doughnut", "donut", "pound", "loaf", "biscotti",
        "bar", "roll", "bread", "pop", "pretzel", "strudel",
    ],
    "Breakfast": [
        "egg", "bagel", "oatmeal", "parfait", "yogurt", "bacon",
        "sausage", "ham", "morning", "breakfast", "frittata", "waffle",
    ],
    "Lunch & Bowls": [
        "sandwich", "panini", "wrap", "salad", "bowl", "soup",
        "box", "chicken", "tuna", "turkey", "protein", "lunch",
        "bistro", "bento",
    ],
}

CATEGORY_COLORS: dict[str, str] = {
    "Bakery":        "#f59e0b",
    "Breakfast":     "#3b82f6",
    "Lunch & Bowls": "#10b981",
    "Others":        "#8b5cf6",
}

PILL_MAP: dict[str, str] = {
    "🥐 Bakery":        "Bakery",
    "🍳 Breakfast":     "Breakfast",
    "🥗 Lunch & Bowls": "Lunch & Bowls",
    "🍽 Others":        "Others",
}


def assign(name: str) -> str:
    """Return the food category for a given item name."""
    name_lower = name.lower()
    for cat, keywords in _KEYWORDS.items():
        if any(kw in name_lower for kw in keywords):
            return cat
    return "Others"
