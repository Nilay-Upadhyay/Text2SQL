from __future__ import annotations

import json
import os
import re
from pathlib import Path

import sqlparse

from src.authorization.metadata_filter import filter_business_metadata, filter_schema_metadata
from src.authorization.seed_relationships import normalize_table_name
from src.authorization.spicedb_client import SpiceDBClient
from src.planner.metadata_loader import load_metadata_dict


class AccessDeniedError(ValueError):
    """Raised when a generated SQL statement references unauthorized objects."""


def get_active_user_id(user_id: str | None = None) -> str:
    return (user_id or os.getenv("SPICEDB_ACTIVE_USER") or "admin").strip() or "admin"


def get_authorized_metadata(user_id: str | None = None) -> tuple[dict, dict, dict]:
    client = SpiceDBClient()
    snapshot = client.get_snapshot(get_active_user_id(user_id))

    schema_dict, business_dict = load_metadata_dict()
    allowed_tables = set(snapshot.allowed_tables)
    allowed_columns = {
        table_name: set(columns)
        for table_name, columns in snapshot.allowed_columns.items()
    }

    filtered_schema = filter_schema_metadata(schema_dict, allowed_tables, allowed_columns)
    filtered_business = filter_business_metadata(business_dict, allowed_tables, allowed_columns)
    return snapshot.__dict__, filtered_schema, filtered_business


def format_authorized_metadata(schema_dict: dict, business_dict: dict) -> tuple[str, str]:
    schema_text = json.dumps(schema_dict, indent=2)
    business_text = json.dumps(business_dict, indent=2)
    return schema_text, business_text


def validate_sql_access(sql: str, user_id: str | None = None) -> None:
    if not sql or not sql.strip():
        return

    client = SpiceDBClient()
    snapshot = client.get_snapshot(get_active_user_id(user_id))

    allowed_tables = {normalize_table_name(table) for table in snapshot.allowed_tables}
    allowed_columns = {
        normalize_table_name(table): set(columns)
        for table, columns in snapshot.allowed_columns.items()
    }

    table_aliases = get_table_aliases(sql)
    columns = parse_columns(sql, table_aliases)

    unauthorized_tables = [
        table_name
        for table_name in table_aliases.values()
        if normalize_table_name(table_name) not in allowed_tables
    ]
    unauthorized_columns = []
    for table_name, column_names in columns.items():
        canonical_table = normalize_table_name(table_name)
        if canonical_table not in allowed_columns:
            unauthorized_columns.extend(f"{table_name}.{column}" for column in column_names)
            continue
        for column_name in column_names:
            if column_name not in allowed_columns[canonical_table]:
                unauthorized_columns.append(f"{table_name}.{column_name}")

    if unauthorized_tables or unauthorized_columns:
        raise AccessDeniedError(
            "Access Denied: the generated SQL references unauthorized tables or columns."
        )


def get_table_aliases(sql: str) -> dict[str, str]:
    aliases: dict[str, str] = {}
    try:
        statements = sqlparse.parse(sql)
    except Exception:
        return aliases

    if not statements:
        return aliases

    statement = statements[0]
    pattern = re.compile(r"\b(?:from|join)\s+([a-zA-Z_][\w\.]*)(?:\s+(?:as\s+)?([a-zA-Z_][\w]*))?", re.IGNORECASE)
    for match in pattern.finditer(str(statement)):
        table_ref = match.group(1).split(".")[-1]
        alias = (match.group(2) or "").strip()
        if alias:
            aliases[alias] = table_ref
        aliases[table_ref] = table_ref
    return aliases


def parse_columns(sql: str, table_aliases: dict[str, str] | None = None) -> dict[str, list[str]]:
    pattern = re.compile(r"\b([a-zA-Z_][\w]*)\.([a-zA-Z_][\w]*)\b")
    columns: dict[str, list[str]] = {}
    aliases = table_aliases or {}
    for table_name, column_name in pattern.findall(sql):
        resolved_table = aliases.get(table_name, table_name)
        columns.setdefault(resolved_table, []).append(column_name)
    return columns
