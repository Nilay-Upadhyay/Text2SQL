from __future__ import annotations

import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.db.validator import validate_sql_query

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(dotenv_path=ROOT / ".env")


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url

    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "")
    database = os.getenv("POSTGRES_DB")

    if not database:
        raise ValueError("DATABASE_URL or POSTGRES_DB must be configured in .env")

    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"


_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(get_database_url(), future=True)
    return _engine


def execute_sql_query(sql: str, max_rows: int = 500) -> pd.DataFrame:
    """Execute a SQL query against the configured Postgres database."""
    validate_sql_query(sql)

    engine = get_engine()
    df = pd.read_sql_query(sql, engine)
    if max_rows is not None and len(df) > max_rows:
        return df.head(max_rows)
    return df
