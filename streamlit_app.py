import streamlit as st
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
    page_icon="🧠",
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

st.title("🧠 Text2SQL Planner")

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
        st.code(
            build_metadata_context(),
            language=None,
        )

if st.button(
    "Generate Query Plan",
    use_container_width=True,
):
    if not question.strip():
        st.warning("Please enter a question.")
        st.stop()

    try:
        with st.spinner("Generating plan..."):
            plan = plan_query(question)

        st.success("Plan generated")

        st.subheader("Query")
        st.code(plan)


        try:
                df = execute_sql_query(plan)
                if df.empty:
                    st.info("The SQL query returned no rows.")
                else:
                    st.subheader("Extracted Data")
                    st.dataframe(df)

                    if len(df) > 200:
                        st.caption(f"Showing first {min(len(df), 200)} rows.")
        except Exception as exec_error:
                st.error(f"Query execution failed: {exec_error}")

        with st.expander("Prompt Preview"):
            st.text(
                build_user_prompt(question)
            )

    except Exception as e:
        st.exception(e)