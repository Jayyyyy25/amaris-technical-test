"""
Streamlit entry point.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Starbucks Nutrition Analyzer",
    page_icon="☕",
    layout="wide",
    initial_sidebar_state="expanded",
)

_ROOT           = Path(__file__).parent.parent
_DEFAULT_DRINKS = _ROOT / "data" / "starbucks-menu-nutrition-drinks.csv"
_DEFAULT_FOOD   = _ROOT / "data" / "starbucks-menu-nutrition-food.csv"

# ---------------------------------------------------------------------------
# Minimal sidebar CSS — clean white background, styled nav links
# ---------------------------------------------------------------------------

_css_path = Path(__file__).parent / "static" / "styles.css"
st.markdown(f"<style>{_css_path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

def _init_state() -> None:
    for key, val in {
        "drinks_df":     None,
        "food_df":       None,
        "groq_client":   None,
        "llm_summary":   None,
        "brief_summary": None,
        "chat_history":  [],
    }.items():
        if key not in st.session_state:
            st.session_state[key] = val

# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def _load_data(drinks_src, food_src) -> None:
    from src.data.loader import load_csv
    from src.data.cleaner import clean_dataset
    try:
        st.session_state.drinks_df     = clean_dataset(load_csv(drinks_src, "drinks"), "drinks")
        st.session_state.food_df       = clean_dataset(load_csv(food_src,   "food"),   "food")
        st.session_state.llm_summary   = None
        st.session_state.brief_summary = None
    except Exception as exc:
        st.error(f"Failed to load data: {exc}")


# ---------------------------------------------------------------------------
# Sidebar — settings only
# ---------------------------------------------------------------------------

def _render_sidebar() -> None:
    with st.sidebar:
        data_ok = st.session_state.drinks_df is not None
        llm_ok  = (st.session_state.groq_client is not None
                   and st.session_state.groq_client.is_available())
        st.caption(
            ("✅" if data_ok else "❌") + " Data  ·  " +
            ("✅" if llm_ok  else "⚠️") + " LLM"
        )

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

_init_state()

from app.pages import dashboard, drinks, food, console, settings  # noqa: E402

_PAGES = [
    st.Page(dashboard.render,  title="Dashboard",       icon="📊", url_path="dashboard",  default=True),
    st.Page(drinks.render,     title="Drinks Analysis", icon="🥤", url_path="drinks"),
    st.Page(food.render,       title="Food Analysis",   icon="🥗", url_path="food"),
    st.Page(console.render,    title="Ask the Menu",    icon="💬", url_path="console"),
    st.Page(settings.render,   title="Settings",        icon="⚙️",  url_path="settings"),
]

pg = st.navigation(_PAGES)

if st.session_state.drinks_df is None and _DEFAULT_DRINKS.exists() and _DEFAULT_FOOD.exists():
    with st.spinner("Loading datasets…"):
        _load_data(_DEFAULT_DRINKS, _DEFAULT_FOOD)

if st.session_state.groq_client is None:
    from src.llm.client import GroqClient
    auto = GroqClient()
    if auto.is_available():
        st.session_state.groq_client = auto

_render_sidebar()
pg.run()
