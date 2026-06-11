from __future__ import annotations

import sqlparse


class SqlValidationError(ValueError):
    """Raised when SQL validation fails."""


def validate_sql_query(sql: str) -> None:
    """Validate that the SQL query is a single SELECT statement.

    This blocks multi-statement payloads and any non-SELECT SQL to help
    avoid SQL injection / unsafe execution risks.
    """
    if not isinstance(sql, str) or not sql.strip():
        raise SqlValidationError("SQL query is empty or missing.")

    statements = [statement for statement in sqlparse.parse(sql) if statement.tokens]
    if len(statements) != 1:
        raise SqlValidationError("Only a single SQL statement is allowed.")

    split_statements = [stmt for stmt in sqlparse.split(sql) if stmt.strip()]
    if len(split_statements) != 1:
        raise SqlValidationError("Only a single SQL statement is allowed.")

    statement = statements[0]
    statement_type = statement.get_type()
    if statement_type != "SELECT":
        raise SqlValidationError("Only SELECT queries are permitted.")
