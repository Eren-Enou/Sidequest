"""Synchronous, file-backed SQLite connections with foreign keys always enabled."""

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL

BACKEND_ROOT = Path(__file__).resolve().parents[1]


def database_path(path=None) -> Path:
    value = Path(path or os.environ.get("SIDEQUEST_DB_PATH", "data/sidequest.sqlite3"))
    return (value if value.is_absolute() else BACKEND_ROOT / value).resolve()


def make_engine(path=None):
    target = database_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(URL.create("sqlite+pysqlite", database=str(target)),
                           connect_args={"check_same_thread": False, "timeout": 5})

    @event.listens_for(engine, "connect")
    def configure(dbapi_connection, _):
        # Let SQLAlchemy issue BEGIN so SQLite DDL and reads participate in transactions.
        dbapi_connection.isolation_level = None
        dbapi_connection.execute("PRAGMA foreign_keys=ON")
        if dbapi_connection.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
            raise RuntimeError("SQLite foreign-key enforcement is unavailable")

    @event.listens_for(engine, "begin")
    def begin(connection):
        immediate = connection.info.pop("begin_immediate", False)
        connection.exec_driver_sql("BEGIN IMMEDIATE" if immediate else "BEGIN")

    return engine
