"""Apply numbered SQL migrations explicitly; no ORM create_all or startup migration."""

import argparse
import hashlib
import sqlite3
from datetime import datetime, timezone

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.database import BACKEND_ROOT, make_engine, WRITE_LOCK_NAMESPACE, WRITE_LOCK_KEY

MIGRATION_DIR = BACKEND_ROOT / "migrations"
POSTGRESQL_MIGRATION_DIR = MIGRATION_DIR / "postgresql"


def stream(engine, directory=None):
    dialect = engine.dialect.name
    if dialect not in {"sqlite", "postgresql"}:
        raise RuntimeError("Unsupported migration dialect")
    files = migration_files(directory or (POSTGRESQL_MIGRATION_DIR if dialect == "postgresql" else MIGRATION_DIR))
    for path in files:
        is_postgresql = path.read_text(encoding="utf-8").startswith("-- sidequest-dialect: postgresql")
        if is_postgresql != (dialect == "postgresql"):
            raise RuntimeError("Migration stream does not match database dialect")
    return files


def checksum(path):
    # Normalize CRLF/LF so a Windows checkout does not invalidate migration history.
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def migration_files(directory=MIGRATION_DIR):
    files = sorted(directory.glob("[0-9][0-9][0-9]_*.sql"))
    numbers = [int(p.name.split("_")[0]) for p in files]
    if not files or numbers != list(range(1, len(files) + 1)):
        raise RuntimeError("Migration numbers must be contiguous, unique, and start at 001")
    return files


def statements(source):
    buffer = ""
    for line in source.splitlines(keepends=True):
        buffer += line
        if sqlite3.complete_statement(buffer):
            yield buffer
            buffer = ""
    if buffer.strip():
        raise RuntimeError("Migration contains an incomplete SQL statement")


def _applied(connection):
    if "schema_migrations" not in inspect(connection).get_table_names():
        return []
    return list(connection.exec_driver_sql("SELECT version, name, checksum FROM schema_migrations ORDER BY version"))


def _validate_history(applied, files):
    if len(applied) > len(files):
        raise RuntimeError("Database has migrations newer than this application")
    for row, path in zip(applied, files):
        expected = (int(path.name.split("_")[0]), path.name, checksum(path))
        if tuple(row) != expected:
            raise RuntimeError("Migration history mismatch; never edit an applied migration")


def require_current_schema(engine):
    try:
        _require_current_schema(engine)
    except SQLAlchemyError:
        if engine.dialect.name == "postgresql":
            raise RuntimeError("PostgreSQL schema validation failed; check connection configuration and explicit migrations") from None
        raise


def _require_current_schema(engine):
    files = stream(engine)
    with engine.connect() as connection:
        if engine.dialect.name == "postgresql" and "schema_migrations" in inspect(connection).get_table_names():
            if connection.exec_driver_sql("SELECT dialect FROM schema_migrations WHERE dialect != 'postgresql'").first():
                raise RuntimeError("Migration history dialect mismatch")
        applied = _applied(connection)
        _validate_history(applied, files)
        if len(applied) != len(files):
            raise RuntimeError("Database is not migrated. Run: python -m app.migrate")
        if not {"games", "goals", "play_sessions"}.issubset(inspect(connection).get_table_names()):
            raise RuntimeError("Migrated database is missing required tables")


def upgrade(engine, directory=None):
    files = stream(engine, directory)
    if engine.dialect.name == "postgresql":
        return _upgrade_postgresql(engine, files)
    with engine.connect() as connection:
        connection.info["begin_immediate"] = True
        with connection.begin():
            tables = set(inspect(connection).get_table_names())
            if tables and "schema_migrations" not in tables:
                raise RuntimeError("Refusing to migrate an unversioned nonempty database")
            applied = _applied(connection)
            _validate_history(applied, files)
            connection.exec_driver_sql("""CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
                checksum TEXT NOT NULL, applied_at TEXT NOT NULL)""")
            for path in files[len(applied):]:
                for statement in statements(path.read_text(encoding="utf-8")):
                    connection.exec_driver_sql(statement)
                connection.exec_driver_sql(
                    "INSERT INTO schema_migrations VALUES (?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))",
                    (int(path.name.split("_")[0]), path.name, checksum(path)))
    return len(files)


def _upgrade_postgresql(engine, files):
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(:namespace, :key)"),
                           {"namespace": WRITE_LOCK_NAMESPACE, "key": WRITE_LOCK_KEY})
        tables = set(inspect(connection).get_table_names())
        if tables and "schema_migrations" not in tables:
            raise RuntimeError("Refusing to migrate an unversioned nonempty database")
        if "schema_migrations" in tables:
            if connection.exec_driver_sql("SELECT dialect FROM schema_migrations WHERE dialect != 'postgresql'").first():
                raise RuntimeError("Migration history dialect mismatch")
        applied = _applied(connection)
        _validate_history(applied, files)
        connection.exec_driver_sql("""CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, checksum TEXT NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL, dialect TEXT NOT NULL CHECK (dialect = 'postgresql'))""")
        for path in files[len(applied):]:
            # Psycopg executes this trusted complete migration script transactionally.
            # No SQLite splitter: PostgreSQL scripts may contain dollar-quoted bodies.
            connection.exec_driver_sql(path.read_text(encoding="utf-8"))
            connection.execute(text("INSERT INTO schema_migrations VALUES (:version, :name, :checksum, :applied_at, 'postgresql')"),
                               {"version": int(path.name.split("_")[0]), "name": path.name,
                                "checksum": checksum(path), "applied_at": datetime.now(timezone.utc)})
    return len(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", help="SQLite file path; relative paths are based on backend/")
    args = parser.parse_args()
    engine = make_engine(args.database)
    try:
        print(f"Database at migration {upgrade(engine):03d}")
    except SQLAlchemyError:
        if engine.dialect.name == "postgresql":
            parser.exit(1, "PostgreSQL migration failed; check connection configuration and migration SQL\n")
        raise
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
