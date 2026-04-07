from __future__ import annotations

import re
from collections import defaultdict

import pymysql

from backend.config import settings


USER_ID_PATTERN = re.compile(r"[^a-zA-Z0-9_]+")


class DatabaseNotFoundError(Exception):
    pass


def resolve_database_name(user_id: str | None) -> str:
    if not user_id:
        return settings.mysql_database

    normalized = USER_ID_PATTERN.sub("_", user_id.strip()).strip("_").lower()
    if not normalized:
        return settings.mysql_database
    return f"{settings.mysql_database}_{normalized}"


def _get_connection():
    return pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user=settings.mysql_user,
        password=settings.mysql_password,
        database="information_schema",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def _schema_exists(cursor, schema_name: str) -> bool:
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


def fetch_schema_metadata(user_id: str | None = None) -> dict:
    schema_name = resolve_database_name(user_id)

    with _get_connection() as connection:
        with connection.cursor() as cursor:
            if not _schema_exists(cursor, schema_name):
                raise DatabaseNotFoundError(schema_name)

            cursor.execute(
                """
                SELECT
                    table_name AS table_name
                FROM tables
                WHERE table_schema = %s
                  AND table_type = 'BASE TABLE'
                ORDER BY table_name
                """,
                (schema_name,),
            )
            table_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    table_name AS table_name,
                    column_name AS column_name,
                    column_type AS column_type,
                    is_nullable AS is_nullable,
                    column_key AS column_key,
                    ordinal_position AS ordinal_position
                FROM columns
                WHERE table_schema = %s
                ORDER BY table_name, ordinal_position
                """,
                (schema_name,),
            )
            column_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    kcu.table_name AS table_name,
                    kcu.column_name AS column_name,
                    kcu.ordinal_position AS ordinal_position
                FROM table_constraints tc
                JOIN key_column_usage kcu
                  ON tc.constraint_schema = kcu.constraint_schema
                 AND tc.table_name = kcu.table_name
                 AND tc.constraint_name = kcu.constraint_name
                WHERE tc.constraint_schema = %s
                  AND tc.constraint_type = 'PRIMARY KEY'
                ORDER BY kcu.table_name, kcu.ordinal_position
                """,
                (schema_name,),
            )
            primary_key_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT
                    kcu.constraint_name AS constraint_name,
                    kcu.table_name AS table_name,
                    kcu.column_name AS column_name,
                    kcu.referenced_table_name AS referenced_table_name,
                    kcu.referenced_column_name AS referenced_column_name,
                    kcu.ordinal_position AS ordinal_position
                FROM key_column_usage kcu
                WHERE kcu.constraint_schema = %s
                  AND kcu.referenced_table_name IS NOT NULL
                ORDER BY
                    kcu.table_name,
                    kcu.constraint_name,
                    kcu.ordinal_position
                """,
                (schema_name,),
            )
            foreign_key_rows = cursor.fetchall()

    tables = {
        row["table_name"]: {
            "name": row["table_name"],
            "columns": [],
            "primaryKey": [],
        }
        for row in table_rows
    }

    for row in column_rows:
        table = tables.setdefault(
            row["table_name"],
            {"name": row["table_name"], "columns": [], "primaryKey": []},
        )
        table["columns"].append(
            {
                "name": row["column_name"],
                "type": row["column_type"],
                "nullable": row["is_nullable"] == "YES",
                "isPrimaryKey": False,
            }
        )

    pk_map: dict[str, list[str]] = defaultdict(list)
    for row in primary_key_rows:
        pk_map[row["table_name"]].append(row["column_name"])

    for table_name, columns in pk_map.items():
        table = tables.setdefault(
            table_name,
            {"name": table_name, "columns": [], "primaryKey": []},
        )
        table["primaryKey"] = columns
        for column in table["columns"]:
            if column["name"] in columns:
                column["isPrimaryKey"] = True

    fk_groups: dict[tuple[str, str], dict] = {}
    for row in foreign_key_rows:
        key = (row["table_name"], row["constraint_name"])
        if key not in fk_groups:
            fk_groups[key] = {
                "name": row["constraint_name"],
                "fromTable": row["table_name"],
                "toTable": row["referenced_table_name"],
                "columnMapping": [],
            }
        fk_groups[key]["columnMapping"].append(
            {
                "fromColumn": row["column_name"],
                "toColumn": row["referenced_column_name"],
            }
        )

    return {
        "database": schema_name,
        "tables": list(tables.values()),
        "foreignKeys": list(fk_groups.values()),
    }
