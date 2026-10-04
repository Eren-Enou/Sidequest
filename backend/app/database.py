"""Database selection and synchronous, dialect-specific engine initialization."""

import os
from pathlib import Path
from dataclasses import dataclass, field

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.pool import NullPool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
WRITE_LOCK_NAMESPACE = 0x53494445  # SIDE; same lock for all Sidequest writes in this database.
WRITE_LOCK_KEY = 1


def serialize_postgresql_write(db):
    if db.get_bind().dialect.name == "postgresql":
        db.execute(text("SELECT pg_advisory_xact_lock(:namespace, :key)"),
                   {"namespace": WRITE_LOCK_NAMESPACE, "key": WRITE_LOCK_KEY})


def database_path(path=None) -> Path:
    value = Path(path or os.environ.get("SIDEQUEST_DB_PATH", "data/sidequest.sqlite3"))
    return (value if value.is_absolute() else BACKEND_ROOT / value).resolve()


@dataclass(frozen=True)
class DatabaseConfiguration:
    # URLs may contain secrets in usernames/query parameters as well as passwords.
    url: URL = field(repr=False)
    dialect: str
    sqlite_path: Path | None = None


def database_configuration(path=None) -> DatabaseConfiguration:
    if "DATABASE_URL" not in os.environ:
        target = database_path(path)
        return DatabaseConfiguration(URL.create("sqlite+pysqlite", database=str(target)),
                                     "sqlite", target)
    if "SIDEQUEST_DB_PATH" in os.environ or path is not None:
        raise ValueError("DATABASE_URL conflicts with SIDEQUEST_DB_PATH or an explicit SQLite path")
    try:
        url = make_url(os.environ["DATABASE_URL"])
        dialect = url.get_backend_name()
    except Exception:
        raise ValueError("DATABASE_URL must be a valid SQLAlchemy database URL") from None
    if dialect not in {"sqlite", "postgresql"}:
        raise ValueError("DATABASE_URL dialect is unsupported; choose sqlite or postgresql")
    if dialect == "postgresql":
        if url.drivername not in {"postgresql", "postgresql+psycopg", "postgresql+psycopg2"}:
            raise ValueError("DATABASE_URL requires a supported synchronous PostgreSQL driver")
        if url.drivername == "postgresql":
            url = url.set(drivername="postgresql+psycopg")
        return DatabaseConfiguration(url, dialect)
    if url.drivername not in {"sqlite", "sqlite+pysqlite"}:
        raise ValueError("DATABASE_URL requires the synchronous SQLite pysqlite driver")
    if not url.database or url.database == ":memory:" or url.host or url.username or url.password:
        raise ValueError("DATABASE_URL SQLite mode requires a local database file")
    if "uri" in url.query:
        raise ValueError("DATABASE_URL SQLite URI mode is unsupported; use a local database file")
    target = database_path(url.database)
    return DatabaseConfiguration(url.set(drivername="sqlite+pysqlite", database=str(target)),
                                 dialect, target)


def make_engine(path=None):
    configuration = database_configuration(path)
    if configuration.dialect != "sqlite":
        try:
            # READ COMMITTED reads current committed state after acquiring the write lock.
            options = {}
            profile = os.environ.get("SIDEQUEST_POSTGRES_POOL", "queue")
            if profile == "null":
                options["poolclass"] = NullPool
            elif profile != "queue":
                raise ValueError("SIDEQUEST_POSTGRES_POOL must be queue or null")
            return create_engine(configuration.url, isolation_level="READ COMMITTED",
                                 hide_parameters=True, **options)
        except Exception:
            raise RuntimeError("DATABASE_URL engine initialization failed; PostgreSQL requires "
                               "a supported synchronous driver and valid configuration") from None
    return _sqlite_engine(configuration)


def _sqlite_engine(configuration):
    target = configuration.sqlite_path
    target.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(configuration.url,
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
