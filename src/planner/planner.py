import json
import os
from pathlib import Path
import requests
from dotenv import load_dotenv
import sqlparse 
from src.planner.metadata_loader import load_metadata
from src.planner.prompts import PLANNER_PROMPT

load_dotenv()

# Global variables for Groq configuration
GROQ_API_KEY = None
GROQ_MODEL = None
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"


def load_config():
    global GROQ_API_KEY
    global GROQ_MODEL

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GROQ_MODEL = os.getenv("GROQ_MODEL")

    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not configured in .env")
    
    if not GROQ_MODEL:
        raise ValueError("GROQ_MODEL not configured in .env")


def build_metadata_context() -> str:
    """Constructs the LLM prompt context using the raw file text."""
    schema_text, biz_dict_text = load_metadata()

    return f"""
SCHEMA:
{schema_text}

BUSINESS_DICTIONARY:
{biz_dict_text}
"""


def build_user_prompt(question: str) -> str:
    metadata_context = build_metadata_context()

    return f"""
USER QUESTION:

{question}

DATABASE METADATA:

{metadata_context}
"""


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


def plan_query(question: str) :
    prompt = f"""
{PLANNER_PROMPT}

{build_user_prompt(question)}
"""

    response_text = call_groq(prompt)
    query = extract_sql_query(response_text)

    return query



if __name__ == "__main__":
    load_config()

    question = (
        "highest value customer"
    )

    plan = plan_query(question)

    print("\nQUERY\n")
    print(plan)