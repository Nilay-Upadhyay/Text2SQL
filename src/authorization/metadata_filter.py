from __future__ import annotations

from src.authorization.seed_relationships import normalize_table_name


def filter_schema_metadata(
    schema_dict: dict,
    allowed_tables: set[str] | list[str] | None = None,
    allowed_columns: dict[str, set[str] | list[str]] | None = None,
) -> dict:
    allowed_table_names = {normalize_table_name(table) for table in (allowed_tables or [])}
    if not allowed_table_names:
        return {}

    filtered: dict = {}
    for table_name, table_data in schema_dict.items():
        canonical_name = normalize_table_name(table_name)
        if canonical_name not in allowed_table_names:
            continue

        columns = table_data.get("columns", {})
        permitted_columns = {
            column_name
            for column_name in (allowed_columns or {}).get(canonical_name, set(columns))
        }
        filtered_columns = {
            column_name: column_type
            for column_name, column_type in columns.items()
            if column_name in permitted_columns
        }
        if filtered_columns:
            filtered[table_name] = {"columns": filtered_columns}
    return filtered


def filter_business_metadata(
    business_dict: dict,
    allowed_tables: set[str] | list[str] | None = None,
    allowed_columns: dict[str, set[str] | list[str]] | None = None,
) -> dict:
    allowed_table_names = {normalize_table_name(table) for table in (allowed_tables or [])}
    if not allowed_table_names:
        return {}

    filtered: dict = {}
    for key, value in business_dict.items():
        table_name, _, column_name = key.partition(".")
        canonical_name = normalize_table_name(table_name)
        if canonical_name not in allowed_table_names:
            continue
        if column_name:
            permitted_columns = {
                column
                for column in (allowed_columns or {}).get(canonical_name, [])
            }
            if permitted_columns and column_name not in permitted_columns:
                continue
        filtered[key] = value
    return filtered
