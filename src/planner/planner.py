import json
from pathlib import Path

import requests
from dotenv import load_dotenv

from src.planner.models import QueryPlan
from src.planner.metadata_loader import load_metadata
from src.planner.prompts import PLANNER_PROMPT

load_dotenv()


OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = None


def load_config():
    import os

    global OLLAMA_BASE_URL
    global OLLAMA_MODEL

    OLLAMA_BASE_URL = os.getenv(
        "OLLAMA_BASE_URL",
        "http://localhost:11434",
    )

    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")

    if not OLLAMA_MODEL:
        raise ValueError(
            "OLLAMA_MODEL not configured in .env"
        )


def build_metadata_context() -> str:
    metadata = load_metadata()

    return f"""
SCHEMA:
{json.dumps(metadata["schema"], indent=2)}

BUSINESS_DICTIONARY:
{json.dumps(metadata["business_dictionary"], indent=2)}

JOIN_DICTIONARY:
{json.dumps(metadata["joins"], indent=2)}

QUERY_PATTERNS:
{json.dumps(metadata["patterns"], indent=2)}
"""


def build_user_prompt(question: str) -> str:
    metadata_context = build_metadata_context()

    return f"""
USER QUESTION:

{question}

DATABASE METADATA:

{metadata_context}
"""


def call_ollama(prompt: str) -> str:

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "format": "json",
    }

    response = requests.post(
        f"{OLLAMA_BASE_URL}/api/generate",
        json=payload,
        timeout=120,
    )

    response.raise_for_status()

    data = response.json()

    return data["response"]


def plan_query(question: str) -> QueryPlan:

    prompt = f"""
{PLANNER_PROMPT}

{build_user_prompt(question)}
"""

    response_text = call_ollama(prompt)

    return QueryPlan.model_validate_json(
        response_text
    )


if __name__ == "__main__":

    load_config()

    question = (
        "Which sellers generated the highest revenue?"
    )

    plan = plan_query(question)

    print("\nQUERY PLAN\n")
    print(plan.model_dump_json(indent=2))