from __future__ import annotations

import re
from typing import Any

import pymysql

from backend.config import settings
from backend.metadata import DatabaseNotFoundError


REFERENCES_SHORTCUT_PATTERN = re.compile(
    r"foreign\s+key\s*\((?P<local_columns>[^)]+)\)\s+references\s+(?P<table>[a-zA-Z_][a-zA-Z0-9_]*)\b(?!\s*\()",
    re.IGNORECASE,
)


def _get_connection(schema_name: str):
    return pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database=schema_name,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def _schema_exists(schema_name: str) -> bool:
    connection = pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database="information_schema",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM schemata
                WHERE schema_name = %s
                LIMIT 1
                """,
                (schema_name,),
            )
            return cursor.fetchone() is not None
    finally:
        connection.close()


def _fetch_primary_key_columns(cursor, schema_name: str, table_name: str) -> list[str]:
    cursor.execute(
        """
        SELECT
            kcu.column_name AS column_name
        FROM table_constraints tc
        JOIN key_column_usage kcu
          ON tc.constraint_schema = kcu.constraint_schema
         AND tc.table_name = kcu.table_name
         AND tc.constraint_name = kcu.constraint_name
        WHERE tc.constraint_schema = %s
          AND tc.table_name = %s
          AND tc.constraint_type = 'PRIMARY KEY'
        ORDER BY kcu.ordinal_position
        """,
        (schema_name, table_name),
    )
    return [row["column_name"] for row in cursor.fetchall()]


def _rewrite_references_shortcuts(query: str, schema_name: str) -> str:
    info_connection = pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database="information_schema",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )

    try:
        with info_connection.cursor() as cursor:
            def replace(match: re.Match[str]) -> str:
                referenced_table = match.group("table")
                pk_columns = _fetch_primary_key_columns(cursor, schema_name, referenced_table)
                if not pk_columns:
                    return match.group(0)

                rewritten_columns = ", ".join(pk_columns)
                return (
                    f"foreign key ({match.group('local_columns')}) "
                    f"references {referenced_table}({rewritten_columns})"
                )

            return REFERENCES_SHORTCUT_PATTERN.sub(replace, query)
    finally:
        info_connection.close()


def _should_retry_create(error: Exception, query: str) -> bool:
    message = str(error).lower()
    normalized_query = query.lstrip().lower()
    return normalized_query.startswith("create") and "foreign key" in message and "references" in normalized_query


def execute_query(query: str, schema_name: str) -> dict[str, Any]:
    if not _schema_exists(schema_name):
        raise DatabaseNotFoundError(schema_name)

    stripped_query = query.strip()
    if not stripped_query:
        raise ValueError("Query is empty.")

    with _get_connection(schema_name) as connection:
        with connection.cursor() as cursor:
            try:
                cursor.execute(stripped_query)
                result = _build_result(cursor, stripped_query)
                connection.commit()
                return result
            except pymysql.MySQLError as error:
                connection.rollback()
                if not _should_retry_create(error, stripped_query):
                    raise

                rewritten_query = _rewrite_references_shortcuts(stripped_query, schema_name)
                if rewritten_query == stripped_query:
                    raise

                cursor.execute(rewritten_query)
                result = _build_result(cursor, rewritten_query)
                connection.commit()
                result["rewrittenQuery"] = rewritten_query
                result["note"] = "MySQL REFERENCES shorthand was expanded automatically."
                return result


def _build_result(cursor, query: str) -> dict[str, Any]:
    normalized_query = query.lstrip().lower()
    normalized_query = normalized_query.lstrip("(").lstrip()
    if normalized_query.startswith(("select", "show", "describe", "desc")):
        rows = cursor.fetchall()
        columns = list(rows[0].keys()) if rows else [column[0] for column in (cursor.description or [])]
        return {
            "kind": "result_set",
            "columns": columns,
            "rows": rows,
            "rowCount": len(rows),
        }

    return {
        "kind": "statement",
        "message": "Statement executed successfully.",
        "affectedRows": cursor.rowcount,
    }
