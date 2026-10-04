"""Configuration tests never connect to PostgreSQL or use personal data."""
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event

from app import database
from app.main import create_app
from app.migrate import require_current_schema, upgrade


@pytest.fixture(autouse=True)
def isolated_configuration(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SIDEQUEST_DB_PATH", raising=False)
    monkeypatch.setattr(database, "BACKEND_ROOT", tmp_path)


@pytest.mark.parametrize("selection", ["default", "relative_env", "absolute_env", "argument"])
def test_sqlite_path_selection(selection, monkeypatch, tmp_path):
    path = None
    expected = tmp_path / "data/sidequest.sqlite3"
    if selection == "relative_env":
        monkeypatch.setenv("SIDEQUEST_DB_PATH", "nested/library.sqlite3")
        expected = tmp_path / "nested/library.sqlite3"
    elif selection == "absolute_env":
        expected = tmp_path / "absolute/library.sqlite3"
        monkeypatch.setenv("SIDEQUEST_DB_PATH", str(expected))
    elif selection == "argument":
        monkeypatch.setenv("SIDEQUEST_DB_PATH", "ignored.sqlite3")
        path = expected = tmp_path / "argument/library.sqlite3"
    engine = database.make_engine(path)
    try:
        assert engine.url.database == str(expected.resolve())
        assert expected.parent.is_dir()
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
            assert connection.connection.driver_connection.isolation_level is None
        assert expected.is_file()
    finally:
        engine.dispose()


@pytest.mark.parametrize("driver", ["postgresql", "postgresql+psycopg", "postgresql+psycopg2"])
def test_external_engine_is_separate(driver, monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"{driver}://owner:fictional_password@localhost/example")
    configuration = database.database_configuration()
    assert configuration.dialect == "postgresql"
    assert configuration.sqlite_path is None
    assert "fictional_password" not in repr(configuration)
    engine = Mock()
    factory = Mock(return_value=engine)
    hooks = Mock(side_effect=AssertionError("SQLite hook installed"))
    monkeypatch.setattr(database, "create_engine", factory)
    monkeypatch.setattr(database.event, "listens_for", hooks)
    assert database.make_engine() is engine
    factory.assert_called_once_with(configuration.url, isolation_level="READ COMMITTED", hide_parameters=True)
    hooks.assert_not_called()
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("path_variable", ["library.sqlite3", ""])
def test_environment_conflict_redacts_credentials(path_variable, monkeypatch, tmp_path):
    monkeypatch.setenv("SIDEQUEST_DB_PATH", path_variable)
    monkeypatch.setenv("DATABASE_URL", "postgresql://secret_user:secret_password@localhost/db?token=secret_token")
    with pytest.raises(ValueError, match="DATABASE_URL.*SIDEQUEST_DB_PATH") as error:
        database.make_engine()
    assert "secret_" not in str(error.value)
    assert list(tmp_path.iterdir()) == []


def test_explicit_path_conflicts_with_url(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/example")
    with pytest.raises(ValueError, match="explicit SQLite path"):
        database.make_engine(tmp_path / "local.sqlite3")
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("url", ["", "  ", "not-a-url-secret_password", "postgresql://owner:secret_password@host:bad/db"])
def test_invalid_url_is_sanitized(url, monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(ValueError, match="valid SQLAlchemy database URL") as error:
        database.make_engine()
    assert "secret_password" not in str(error.value)
    assert error.value.__suppress_context__
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("url", ["mysql://owner:secret_password@localhost/db", "unknown://localhost/db", "postgres://localhost/db"])
def test_unsupported_dialect(url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(ValueError, match="dialect is unsupported") as error:
        database.database_configuration()
    assert "secret_password" not in str(error.value)


@pytest.mark.parametrize("url", ["postgresql+asyncpg://localhost/db", "sqlite+aiosqlite:///db.sqlite3"])
def test_async_driver_rejected(url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(ValueError, match="synchronous"):
        database.make_engine()


@pytest.mark.parametrize("url", ["sqlite://", "sqlite:///:memory:", "sqlite:///file:test?uri=true"])
def test_sqlite_url_requires_ordinary_file(url, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", url)
    with pytest.raises(ValueError, match="local database file"):
        database.make_engine()


@pytest.mark.parametrize("driver", ["sqlite", "sqlite+pysqlite"])
def test_sqlite_url_uses_same_hooks(driver, monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", f"{driver}:///nested/url.sqlite3")
    engine = database.make_engine()
    commands = []
    event.listen(engine, "before_cursor_execute", lambda c, cursor, sql, params, ctx, many: commands.append(sql))
    try:
        assert engine.url.database == str(tmp_path / "nested/url.sqlite3")
        with engine.connect() as connection:
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
            connection.rollback()
            connection.info["begin_immediate"] = True
            with connection.begin():
                connection.exec_driver_sql("CREATE TABLE sample(id INTEGER)")
                connection.exec_driver_sql("INSERT INTO sample VALUES (1)")
            assert "begin_immediate" not in connection.info
        assert "BEGIN" in commands and "BEGIN IMMEDIATE" in commands
        with engine.connect() as connection:
            assert connection.exec_driver_sql("SELECT count(*) FROM sample").scalar() == 1
    finally:
        engine.dispose()


def test_external_initialization_error_is_sanitized(monkeypatch, caplog, capsys):
    monkeypatch.setenv("DATABASE_URL", "postgresql://owner:secret_password@localhost/db?token=secret_token")
    monkeypatch.setattr(database, "create_engine", Mock(side_effect=ImportError("secret_password secret_token")))
    with pytest.raises(RuntimeError, match="synchronous driver") as error:
        database.make_engine()
    assert "secret_" not in str(error.value)
    assert error.value.__suppress_context__
    assert "secret_" not in caplog.text + capsys.readouterr().out


@pytest.mark.parametrize("operation", [require_current_schema, upgrade])
def test_unsupported_schema_guard_precedes_connection(operation):
    engine = SimpleNamespace(dialect=SimpleNamespace(name="mysql"), connect=Mock())
    with pytest.raises(RuntimeError, match="Unsupported migration dialect"):
        operation(engine)
    engine.connect.assert_not_called()


def test_external_application_startup_guard(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "postgresql://localhost/example")
    engine = Mock()
    engine.dialect.name = "postgresql"
    monkeypatch.setattr(database, "create_engine", Mock(return_value=engine))
    monkeypatch.setattr("app.main.require_current_schema", Mock(side_effect=RuntimeError("Database is not migrated")))
    application = create_app()
    with pytest.raises(RuntimeError, match="Database is not migrated"):
        with TestClient(application):
            pass
    engine.connect.assert_not_called()
    engine.dispose.assert_called_once()
    assert list(tmp_path.iterdir()) == []


def test_local_startup_migrations_and_reopen(tmp_path):
    path = tmp_path / "startup.sqlite3"
    engine = database.make_engine(path)
    assert upgrade(engine) == 2
    assert upgrade(engine) == 2
    require_current_schema(engine)
    engine.dispose()
    with TestClient(create_app(path)) as client:
        assert client.get("/api/games").json() == []


def test_sqlite_migration_cli(monkeypatch, tmp_path):
    import os
    environment = dict(os.environ)
    environment.pop("DATABASE_URL", None)
    environment["SIDEQUEST_DB_PATH"] = str(tmp_path / "cli.sqlite3")
    backend = database.Path(__file__).resolve().parents[1]
    for _ in range(2):
        result = subprocess.run([sys.executable, "-m", "app.migrate"], cwd=backend,
                                env=environment, capture_output=True, text=True, check=True)
        assert "Database at migration 002" in result.stdout
    assert (tmp_path / "cli.sqlite3").is_file()
