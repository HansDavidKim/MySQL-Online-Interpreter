from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from backend.metadata import DatabaseNotFoundError, fetch_schema_metadata


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
    return {"status": "ok"}


@app.get("/api/schema-metadata")
def get_schema_metadata(user_id: str | None = Query(default=None)):
    try:
        return fetch_schema_metadata(user_id=user_id)
    except DatabaseNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Practice database '{exc.args[0]}' was not found.",
        ) from exc
