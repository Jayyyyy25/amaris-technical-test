"""
Console page — ChatGPT-style natural language Q&A over menu data.
"""

from __future__ import annotations

import streamlit as st

from src.summarizer import answer_query


_EXAMPLES = [
    "What is the highest calorie food item?",
    "Which drinks have the most sodium?",
    "What are the top 5 lowest-calorie drinks?",
    "Which food item has the most protein?",
    "How do average calories compare between drinks and food?",
    "Is there any caffeine data available?",
    "Which drink category has the highest average calories?",
    "What food items have more than 20g of protein?",
]


def render() -> None:
    st.header("Console")
    st.caption("Ask anything about the Starbucks menu in plain English.")

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

    # ── Initialise chat history ───────────────────────────────────────────────
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # ── Example question pills ────────────────────────────────────────────────
    with st.expander("Example questions", expanded=not st.session_state.chat_history):
        cols = st.columns(2)
        for i, q in enumerate(_EXAMPLES):
            if cols[i % 2].button(q, key=f"ex_{i}", use_container_width=True):
                st.session_state._pending_question = q

    # ── Render chat history ───────────────────────────────────────────────────
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── Handle pending question from example button ───────────────────────────
    pending = st.session_state.pop("_pending_question", None)

    # ── Chat input ────────────────────────────────────────────────────────────
    user_input = st.chat_input("Ask a question about the menu…")
    question   = user_input or pending

    if question:
        # Display user message
        with st.chat_message("user"):
            st.markdown(question)
        st.session_state.chat_history.append({"role": "user", "content": question})

        # Generate and display assistant reply
        with st.chat_message("assistant"):
            with st.spinner("Thinking…"):
                try:
                    answer = answer_query(groq_client, question, drinks_df, food_df)
                except RuntimeError as exc:
                    answer = f"Error: {exc}"
            st.markdown(answer)

        st.session_state.chat_history.append({"role": "assistant", "content": answer})

    # ── Clear chat button ─────────────────────────────────────────────────────
    if st.session_state.chat_history:
        if st.button("Clear conversation", use_container_width=False):
            st.session_state.chat_history = []
            st.rerun()
