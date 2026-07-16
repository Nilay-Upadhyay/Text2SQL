from __future__ import annotations

import json
import os

from src.authorization.metadata_filter import filter_business_metadata, filter_schema_metadata
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


