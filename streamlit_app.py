import streamlit as st
import json
from src.db.executor import execute_sql_query
from src.authorization.permission_service import AccessDeniedError
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

active_user = st.selectbox(
    "Active user",
    ["admin", "sales_analyst", "finance_analyst", "customer_support"],
    index=0,
)

show_metadata = st.checkbox(
    "Show Metadata Context"
)

if show_metadata:
    with st.expander("Metadata"):
        metadata_context, _ = build_metadata_context(question, active_user)
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
            plan, retrieval_metadata,response = plan_query(question, active_user)

        if "INSUFFICIENT_AUTHORIZATION" in response:
            st.error("You do not have access to the requested data.")
            with st.expander("Model Response"):
                st.text(response)
            with st.expander("Prompt Preview"):
                user_prompt, _ = build_user_prompt(question, active_user)
                st.text(user_prompt)
            # stop streamlit execution if access is denied
            st.stop()

        elif 'OUT_OF_SCOPE' in response:
            st.error("The question is out of scope for the database.")
            with st.expander("Model Response"):
                st.text(response)
            with st.expander("Prompt Preview"):
                user_prompt, _ = build_user_prompt(question, active_user)
                st.text(user_prompt)
            # stop streamlit execution if access is denied
            st.stop()
        else:
            st.success("Query generated")

        # Show retrieval metadata if dynamic schema was used
        if retrieval_metadata.get("method") != "full":
            st.info(f"Schema Retrieval: {retrieval_metadata.get('method', 'unknown').upper()} | "
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
        
        with st.expander("Model Response"):
            st.text(response)

        with st.expander("Prompt Preview"):
            user_prompt, _ = build_user_prompt(question, active_user)
            st.text(user_prompt)

        with st.expander("Retrieval Metadata"):
            st.json(retrieval_metadata)

    except AccessDeniedError as e:
        st.error("You do not have access to the requested data.")
    except Exception as e:
        st.exception(e)