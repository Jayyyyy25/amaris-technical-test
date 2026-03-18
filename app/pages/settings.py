"""
Settings page — data loading and LLM configuration.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_ROOT           = Path(__file__).parent.parent.parent
_DEFAULT_DRINKS = _ROOT / "data" / "starbucks-menu-nutrition-drinks.csv"
_DEFAULT_FOOD   = _ROOT / "data" / "starbucks-menu-nutrition-food.csv"


def _save_upload(uploaded, suffix: str) -> Path | None:
    if uploaded is None:
        return None
    import tempfile, shutil
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    with open(fd, "wb") as fh:
        shutil.copyfileobj(uploaded, fh)
    return Path(tmp_path)


def _load_data(drinks_src, food_src) -> None:
    from src.data.loader import load_csv
    from src.data.cleaner import clean_dataset
    try:
        st.session_state.drinks_df     = clean_dataset(load_csv(drinks_src, "drinks"), "drinks")
        st.session_state.food_df       = clean_dataset(load_csv(food_src,   "food"),   "food")
        st.session_state.llm_summary   = None
        st.session_state.brief_summary = None
        st.success(
            f"Loaded {len(st.session_state.drinks_df)} drinks and "
            f"{len(st.session_state.food_df)} food items."
        )
    except Exception as exc:
        st.error(f"Failed to load data: {exc}")


def render() -> None:
    st.header("Settings")

    # ── Datasets ─────────────────────────────────────────────────────────────
    st.subheader("Datasets")

    col_l, col_r = st.columns(2)

    with col_l:
        drinks_upload = st.file_uploader(
            "Drinks CSV", type=["csv"], key="drinks_upload",
            help="Leave empty to use the bundled dataset",
        )
    with col_r:
        food_upload = st.file_uploader(
            "Food CSV", type=["csv"], key="food_upload",
            help="Leave empty to use the bundled dataset",
        )

    drinks_src = _save_upload(drinks_upload, ".csv") if drinks_upload else _DEFAULT_DRINKS
    food_src   = _save_upload(food_upload,   ".csv") if food_upload   else _DEFAULT_FOOD

    if st.button("Load / Reload Data", type="primary"):
        with st.spinner("Loading and cleaning datasets…"):
            _load_data(drinks_src, food_src)

    # Current status
    if st.session_state.get("drinks_df") is not None:
        d = st.session_state.drinks_df
        f = st.session_state.food_df
        n_imputed = int(d["is_imputed"].sum()) if "is_imputed" in d.columns else 0
        st.info(
            f"Currently loaded: **{len(d)} drinks** ({n_imputed} imputed) "
            f"and **{len(f)} food items**."
        )
    else:
        st.warning("No data loaded yet.")

    st.divider()

    # ── LLM ──────────────────────────────────────────────────────────────────
    st.subheader("LLM Configuration")

    col_a, col_b = st.columns(2)

    with col_a:
        api_key = st.text_input(
            "Groq API Key",
            type="password",
            placeholder="Loaded from .env if blank",
            key="api_key_input",
        )
    with col_b:
        model = st.selectbox(
            "Model",
            ["llama-3.1-8b-instant", "llama-3.3-70b-versatile",
             "llama3-70b-8192", "gemma2-9b-it"],
            key="model_select",
        )

    if st.button("Connect LLM", type="primary"):
        from src.llm.client import GroqClient
        client = GroqClient(api_key=api_key or None, model=model)
        if client.is_available():
            st.session_state.groq_client = client
            st.session_state.llm_summary = None
            st.success(f"Connected to **{client.model}**.")
        else:
            st.error(
                "No API key found. Add `GROQ_API_KEY` to your `.env` file "
                "or enter it above."
            )

    groq_client = st.session_state.get("groq_client")
    if groq_client and groq_client.is_available():
        st.info(f"LLM connected: **{groq_client.model}**")
    else:
        st.warning("LLM not connected.")
