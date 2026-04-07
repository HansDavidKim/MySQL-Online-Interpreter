from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@dataclass(frozen=True)
class Settings:
    mysql_host: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    mysql_port: int = int(os.getenv("MYSQL_PORT", "3306"))
    mysql_database: str = os.getenv("MYSQL_DATABASE", "mysql_interpreter_practice")
    mysql_user: str = os.getenv("MYSQL_USER", "practice_user")
    mysql_password: str = os.getenv("MYSQL_PASSWORD", "practice_password")


settings = Settings()
