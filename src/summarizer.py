"""
Summarizer

Builds a structured ``menu_statistics`` dict from DataFrame statistics and
constructs prompts for two distinct features:

1. generate_summary()  — one-shot nutritional narrative covering both datasets
2. answer_query()      — natural-language Q&A grounded in the injected context

Neither function performs any data I/O; they receive clean DataFrames and
delegate all API calls to :class:`~src.llm_client.GroqClient`.
"""

from __future__ import annotations

import json

import pandas as pd

from src.llm_client import GroqClient
from src.data_processor import compute_derived_stats


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_BRIEF_SUMMARY_SYSTEM_PROMPT = """
You are a nutrition analyst specialising in Starbucks menu items.

You will be given a JSON format aggregated nutrition statistics describing the full Starbucks menu, including both beverages and food.

Your task is to generate a VERY concise whole-menu nutrition summary.

Requirements:
- Write ONLY 4-5 sentences.
- Describe overall calorie density patterns across drinks and food.
- Mention major sugar / fat drivers.
- Identify generally healthier categories vs indulgent categories.
- Mention that customization or portion size affects nutrition impact.
- Focus on high-level patterns, not specific menu items.
- Do not use bullet points or lists.
- Do not give generic health advice.
- Caffeine data is NOT available, so do NOT mention it.
- Do NOT invent data not present in the context.

Output:
A single short paragraph summary.
""".strip()

_SUMMARY_SYSTEM_PROMPT = """
You are a nutrition analyst specialising in Starbucks menu items.

You will be given a JSON format aggregated nutrition statistics describing the full Starbucks menu, including both beverages and food.

Your task is to generate a structured and practical nutrition insight summary for the WHOLE MENU.

Format your response with these sections:
## Overview
## Drinks Calorie and Sugar Patterns
## Food Nutrition Landscape
## Hidden Nutrition Insights and Model Findings (Compare deeper observations and include any important patterns detected by the model that may not be obvious from the raw stats alone)
## Health Recommendations & Decision Guidance (e.g. weight control, study energy, meal replacement, occasional treat)

Rules:
- Cover BOTH drinks and food categories.
- The summary must be informative but not overly long or academic (~250–350 words).
- Focus on explaining nutrition patterns and decision insights rather than listing specific menu items and their nutrition stats.
- Highlight surprising or notable findings (e.g., unusually high sodium, wide calorie ranges).
- Caffeine data is NOT available — do not mention or estimate it.
- Sugar is not directly measured; net carbs (carbs − fiber) is the available proxy — use that term when relevant.
- Do NOT invent any data not present in the context.
- Keep the tone professional but accessible.
- Use bullet points where appropriate.
""".strip()

_QUERY_SYSTEM_PROMPT_TEMPLATE = """
You are an expert Starbucks Nutrition Analyst and a helpful "AI Barista". 
Your job is to answer customer questions about the Starbucks menu accurately and concisely.

AVAILABLE DATA (JSON):
{context}

Conversation History:
{history}

Rules:
- Answer ONLY using the data above. Never hallucinate values or item names.
- Always refer to the history of the conversation to answer follow-up questions if the history is non-empty.
- If asked about caffeine, respond: "Caffeine data is not available in this dataset."
- If asked about sugar, clarify that direct sugar data is unavailable but net carbs (carbs − fiber) is the closest available proxy.
- If a question cannot be answered from the data, say so clearly.
- Be concise. Use bullet points for lists of items.
- Always cite specific numbers when available.
""".strip()


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def _top_n_records(
    df: pd.DataFrame,
    sort_col: str,
    fields: list[str],
    n: int,
    ascending: bool = False,
) -> list[dict]:
    """Return top-n rows as a list of dicts with only the specified fields."""
    if sort_col not in df.columns:
        return []
    subset = [f for f in fields if f in df.columns]
    top = (
        df.dropna(subset=[sort_col])
        .sort_values(sort_col, ascending=ascending)
        .head(n)[subset]
    )
    records = []
    for _, row in top.iterrows():
        record = {}
        for f in subset:
            val = row[f]
            record[f] = round(float(val), 1) if isinstance(val, float) else val
        records.append(record)
    return records


def build_menu_statistics(
    drinks_df: pd.DataFrame,
    food_df: pd.DataFrame,
    top_n: int = 5,
) -> dict:
    """
    Build a structured ``menu_statistics`` dict from both DataFrames.

    The dict is designed to be JSON-serialized and injected into LLM prompts.
    It includes per-dataset averages, calorie ranges, ranked item lists, derived
    ratios, and cross-dataset comparisons.

    Parameters
    ----------
    drinks_df:
        Cleaned drinks DataFrame.
    food_df:
        Cleaned food DataFrame.
    top_n:
        Number of items to include in each ranked list.

    Returns
    -------
    dict
        Structured statistics ready for ``json.dumps()``.
    """
    stats: dict = {}

    # ── Drinks ──────────────────────────────────────────────────────────────
    d = drinks_df.copy()
    d_derived = compute_derived_stats(d)
    n_imputed = int(d["is_imputed"].sum()) if "is_imputed" in d.columns else 0

    if "carb_g" in d.columns and "fiber_g" in d.columns:
        d["net_carbs_g"] = (d["carb_g"] - d["fiber_g"]).clip(lower=0).round(1)

    drinks_stats: dict = {
        "menu_size": len(d),
        "imputed_count": n_imputed,
    }

    for col, key in [("calories", "average_calories"), ("fat_g", "average_fat_g"),
                     ("protein_g", "average_protein_g"), ("sodium_mg", "average_sodium_mg")]:
        if col in d.columns:
            drinks_stats[key] = round(float(d[col].mean(skipna=True)), 1)

    if "calories" in d.columns:
        drinks_stats["calorie_range"] = {
            "min": round(float(d["calories"].min(skipna=True)), 1),
            "max": round(float(d["calories"].max(skipna=True)), 1),
        }

    if "net_carbs_g" in d.columns:
        drinks_stats["average_net_carbs_g"] = round(float(d["net_carbs_g"].mean(skipna=True)), 1)
        drinks_stats["highest_sugar_traps_by_net_carbs"] = _top_n_records(
            d, "net_carbs_g", ["item_name", "category", "net_carbs_g", "calories"], top_n,
        )
        drinks_stats["safest_low_carb_options"] = _top_n_records(
            d, "net_carbs_g", ["item_name", "category", "net_carbs_g", "calories"], top_n,
            ascending=True,
        )

    if "calories" in d.columns:
        drinks_stats["highest_calorie_drinks"] = _top_n_records(
            d, "calories", ["item_name", "category", "calories", "fat_g", "net_carbs_g"], top_n,
        )

    if "sodium_mg" in d.columns:
        drinks_stats["highest_sodium_drinks"] = _top_n_records(
            d, "sodium_mg", ["item_name", "category", "sodium_mg", "calories"], top_n,
        )

    if "category" in d.columns and "calories" in d.columns:
        drinks_stats["avg_calories_by_category"] = (
            d.groupby("category")["calories"]
            .mean()
            .sort_values(ascending=False)
            .round(1)
            .to_dict()
        )

    if "fat_to_protein_ratio" in d_derived:
        drinks_stats["avg_fat_to_protein_ratio"] = d_derived["fat_to_protein_ratio"]
    if "carb_to_protein_ratio" in d_derived:
        drinks_stats["avg_carb_to_protein_ratio"] = d_derived["carb_to_protein_ratio"]

    stats["drinks_analysis"] = drinks_stats

    # ── Food ────────────────────────────────────────────────────────────────
    f = food_df.copy()
    f_derived = compute_derived_stats(f)

    food_stats: dict = {"menu_size": len(f)}

    for col, key in [("calories", "average_calories"), ("fat_g", "average_fat_g"),
                     ("protein_g", "average_protein_g"), ("fiber_g", "average_fiber_g")]:
        if col in f.columns:
            food_stats[key] = round(float(f[col].mean(skipna=True)), 1)

    if "calories" in f.columns:
        food_stats["calorie_range"] = {
            "min": round(float(f["calories"].min(skipna=True)), 1),
            "max": round(float(f["calories"].max(skipna=True)), 1),
        }

    if all(c in f.columns for c in ("protein_g", "fiber_g", "calories")):
        satiety = (
            (f["protein_g"] + f["fiber_g"])
            / f["calories"].replace(0, float("nan"))
            * 100
        ).dropna()
        food_stats["avg_satiety_score"] = round(float(satiety.mean()), 1)

    if "calories" in f.columns:
        food_stats["most_calorie_dense_items"] = _top_n_records(
            f, "calories", ["item_name", "calories", "fat_g", "protein_g"], top_n,
        )
        food_stats["lowest_calorie_items"] = _top_n_records(
            f, "calories", ["item_name", "calories", "protein_g"], top_n, ascending=True,
        )

    if "protein_g" in f.columns:
        food_stats["highest_satiety_efficiency_items"] = _top_n_records(
            f, "protein_g", ["item_name", "protein_g", "fiber_g", "calories"], top_n,
        )

    if "fat_g" in f.columns and "protein_g" in f.columns:
        ratio_df = f[["item_name", "fat_g", "protein_g", "calories"]].dropna()
        ratio_df = ratio_df[ratio_df["protein_g"] > 0].copy()
        ratio_df["fat_protein_ratio"] = (ratio_df["fat_g"] / ratio_df["protein_g"]).round(2)
        food_stats["worst_fat_to_protein_ratio_items"] = [
            {
                "item": row["item_name"],
                "ratio": row["fat_protein_ratio"],
                "calories": round(row["calories"], 1),
                "protein_g": round(row["protein_g"], 1),
            }
            for _, row in ratio_df.sort_values("fat_protein_ratio", ascending=False).head(top_n).iterrows()
        ]

    if "fat_to_protein_ratio" in f_derived:
        food_stats["avg_fat_to_protein_ratio"] = f_derived["fat_to_protein_ratio"]

    stats["food_analysis"] = food_stats

    # ── Comparative insights ─────────────────────────────────────────────────
    comparative: dict = {}

    if "calories" in drinks_df.columns and "calories" in food_df.columns:
        d_avg = round(float(drinks_df["calories"].mean(skipna=True)), 1)
        f_avg = round(float(food_df["calories"].mean(skipna=True)), 1)
        diff  = round(f_avg - d_avg, 1)
        comparative["avg_calories_drinks"]           = d_avg
        comparative["avg_calories_food"]             = f_avg
        comparative["food_vs_drink_avg_calorie_diff"] = (
            f"+{diff} calories in food" if diff >= 0 else f"{diff} calories in food"
        )
        comparative["worst_case_combo_calories"] = int(
            drinks_df["calories"].max(skipna=True) + food_df["calories"].max(skipna=True)
        )

    for col, d_key, f_key in [
        ("protein_g", "avg_protein_drinks_g", "avg_protein_food_g"),
        ("fat_g",     "avg_fat_drinks_g",     "avg_fat_food_g"),
    ]:
        if col in drinks_df.columns and col in food_df.columns:
            comparative[d_key] = round(float(drinks_df[col].mean(skipna=True)), 1)
            comparative[f_key] = round(float(food_df[col].mean(skipna=True)), 1)

    stats["comparative_insights"] = comparative
    stats["data_notes"] = [
        "Caffeine data is not available in this dataset.",
        "Direct sugar data is not available; net carbs (carbs − fiber) is used as a proxy.",
        f"Drinks: {n_imputed} items had missing values filled via category-based median imputation.",
    ]

    return stats


# ---------------------------------------------------------------------------
# Public features
# ---------------------------------------------------------------------------

def generate_brief_summary(
    client: GroqClient,
    drinks_df: pd.DataFrame,
    food_df: pd.DataFrame,
) -> str:
    """Generate a single-paragraph headline summary for the dashboard."""
    context = json.dumps(build_menu_statistics(drinks_df, food_df, top_n=3), indent=2)
    return client.complete(
        system_prompt=_BRIEF_SUMMARY_SYSTEM_PROMPT,
        user_message=context,
        temperature=0.4,
        max_tokens=300,
    )


def generate_summary(
    client: GroqClient,
    drinks_df: pd.DataFrame,
    food_df: pd.DataFrame,
) -> str:
    """Generate a structured nutritional insight report for both datasets."""
    context = json.dumps(build_menu_statistics(drinks_df, food_df, top_n=5), indent=2)
    return client.complete(
        system_prompt=_SUMMARY_SYSTEM_PROMPT,
        user_message=context,
        temperature=0.4,
        max_tokens=1500,
    )


def answer_query_with_history(
    client: GroqClient,
    history: list[dict[str, str]],
    drinks_df: pd.DataFrame,
    food_df: pd.DataFrame,
) -> str:
    """Answer using full conversation history so follow-up questions work.

    Parameters
    ----------
    client:
        Configured :class:`~src.llm_client.GroqClient` instance.
    history:
        All turns so far as ``[{"role": "user"|"assistant", "content": "..."}]``.
        The latest user message must already be appended before calling this.
    drinks_df:
        Cleaned drinks DataFrame.
    food_df:
        Cleaned food DataFrame.
    """
    context          = json.dumps(build_menu_statistics(drinks_df, food_df, top_n=8), indent=2)
    prior_turns      = history[:-1]   # all turns except the latest user question
    current_question = history[-1]["content"] if history else ""
    system_prompt    = _QUERY_SYSTEM_PROMPT_TEMPLATE.format(
        context=context,
        history=json.dumps(prior_turns, indent=2),
    )
    return client.complete(
        system_prompt=system_prompt,
        user_message=current_question,
        temperature=0.3,
        max_tokens=1024,
    )
