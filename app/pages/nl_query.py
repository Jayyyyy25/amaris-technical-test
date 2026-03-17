"""
Natural Language Q&A page — grounded question answering over menu data.
"""

from __future__ import annotations

import streamlit as st

from src.summarizer import answer_query, build_context_block


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
    st.header("💬 Ask a Question")

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

    st.markdown(
        "Ask any question about the Starbucks menu in plain English. "
        "The LLM answers using only the computed dataset statistics — it cannot hallucinate item names or values."
    )

    # ── Example questions ────────────────────────────────────────────────────
    with st.expander("💡 Example questions"):
        for q in _EXAMPLE_QUESTIONS:
            if st.button(q, key=f"eg_{q[:30]}"):
                st.session_state["nl_question"] = q

    # ── Question input ───────────────────────────────────────────────────────
    question = st.text_input(
        "Your question",
        value=st.session_state.get("nl_question", ""),
        placeholder="e.g. What is the lowest-calorie drink?",
        key="nl_question",
    )

    ask_btn = st.button("Ask", type="primary", use_container_width=False)

    if ask_btn and question.strip():
        with st.spinner("Thinking…"):
            try:
                answer = answer_query(groq_client, question, drinks_df, food_df)
            except RuntimeError as exc:
                st.error(str(exc))
                return

        st.divider()
        st.markdown(f"**Q:** {question}")
        st.markdown(f"**A:** {answer}")

        with st.expander("🔍 View context sent to LLM"):
            ctx = build_context_block(drinks_df, food_df, top_n=8)
            st.text(ctx)
            st.caption(f"{len(ctx)} characters · ~{len(ctx) // 4} tokens (estimated)")

    elif ask_btn:
        st.warning("Please enter a question.")
