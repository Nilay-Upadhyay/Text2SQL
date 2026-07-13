import json
import logging
import os
from pathlib import Path
import requests
from dotenv import load_dotenv
import sqlparse 
from src.planner.metadata_loader import (
    filter_business_dictionary,
    load_metadata,
    load_metadata_dict,
)
from src.planner.prompts import PLANNER_PROMPT, get_dynamic_schema_prompt
from src.authorization.metadata_filter import (
    filter_business_metadata,
    filter_schema_metadata,
)
from src.authorization.permission_service import (
    AccessDeniedError,
    get_authorized_metadata,
    format_authorized_metadata,
    validate_sql_access,
)
from src.metadata.embedding_manager import EmbeddingManager
from src.metadata.vector_retriever import VectorRetriever

load_dotenv()

logger = logging.getLogger(__name__)

# Global variables for Groq configuration
GROQ_API_KEY = None
GROQ_MODEL = None
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"

# Vector retriever for dynamic schema retrieval
VECTOR_RETRIEVER = None
USE_DYNAMIC_SCHEMA = os.getenv("USE_DYNAMIC_SCHEMA", "true").lower() == "true"
SCHEMA_CONFIDENCE_THRESHOLD = float(os.getenv("SCHEMA_CONFIDENCE_THRESHOLD", "0.2"))


def load_config():
    global GROQ_API_KEY
    global GROQ_MODEL
    global VECTOR_RETRIEVER

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL")

    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not configured in .env")
    
    if not GROQ_MODEL:
        raise ValueError("GROQ_MODEL not configured in .env")

    # Initialize vector retriever if dynamic schema is enabled
    if USE_DYNAMIC_SCHEMA:
        try:
            logger.info("Initializing dynamic schema retriever...")
            embedding_manager = EmbeddingManager()
            VECTOR_RETRIEVER = VectorRetriever(
                embedding_manager=embedding_manager,
                similarity_threshold=SCHEMA_CONFIDENCE_THRESHOLD,
                top_k=10,
            )
            logger.info("Dynamic schema retriever initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize vector retriever: {e}. Falling back to full schema.")
            VECTOR_RETRIEVER = None


def build_metadata_context(question: str = "", active_user: str | None = None) -> tuple[str, dict]:
    """Constructs the LLM prompt context using authorized metadata."""
    retrieval_metadata = {
        "method": "full",
        "confidence": 1.0,
        "tables_selected": [],
        "retrieved_count": 0,
        "authorized_user": active_user or "admin",
        "authorized_tables": [],
    }

    snapshot, authorized_schema, authorized_business = get_authorized_metadata(active_user)
    retrieval_metadata["authorized_user"] = snapshot.get("user_id", active_user or "admin")
    retrieval_metadata["authorized_tables"] = list(snapshot.get("allowed_tables", []))

    if USE_DYNAMIC_SCHEMA and VECTOR_RETRIEVER and question:
        try:
            retrieved = VECTOR_RETRIEVER.retrieve_relevant_schema(
                question,
                top_k=10,
                confidence_threshold=SCHEMA_CONFIDENCE_THRESHOLD,
            )

            retrieval_metadata.update(
                {
                    "method": "dynamic" if not retrieved.get("fallback") else "fallback",
                    "confidence": retrieved.get("confidence", 0.0),
                    "tables_selected": retrieved.get("tables", []),
                    "retrieved_count": retrieved.get("result_count", 0),
                }
            )

            if retrieved.get("confidence", 0.0) < SCHEMA_CONFIDENCE_THRESHOLD * 2:
                logger.warning(
                    f"Low confidence retrieval ({retrieved.get('confidence', 0.0):.2f}), "
                    f"falling back to broader schema"
                )
                retrieval_metadata["method"] = "fallback"
            else:
                full_schema_dict, full_biz_dict = load_metadata_dict()
                allowed_tables = set(snapshot.get("allowed_tables", []))
                allowed_columns = {
                    table_name: set(columns)
                    for table_name, columns in snapshot.get("allowed_columns", {}).items()
                }
                expanded_schema = VECTOR_RETRIEVER.expand_retrieved_schema(
                    retrieved, full_schema_dict
                )
                authorized_schema = filter_schema_metadata(expanded_schema, allowed_tables, allowed_columns)
                authorized_business = filter_business_metadata(full_biz_dict, allowed_tables, allowed_columns)

        except Exception as e:
            logger.warning(f"Error in dynamic schema retrieval: {e}. Using authorized full schema.")
            retrieval_metadata["method"] = "error_fallback"

    schema_text, biz_dict_text = format_authorized_metadata(authorized_schema, authorized_business)
    metadata_context = f"""
SCHEMA:
{schema_text}
"""
# BUSINESS_DICTIONARY:
# {biz_dict_text}
    return metadata_context, retrieval_metadata


def build_user_prompt(question: str, active_user: str | None = None) -> tuple[str, dict]:
    """Build the user prompt with metadata context.
    
    Args:
        question: User question
        
    Returns:
        Tuple of (prompt_text, retrieval_metadata)
    """
    metadata_context, retrieval_metadata = build_metadata_context(question, active_user)

    return f"""
USER QUESTION:

{question}

DATABASE METADATA:

{metadata_context}
""", retrieval_metadata


def extract_sql_query(response_text: str) -> str | None:
    try:
        payload = json.loads(response_text)
    except json.JSONDecodeError:
        return None

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key.lower() in {"query", "sql", "sql_query", "statement"} and isinstance(item, str):
                    # Clean, format, and align the extracted SQL query string
                    formatted_sql = sqlparse.format(
                        item,
                        reindent=True,
                        keyword_case='upper',
                        reindent_aligned=True,
                        strip_comments=False
                    )
                    return formatted_sql
                result = walk(item)
                if result:
                    return result
        elif isinstance(value, list):
            for item in value:
                result = walk(item)
                if result:
                    return result
        return None

    return walk(payload)


def call_groq(prompt: str) -> str:
    """Calls the Groq API using standard requests, forcing a JSON object response."""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    # Groq uses the ChatCompletions format and supports structured JSON outputs
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        # Forces the model to respond with a valid JSON object
        "response_format": {"type": "json_object"},
        "temperature": 0.2, 
        "stream": False
    }

    response = requests.post(
        GROQ_BASE_URL,
        headers=headers,
        json=payload,
        timeout=120,
    )
    # Add these lines right before raise_for_status() to see the real error
    if response.status_code != 200:
        print("Groq Error Response:", response.text)

    response.raise_for_status()

    data = response.json()
    
    # Extract text from standard OpenAI/Groq response format
    return data["choices"][0]["message"]["content"]


def plan_query(question: str, active_user: str | None = None) -> tuple[str | None, dict]:
    """Plan a SQL query from a natural language question."""
    snapshot, _, _ = get_authorized_metadata(active_user)
    if not snapshot.get("allowed_tables"):
        raise AccessDeniedError("You do not have access to the requested data.")

    user_prompt, retrieval_metadata = build_user_prompt(question, active_user)
    
    prompt = f"""
{PLANNER_PROMPT}

{user_prompt}
"""

    response_text = call_groq(prompt)
    query = extract_sql_query(response_text)

    if query:
        validate_sql_access(query, active_user)

    return query, retrieval_metadata



if __name__ == "__main__":
    load_config()

    question = (
        "highest value customer"
    )

    plan, metadata = plan_query(question)

    print("\nQUERY\n")
    print(plan)
    print("\nRETRIEVAL METADATA\n")
    print(json.dumps(metadata, indent=2))