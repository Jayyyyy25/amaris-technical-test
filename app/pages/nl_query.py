"""
Natural Language Q&A page — conversational Q&A with session memory.
"""

from __future__ import annotations

import json

import streamlit as st

from src.summarizer import answer_query_with_history, build_menu_statistics


_EXAMPLE_QUESTIONS = [
    "What is the highest calorie food item?",
    "Which drinks have the most sodium?",
    "What are the top 5 lowest-calorie drinks?",
    "Which food item has the most protein?",
    "How do average calories compare between drinks and food?",
    "What is the average fat content for drinks?",
    "Which drink category has the highest average calories?",
    "Is there any caffeine data available?",
]


def render() -> None:
    drinks_df   = st.session_state.get("drinks_df")
    food_df     = st.session_state.get("food_df")
    groq_client = st.session_state.get("groq_client")

    if drinks_df is None or food_df is None:
        st.info("Load the datasets using the sidebar first.")
        return

    if groq_client is None or not groq_client.is_available():
        st.warning(
            "LLM is not connected. Add your `GROQ_API_KEY` to `.env` "
            "or enter it in the sidebar and click **Connect LLM**."
        )
        return

    # ── Header ───────────────────────────────────────────────────────────────
    st.markdown(
        '<h2 style="margin:0 0 4px 0;font-size:26px;font-weight:800;color:#1a1a1a;">'
        'Ask a Question</h2>',
        unsafe_allow_html=True,
    )
    st.caption(
        "Ask anything about the Starbucks menu — follow-up questions are supported. "
        "Answers are grounded in computed dataset statistics."
    )

    # ── Session chat history ──────────────────────────────────────────────────
    if "nl_chat_history" not in st.session_state:
        st.session_state["nl_chat_history"] = []

    history: list[dict[str, str]] = st.session_state["nl_chat_history"]

    # ── Top bar: examples + clear ─────────────────────────────────────────────
    top_l, top_r = st.columns([5, 1], vertical_alignment="bottom")

    with top_l:
        with st.expander("💡 Example questions"):
            cols = st.columns(2)
            for i, q in enumerate(_EXAMPLE_QUESTIONS):
                if cols[i % 2].button(q, key=f"eg_{i}", use_container_width=True):
                    st.session_state["nl_prefill"] = q
                    st.rerun()

    with top_r:
        if st.button("🗑 Clear chat", use_container_width=True, disabled=not history):
            st.session_state["nl_chat_history"] = []
            st.rerun()

    # ── Render existing turns ─────────────────────────────────────────────────
    for msg in history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Chat input ────────────────────────────────────────────────────────────
    prefill  = st.session_state.pop("nl_prefill", "")
    question = st.chat_input("Ask a question about the menu…")

    if not question and prefill:
        question = prefill

    if question:
        with st.chat_message("user"):
            st.markdown(question)
        history.append({"role": "user", "content": question})

        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    answer = answer_query_with_history(
                        groq_client, history, drinks_df, food_df
                    )
                except RuntimeError as exc:
                    st.error(str(exc))
                    history.pop()
                    return
            st.markdown(answer)

        history.append({"role": "assistant", "content": answer})

    # ── Context expander ──────────────────────────────────────────────────────
    if history:
        with st.expander("🔍 View context sent to LLM"):
            ctx = json.dumps(build_menu_statistics(drinks_df, food_df, top_n=8), indent=2)
            st.code(ctx, language="json")
            st.caption(f"{len(ctx)} characters · ~{len(ctx) // 4} tokens (estimated)")
