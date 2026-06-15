import streamlit as st
import json
from src.db.executor import execute_sql_query
from src.planner.planner import (
    build_metadata_context,
    build_user_prompt,
    load_config,
    plan_query,
)

# --------------------------------------------------
# Streamlit Config
# --------------------------------------------------

st.set_page_config(
    page_title="Text2SQL Planner",
    layout="wide",
)

# --------------------------------------------------
# Initialize Planner
# --------------------------------------------------

try:
    load_config()
except Exception as e:
    st.error(str(e))
    st.stop()

# --------------------------------------------------
# UI
# --------------------------------------------------

st.title("Text2SQL Planner")

question = st.text_area(
    "Business Question",
    value="Top 5 sellers by revenue?",
    height=120,
)

show_metadata = st.checkbox(
    "Show Metadata Context"
)

if show_metadata:
    with st.expander("Metadata"):
        metadata_context, _ = build_metadata_context(question)
        st.code(
            metadata_context,
            language=None,
        )

if st.button(
    "Generate Query",
    use_container_width=True,
):
    if not question.strip():
        st.warning("Please enter a question.")
        st.stop()

    try:
        with st.spinner("Generating Query..."):
            plan, retrieval_metadata = plan_query(question)

        st.success("Query generated")

        # Show retrieval metadata if dynamic schema was used
        if retrieval_metadata.get("method") != "full":
            st.info(f"🔍 Schema Retrieval: {retrieval_metadata.get('method', 'unknown').upper()} | "
                   f"Confidence: {retrieval_metadata.get('confidence', 0):.2%} | "
                   f"Tables: {len(retrieval_metadata.get('tables_selected', []))}")

        st.subheader("Query")
        st.code(plan, language="sql")

        try:
            if plan:
                df = execute_sql_query(plan)
                if df.empty:
                    st.info("The SQL query returned no rows.")
                else:
                    st.subheader("Extracted Data")
                    st.dataframe(df)

                    if len(df) > 200:
                        st.caption(f"Showing first {min(len(df), 200)} rows.")
            else:
                st.error("Failed to extract SQL query from model response")
        except Exception as exec_error:
            st.error(f"Query execution failed: {exec_error}")

        with st.expander("Prompt Preview"):
            user_prompt, _ = build_user_prompt(question)
            st.text(user_prompt)

        with st.expander("Retrieval Metadata"):
            st.json(retrieval_metadata)

    except Exception as e:
        st.exception(e)