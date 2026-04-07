from __future__ import annotations

import ipaddress
import re
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pymysql

from backend.config import settings


SCHEMA_SQL_PATH = Path(__file__).resolve().parent / "schema_init.sql"
SAMPLE_SQL_PATH = Path(__file__).resolve().parent / "sample_appending.sql"


class SessionConfigError(Exception):
    pass


class PracticeDatabaseNotFoundError(Exception):
    pass


@dataclass
class SessionLease:
    client_ip: str
    database: str
    expires_at: datetime


_LEASES: dict[str, SessionLease] = {}
_LOCK = threading.Lock()


def resolve_client_ip(raw_client_ip: str | None) -> str:
    candidate = (raw_client_ip or "").split(",")[0].strip()
    if not candidate:
        candidate = "127.0.0.1"

    try:
        normalized = ipaddress.ip_address(candidate)
    except ValueError:
        sanitized = "".join(ch if ch.isalnum() else "_" for ch in candidate)
        return sanitized.strip("_").lower() or "unknown_client"

    return str(normalized).replace(":", "_").replace(".", "_")


def resolve_database_name_from_ip(raw_client_ip: str | None) -> str:
    return f"{settings.mysql_database}_{resolve_client_ip(raw_client_ip)}"


def ensure_practice_database(raw_client_ip: str | None) -> SessionLease:
    _require_root_password()
    cleanup_expired_sessions()

    client_key = resolve_client_ip(raw_client_ip)
    database = resolve_database_name_from_ip(raw_client_ip)
    expires_at = _next_expiration()

    with _LOCK:
        lease = _LEASES.get(client_key)
        if lease:
            lease.expires_at = expires_at
            return lease

        if _database_exists(database):
            _drop_database(database)
        _create_database(database)
        _initialize_database(database)
        lease = SessionLease(client_ip=client_key, database=database, expires_at=expires_at)
        _LEASES[client_key] = lease
        return lease


def heartbeat_practice_database(raw_client_ip: str | None) -> SessionLease:
    cleanup_expired_sessions()
    client_key = resolve_client_ip(raw_client_ip)

    with _LOCK:
        lease = _LEASES.get(client_key)
        if lease:
            lease.expires_at = _next_expiration()
            return lease

    return ensure_practice_database(raw_client_ip)


def release_practice_database(raw_client_ip: str | None) -> None:
    client_key = resolve_client_ip(raw_client_ip)

    with _LOCK:
        lease = _LEASES.pop(client_key, None)

    if lease:
        _drop_database(lease.database)


def get_active_database(raw_client_ip: str | None) -> str:
    cleanup_expired_sessions()
    client_key = resolve_client_ip(raw_client_ip)
    expires_at = _next_expiration()

    with _LOCK:
        lease = _LEASES.get(client_key)
        if lease:
            lease.expires_at = expires_at
            return lease.database

    database = resolve_database_name_from_ip(raw_client_ip)
    if not _database_exists(database):
        raise PracticeDatabaseNotFoundError(database)

    with _LOCK:
        _LEASES[client_key] = SessionLease(client_ip=client_key, database=database, expires_at=expires_at)

    return database


def cleanup_expired_sessions() -> None:
    now = datetime.now(UTC)

    with _LOCK:
        expired = [key for key, lease in _LEASES.items() if lease.expires_at <= now]
        databases = [_LEASES[key].database for key in expired]
        for key in expired:
            _LEASES.pop(key, None)

    for database in databases:
        _drop_database(database)


def _next_expiration() -> datetime:
    return datetime.now(UTC) + timedelta(seconds=settings.session_ttl_seconds)


def _require_root_password() -> None:
    if not settings.mysql_root_password:
        raise SessionConfigError("MYSQL_ROOT_PASSWORD is required for IP-scoped practice database management.")


def _admin_connection(database: str | None = None):
    return pymysql.connect(
        host=settings.mysql_host,
        port=settings.mysql_port,
        user="root",
        password=settings.mysql_root_password,
        database=database,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def _database_exists(database: str) -> bool:
    connection = _admin_connection("information_schema")
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT 1
                FROM schemata
                WHERE schema_name = %s
                LIMIT 1
                """,
                (database,),
            )
            return cursor.fetchone() is not None
    finally:
        connection.close()


def _create_database(database: str) -> None:
    connection = _admin_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE `{database}`")
            cursor.execute(f"GRANT ALL PRIVILEGES ON `{database}`.* TO `{settings.mysql_user}`@'%'")
            cursor.execute("FLUSH PRIVILEGES")
    finally:
        connection.close()


def _drop_database(database: str) -> None:
    connection = _admin_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(f"DROP DATABASE IF EXISTS `{database}`")
    finally:
        connection.close()


def _initialize_database(database: str) -> None:
    sql_scripts = [SCHEMA_SQL_PATH.read_text(), SAMPLE_SQL_PATH.read_text()]
    connection = _admin_connection(database)

    try:
        with connection.cursor() as cursor:
            for statement in _split_sql_statements("\n".join(sql_scripts)):
                cursor.execute(statement)
    finally:
        connection.close()


def _split_sql_statements(sql: str) -> list[str]:
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    statements: list[str] = []
    current: list[str] = []

    for line in sql.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue

        current.append(line)
        if stripped.endswith(";"):
            statement = "\n".join(current).strip().rstrip(";").strip()
            if statement:
                statements.append(statement)
            current = []

    trailing = "\n".join(current).strip().rstrip(";").strip()
    if trailing:
        statements.append(trailing)

    return statements
