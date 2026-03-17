"""
Summarizer

Builds the LLM context block from pre-computed DataFrame statistics and
constructs prompts for two distinct features:

1. generate_summary()  — one-shot nutritional narrative covering both datasets
2. answer_query()      — natural-language Q&A grounded in the injected context

Neither function performs any data I/O; they receive clean DataFrames and
delegate all API calls to :class:`~src.llm_client.GroqClient`.
"""

from __future__ import annotations

import pandas as pd

from src.llm_client import GroqClient
from src.data_processor import (
    compute_descriptive_stats,
    compute_cross_dataset_stats,
    compute_derived_stats,
    get_top_n,
    COLUMN_LABELS,
)


# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

_BRIEF_SUMMARY_SYSTEM_PROMPT = """
You are a professional nutritionist reviewing Starbucks menu data.
You will be given statistical data for both the drinks and food menus.

Write exactly ONE concise paragraph (4-6 sentences) that captures the most important
nutritional highlights across both datasets. Mention specific numbers and notable items.
Do NOT use headers, bullet points, or multiple paragraphs — plain prose only.
Caffeine and sugar data are NOT available — do not mention them.
Do NOT invent data not present in the context.
""".strip()

_SUMMARY_SYSTEM_PROMPT = """
You are a professional nutritionist and data analyst reviewing Starbucks menu data.
You will be given a structured statistical summary of both the drinks and food menus.

Your task is to produce a clear, engaging nutritional analysis report.

Format your response with these sections:
## Overview
## Drinks Analysis
## Food Analysis
## Drinks vs Food Comparison
## Health Recommendations

Rules:
- Support every claim with specific numbers from the data.
- Name specific menu items when they appear in the top/bottom rankings.
- Highlight surprising or notable findings (e.g., unusually high sodium, wide calorie ranges).
- Caffeine and sugar data are NOT available — do not mention or estimate them.
- Do NOT invent any data not present in the context.
- Keep the tone professional but accessible.
""".strip()

_QUERY_SYSTEM_PROMPT_TEMPLATE = """
You are a precise data analyst assistant with access to Starbucks menu nutritional data.

AVAILABLE DATA:
{context}

Rules:
- Answer ONLY using the data above. Never hallucinate values or item names.
- If asked about caffeine or sugar, respond: "Caffeine/sugar data is not available in this dataset."
- If a question cannot be answered from the data, say so clearly.
- Be concise. Use bullet points for lists of items.
- Always cite specific numbers when available.
""".strip()


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def build_context_block(
    drinks_df: pd.DataFrame,
    food_df: pd.DataFrame,
    top_n: int = 5,
) -> str:
    """Serialize dataset statistics into a compact, LLM-readable text block.

    Includes per-column stats, top/bottom-N items for key nutrients,
    cross-dataset comparison, derived ratios, and a note about absent columns.
    Designed to stay under ~1 200 tokens.

    Parameters
    ----------
    drinks_df:
        Cleaned drinks DataFrame.
    food_df:
        Cleaned food DataFrame.
    top_n:
        Number of top/bottom items to include per nutrient ranking.

    Returns
    -------
    str
        Multi-line context block ready for injection into a prompt.
    """
    lines: list[str] = []

    # ── Drinks ──────────────────────────────────────────────────────────
    d_stats   = compute_descriptive_stats(drinks_df)
    d_derived = compute_derived_stats(drinks_df)
    n_imputed = int(drinks_df["is_imputed"].sum()) if "is_imputed" in drinks_df.columns else 0

    lines.append(f"DRINKS DATASET ({len(drinks_df)} items, {n_imputed} with imputed values):")
    lines.append(_format_stats_block(d_stats))

    lines.append(f"  Fat-to-protein ratio (avg): {d_derived.get('fat_to_protein_ratio', 'N/A')}")
    lines.append(f"  Carb-to-protein ratio (avg): {d_derived.get('carb_to_protein_ratio', 'N/A')}")

    lines.append(f"\n  Top {top_n} highest-calorie drinks:")
    lines.append(_format_top_n(drinks_df, "calories", top_n, ascending=False))

    lines.append(f"\n  Top {top_n} lowest-calorie drinks:")
    lines.append(_format_top_n(drinks_df, "calories", top_n, ascending=True))

    lines.append(f"\n  Top {top_n} highest-sodium drinks:")
    lines.append(_format_top_n(drinks_df, "sodium_mg", top_n, ascending=False))

    if "category" in drinks_df.columns:
        lines.append("\n  Average calories by drink category:")
        cat_means = (
            drinks_df.groupby("category")["calories"]
            .mean()
            .sort_values(ascending=False)
            .round(1)
        )
        for cat, val in cat_means.items():
            lines.append(f"    {cat}: {val} kcal")

    # ── Food ────────────────────────────────────────────────────────────
    f_stats   = compute_descriptive_stats(food_df)
    f_derived = compute_derived_stats(food_df)

    lines.append(f"\nFOOD DATASET ({len(food_df)} items):")
    lines.append(_format_stats_block(f_stats))

    lines.append(f"  Fat-to-protein ratio (avg): {f_derived.get('fat_to_protein_ratio', 'N/A')}")
    lines.append(f"  Carb-to-protein ratio (avg): {f_derived.get('carb_to_protein_ratio', 'N/A')}")

    lines.append(f"\n  Top {top_n} highest-calorie food items:")
    lines.append(_format_top_n(food_df, "calories", top_n, ascending=False))

    lines.append(f"\n  Top {top_n} lowest-calorie food items:")
    lines.append(_format_top_n(food_df, "calories", top_n, ascending=True))

    lines.append(f"\n  Top {top_n} highest-protein food items:")
    lines.append(_format_top_n(food_df, "protein_g", top_n, ascending=False))

    # ── Cross-dataset ────────────────────────────────────────────────────
    cross = compute_cross_dataset_stats(drinks_df, food_df)
    lines.append("\nCROSS-DATASET COMPARISON (mean values):")
    for col, vals in cross.items():
        label = COLUMN_LABELS.get(col, col)
        lines.append(
            f"  {label}: drinks={vals['drinks_mean']}, food={vals['food_mean']}  "
            f"(food is {round(vals['food_mean'] / vals['drinks_mean'], 1)}× higher)"
            if vals["drinks_mean"] > 0
            else f"  {label}: drinks={vals['drinks_mean']}, food={vals['food_mean']}"
        )

    # ── Data limitations ─────────────────────────────────────────────────
    absent = d_derived.get("missing_columns", "")
    if absent:
        lines.append(f"\nNOTE: The following columns are absent from both datasets: {absent}.")
        lines.append("Do not reference or estimate these values.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public features
# ---------------------------------------------------------------------------

def generate_brief_summary(
    client: GroqClient,
    drinks_df: pd.DataFrame,
    food_df: pd.DataFrame,
) -> str:
    """Generate a single-paragraph headline summary for the dashboard."""
    context = build_context_block(drinks_df, food_df, top_n=3)
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
    """Generate a structured nutritional insight report for both datasets.

    Parameters
    ----------
    client:
        Configured :class:`~src.llm_client.GroqClient` instance.
    drinks_df:
        Cleaned drinks DataFrame.
    food_df:
        Cleaned food DataFrame.

    Returns
    -------
    str
        Markdown-formatted nutritional analysis.
    """
    context = build_context_block(drinks_df, food_df, top_n=5)
    return client.complete(
        system_prompt=_SUMMARY_SYSTEM_PROMPT,
        user_message=context,
        temperature=0.4,
        max_tokens=1500,
    )


def answer_query(
    client: GroqClient,
    question: str,
    drinks_df: pd.DataFrame,
    food_df: pd.DataFrame,
) -> str:
    """Answer a natural-language question about the menu data.

    The context block is injected into the system prompt so the LLM is
    grounded in actual computed statistics — it cannot hallucinate item
    names or values that are not present in the data.

    Parameters
    ----------
    client:
        Configured :class:`~src.llm_client.GroqClient` instance.
    question:
        Free-form user question (e.g. ``"What's the lowest-calorie drink?"``).
    drinks_df:
        Cleaned drinks DataFrame.
    food_df:
        Cleaned food DataFrame.

    Returns
    -------
    str
        The model's answer, grounded in the injected context.
    """
    context      = build_context_block(drinks_df, food_df, top_n=8)
    system_prompt = _QUERY_SYSTEM_PROMPT_TEMPLATE.format(context=context)
    return client.complete(
        system_prompt=system_prompt,
        user_message=question,
        temperature=0.1,   # low temp → factual, deterministic
        max_tokens=1024,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _format_stats_block(stats: dict[str, dict[str, float]]) -> str:
    """Format a stats dict as an indented multi-line string."""
    lines = []
    for col, s in stats.items():
        label = COLUMN_LABELS.get(col, col)
        lines.append(
            f"  {label}: mean={s['mean']}, median={s['median']}, "
            f"min={s['min']}, max={s['max']}, total={s['total']}"
        )
    return "\n".join(lines)


def _format_top_n(
    df: pd.DataFrame,
    column: str,
    n: int,
    ascending: bool,
) -> str:
    """Format top-N rows as a numbered list with item name and value."""
    if column not in df.columns:
        return "    (data not available)"
    label   = COLUMN_LABELS.get(column, column)
    top_df  = get_top_n(df, column, n=n, ascending=ascending)
    lines   = []
    for i, row in top_df.iterrows():
        name = row.get("item_name", "Unknown")
        val  = row.get(column, "N/A")
        lines.append(f"    {i + 1}. {name} — {val} {label}")
    return "\n".join(lines) if lines else "    (no data)"
