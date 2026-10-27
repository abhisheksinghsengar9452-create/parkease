"""Runtime configuration. MySQL is mandatory outside tests."""
from __future__ import annotations
import os


def mysql_database_url() -> str:
    value = os.getenv("DATABASE_URL", "")
    if not value.startswith("mysql+pymysql://"):
        raise RuntimeError("DATABASE_URL must use mysql+pymysql:// and point to MySQL 8.0+.")
    return value
