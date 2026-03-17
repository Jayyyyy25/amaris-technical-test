"""
LLM Insights page — AI-generated nutritional summary report.
"""

from __future__ import annotations

import streamlit as st

from src.summarizer import generate_summary, build_context_block


def render() -> None:
    st.header("🧠 LLM Nutritional Insights")

    drinks_df    = st.session_state.get("drinks_df")
    food_df      = st.session_state.get("food_df")
    groq_client  = st.session_state.get("groq_client")

    if drinks_df is None or food_df is None:
        st.info("Load the datasets using the sidebar first.")
        return

    if groq_client is None or not groq_client.is_available():
        st.warning(
            "LLM is not connected. Add your `GROQ_API_KEY` to `.env` "
            "or enter it in the sidebar and click **Connect LLM**."
        )
        return

    st.markdown(
        "Click **Generate Summary** to have the LLM produce a structured "
        "nutritional analysis report grounded in the actual dataset statistics."
    )

    col_btn, col_dl = st.columns([2, 1])

    if col_btn.button("🔄 Generate Summary", use_container_width=True):
        with st.spinner("Generating nutritional summary…"):
            try:
                st.session_state.llm_summary = generate_summary(
                    groq_client, drinks_df, food_df
                )
            except RuntimeError as exc:
                st.error(str(exc))
                return

    summary = st.session_state.get("llm_summary")

    if summary:
        st.divider()
        st.markdown(summary)

        col_dl.download_button(
            label="⬇️ Download",
            data=summary,
            file_name="starbucks_nutrition_summary.md",
            mime="text/markdown",
            use_container_width=True,
        )

        with st.expander("🔍 View context sent to LLM"):
            ctx = build_context_block(drinks_df, food_df)
            st.text(ctx)
            st.caption(f"{len(ctx)} characters · ~{len(ctx) // 4} tokens (estimated)")
    else:
        st.info("No summary generated yet. Click **Generate Summary** above.")
