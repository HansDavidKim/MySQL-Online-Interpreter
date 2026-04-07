from __future__ import annotations

import pymysql
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.metadata import DatabaseNotFoundError, fetch_schema_metadata
from backend.models import QueryRequest
from backend.query_executor import execute_query
from backend.session_manager import (
    PracticeDatabaseNotFoundError,
    SessionConfigError,
    cleanup_expired_sessions,
    ensure_practice_database,
    get_active_database,
    heartbeat_practice_database,
    release_practice_database,
)


app = FastAPI(title="MySQL Interpreter Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    cleanup_expired_sessions()
    return {"status": "ok"}


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded
    return request.client.host if request.client else None


@app.post("/api/session")
def create_or_resume_session(request: Request):
    try:
        lease = ensure_practice_database(_client_ip(request))
        return {
            "database": lease.database,
            "ttlSeconds": settings.session_ttl_seconds,
        }
    except SessionConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/session/heartbeat")
def heartbeat_session(request: Request):
    try:
        lease = heartbeat_practice_database(_client_ip(request))
        return {
            "database": lease.database,
            "ttlSeconds": settings.session_ttl_seconds,
        }
    except SessionConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/session/release")
def release_session(request: Request):
    try:
        release_practice_database(_client_ip(request))
        return {"released": True}
    except SessionConfigError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/schema-metadata")
def get_schema_metadata(request: Request):
    try:
        return fetch_schema_metadata(get_active_database(_client_ip(request)))
    except DatabaseNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Practice database '{exc.args[0]}' was not found.",
        ) from exc
    except PracticeDatabaseNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Practice database '{exc.args[0]}' was not found for this IP session.",
        ) from exc


@app.post("/api/query")
def run_query(payload: QueryRequest, request: Request):
    try:
        return execute_query(query=payload.query, schema_name=get_active_database(_client_ip(request)))
    except DatabaseNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Practice database '{exc.args[0]}' was not found.",
        ) from exc
    except PracticeDatabaseNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Practice database '{exc.args[0]}' was not found for this IP session.",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except pymysql.MySQLError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
