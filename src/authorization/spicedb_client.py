from __future__ import annotations

import os
from dataclasses import dataclass

from src.authorization.seed_relationships import (
    get_relationship_tuples,
    get_seed_access,
    normalize_table_name,
)


@dataclass(frozen=True)
class AuthorizationSnapshot:
    user_id: str
    allowed_tables: tuple[str, ...]
    allowed_columns: dict[str, tuple[str, ...]]
    allowed_business_terms: tuple[str, ...]


class SpiceDBClient:
    def __init__(self, endpoint: str | None = None, token: str | None = None) -> None:
        self.endpoint = (endpoint or os.getenv("SPICEDB_ENDPOINT", "")).rstrip("/")
        self.token = token or os.getenv("SPICEDB_TOKEN", "")

    def get_snapshot(self, user_id: str | None = None) -> AuthorizationSnapshot:
        access = get_seed_access(user_id)
        tables = tuple(normalize_table_name(table) for table in access.tables)
        columns = {table: tuple(self._get_columns(table)) for table in tables}
        return AuthorizationSnapshot(
            user_id=access.user_id,
            allowed_tables=tables,
            allowed_columns=columns,
            allowed_business_terms=access.business_terms,
        )

    def get_relationship_tuples(self, user_id: str | None = None) -> list[tuple[str, str, str]]:
        return get_relationship_tuples(user_id)

    def _get_columns(self, table_name: str) -> list[str]:
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "metadata",
            "generated",
            "schema.json",
        )
        if not os.path.exists(schema_path):
            return []

        with open(schema_path, encoding="utf-8") as handle:
            metadata = {
                key: value
                for key, value in __import__("json").load(handle).items()
            }

        table_data = metadata.get(table_name, {})
        return list(table_data.get("columns", {}).keys())

    def get_schema_text(self) -> str:
        schema_path = os.path.join(os.path.dirname(__file__), "schema.zed")
        with open(schema_path, encoding="utf-8") as handle:
            return handle.read()
