"""Apply numbered SQL migrations explicitly; no ORM create_all or startup migration."""

import argparse
import hashlib
import sqlite3

from sqlalchemy import inspect

from app.database import BACKEND_ROOT, make_engine

MIGRATION_DIR = BACKEND_ROOT / "migrations"


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
    with engine.connect() as connection:
        files = migration_files()
        applied = _applied(connection)
        _validate_history(applied, files)
        if len(applied) != len(files):
            raise RuntimeError("Database is not migrated. Run: python -m app.migrate")
        if not {"games", "goals", "play_sessions"}.issubset(inspect(connection).get_table_names()):
            raise RuntimeError("Migrated database is missing required tables")


def upgrade(engine, directory=MIGRATION_DIR):
    files = migration_files(directory)
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", help="SQLite file path; relative paths are based on backend/")
    args = parser.parse_args()
    engine = make_engine(args.database)
    try:
        print(f"Database at migration {upgrade(engine):03d}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
