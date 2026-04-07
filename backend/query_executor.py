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
UNIQUE_PATTERN = re.compile(r"\bunique\s*\(", re.IGNORECASE)


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


def _rewrite_textbook_predicates(query: str) -> tuple[str, list[str]]:
    rewritten = query
    notes: list[str] = []

    if UNIQUE_PATTERN.search(rewritten):
        rewritten = _rewrite_unique_predicates(rewritten)
        if rewritten != query:
            notes.append("UNIQUE(subquery) was expanded into a duplicate-check subquery.")

    return rewritten, notes


def _rewrite_unique_predicates(query: str) -> str:
    cursor = 0
    chunks: list[str] = []

    while True:
        match = UNIQUE_PATTERN.search(query, cursor)
        if not match:
            chunks.append(query[cursor:])
            break

        open_paren_index = query.find("(", match.start())
        close_paren_index = _find_matching_paren(query, open_paren_index)
        if close_paren_index == -1:
            chunks.append(query[cursor:])
            break

        subquery = query[open_paren_index + 1 : close_paren_index].strip()
        rewritten = _build_unique_rewrite(subquery)
        chunks.append(query[cursor : match.start()])
        chunks.append(rewritten)
        cursor = close_paren_index + 1

    return "".join(chunks)


def _build_unique_rewrite(subquery: str) -> str:
    select_index = _find_keyword_at_top_level(subquery, "select")
    from_index = _find_keyword_at_top_level(subquery, "from")

    if select_index == -1 or from_index == -1 or from_index <= select_index:
        return f"unique({subquery})"

    select_list = subquery[select_index + len("select") : from_index].strip()
    expressions = _split_top_level(select_list, ",")
    if not expressions:
        return f"unique({subquery})"

    aliases = [f"__unique_col_{index}" for index in range(len(expressions))]
    aliased_select = ", ".join(
        f"{expression.strip()} AS {alias}" for expression, alias in zip(expressions, aliases, strict=False)
    )
    rest = subquery[from_index:]
    derived_query = f"SELECT {aliased_select} {rest}"
    group_by = ", ".join(aliases)

    return (
        "NOT EXISTS ("
        "SELECT 1 "
        f"FROM ({derived_query}) AS __unique_subquery "
        f"GROUP BY {group_by} "
        "HAVING COUNT(*) > 1"
        ")"
    )


def _find_matching_paren(text: str, open_index: int) -> int:
    depth = 0
    in_single_quote = False
    in_double_quote = False

    for index in range(open_index, len(text)):
        char = text[index]
        prev = text[index - 1] if index > 0 else ""

        if char == "'" and not in_double_quote and prev != "\\":
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote and prev != "\\":
            in_double_quote = not in_double_quote
        elif not in_single_quote and not in_double_quote:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return index

    return -1


def _find_keyword_at_top_level(text: str, keyword: str) -> int:
    lower_text = text.lower()
    lower_keyword = keyword.lower()
    depth = 0
    in_single_quote = False
    in_double_quote = False

    for index, char in enumerate(text):
        prev = text[index - 1] if index > 0 else ""

        if char == "'" and not in_double_quote and prev != "\\":
            in_single_quote = not in_single_quote
            continue
        if char == '"' and not in_single_quote and prev != "\\":
            in_double_quote = not in_double_quote
            continue
        if in_single_quote or in_double_quote:
            continue

        if char == "(":
            depth += 1
            continue
        if char == ")":
            depth -= 1
            continue

        if depth == 0 and lower_text.startswith(lower_keyword, index):
            before = lower_text[index - 1] if index > 0 else " "
            after_index = index + len(lower_keyword)
            after = lower_text[after_index] if after_index < len(lower_text) else " "
            if not (before.isalnum() or before == "_") and not (after.isalnum() or after == "_"):
                return index

    return -1


def _split_top_level(text: str, delimiter: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    in_single_quote = False
    in_double_quote = False

    for index, char in enumerate(text):
        prev = text[index - 1] if index > 0 else ""

        if char == "'" and not in_double_quote and prev != "\\":
            in_single_quote = not in_single_quote
        elif char == '"' and not in_single_quote and prev != "\\":
            in_double_quote = not in_double_quote
        elif not in_single_quote and not in_double_quote:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
            elif char == delimiter and depth == 0:
                parts.append("".join(current).strip())
                current = []
                continue

        current.append(char)

    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


def execute_query(query: str, schema_name: str) -> dict[str, Any]:
    if not _schema_exists(schema_name):
        raise DatabaseNotFoundError(schema_name)

    stripped_query = query.strip()
    if not stripped_query:
        raise ValueError("Query is empty.")

    rewritten_query, rewrite_notes = _rewrite_textbook_predicates(stripped_query)

    with _get_connection(schema_name) as connection:
        with connection.cursor() as cursor:
            try:
                cursor.execute(rewritten_query)
                result = _build_result(cursor, rewritten_query)
                connection.commit()
                if rewrite_notes:
                    result["rewrittenQuery"] = rewritten_query
                    result["note"] = " ".join(rewrite_notes)
                return result
            except pymysql.MySQLError as error:
                connection.rollback()
                if not _should_retry_create(error, rewritten_query):
                    raise

                retried_query = _rewrite_references_shortcuts(rewritten_query, schema_name)
                if retried_query == rewritten_query:
                    raise

                cursor.execute(retried_query)
                result = _build_result(cursor, retried_query)
                connection.commit()
                notes = rewrite_notes + ["MySQL REFERENCES shorthand was expanded automatically."]
                result["rewrittenQuery"] = retried_query
                result["note"] = " ".join(notes)
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
