"""Selected real database contracts run on SQLite and opt-in local PostgreSQL."""
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4
from datetime import timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
import psycopg
from fastapi.testclient import TestClient
from sqlalchemy import event, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import make_engine, serialize_postgresql_write
from app.main import create_app
from app.migrate import upgrade, require_current_schema, POSTGRESQL_MIGRATION_DIR, MIGRATION_DIR
from app.models import Game, Goal, PlaySession
from app.routes import get_evaluation_time
from app.session_routes import get_operation_time
import test_sessions_api as sessions
import test_library_api as library_contracts
from test_library_api import seed, session_row, NOW, GAME


@pytest.fixture(params=["sqlite", "postgresql"])
def persistence(request, monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SIDEQUEST_DB_PATH", raising=False)
    path = tmp_path / "contract.sqlite3"
    admin_url = os.environ.get("SIDEQUEST_TEST_POSTGRES_URL")
    name = None
    if request.param == "postgresql":
        if not admin_url:
            pytest.skip("Set SIDEQUEST_TEST_POSTGRES_URL to an isolated local test cluster")
        url = make_url(admin_url)
        if url.host not in {"127.0.0.1", "localhost", "::1"}:
            pytest.fail("PostgreSQL integration requires a local isolated test cluster", pytrace=False)
        name = "sidequest_test_" + uuid4().hex
        try:
            with psycopg.connect(url.set(drivername="postgresql").render_as_string(hide_password=False), autocommit=True) as admin:
                admin.execute(psycopg.sql.SQL("CREATE DATABASE {}").format(psycopg.sql.Identifier(name)))
        except Exception:
            pytest.fail("Cannot create isolated local PostgreSQL test database", pytrace=False)
        monkeypatch.setenv("DATABASE_URL", url.set(database=name).render_as_string(hide_password=False))
        path = None
    engine = make_engine(path)
    try:
        with pytest.raises(RuntimeError, match="not migrated"):
            require_current_schema(engine)
        assert upgrade(engine) == 2
        assert upgrade(engine) == 2
        require_current_schema(engine)
        monkeypatch.setattr("app.routes.utcnow", lambda: NOW - timedelta(days=1))
        app = create_app(path)
        app.dependency_overrides[get_operation_time] = lambda: NOW
        app.dependency_overrides[get_evaluation_time] = lambda: NOW
        with TestClient(app) as client:
            yield client, app.state.engine, path
    finally:
        engine.dispose()
        if name:
            with psycopg.connect(url.set(drivername="postgresql").render_as_string(hide_password=False), autocommit=True) as admin:
                admin.execute(psycopg.sql.SQL("DROP DATABASE {} WITH (FORCE)").format(psycopg.sql.Identifier(name)))


@pytest.mark.parametrize("scenario", [
    "test_full_loop_snapshot_and_recency", "test_near_equivalent_nonwinner_start",
    "test_stale_recommendation_revalidated", "test_second_active_conflict",
    "test_concurrent_start", "test_reopen_active_and_completed",
    "test_optional_completion_and_duplicate_finish", "test_finish_without_completion",
    "test_finish_and_goal_completion_rollback_on_database_failure",
    "test_history_order_and_immutable_evidence", "test_offset_time_and_one_capture",
    "test_composite_foreign_key_still_enforced", "test_concurrent_finish_preserves_first_history",
    "test_history_newer_finish_precedes_older",
])
def test_lifecycle_contract(persistence, scenario):
    getattr(sessions, scenario)(persistence)


@pytest.mark.parametrize("scenario", ["test_create_retrieve_and_defaults", "test_partial_edits_and_clear_notes"])
def test_library_contract(persistence, scenario):
    getattr(library_contracts, scenario)(persistence)


def test_library_archive_completion_restore(persistence):
    client, _, _ = persistence
    game, goal = seed(client)
    assert client.post(f'/api/goals/{goal["id"]}/complete').json()["status"] == "completed"
    assert client.post(f'/api/goals/{goal["id"]}/restore').json()["status"] == "active"
    assert client.delete(f'/api/goals/{goal["id"]}').status_code == 204
    assert client.post(f'/api/goals/{goal["id"]}/restore').json()["status"] == "active"
    assert client.delete(f'/api/games/{game["id"]}').status_code == 204
    assert client.get('/api/games').json() == []
    assert client.post(f'/api/games/{game["id"]}/restore').json()["archived_at"] is None


@pytest.mark.parametrize("case", ["foreign_key", "active_unique", "title", "tags", "interest", "goal_status", "duration", "json_object"])
def test_database_constraints(persistence, case):
    client, engine, _ = persistence
    game, goal = seed(client)
    with Session(engine) as db:
        if case == "foreign_key":
            db.add(Goal(game_id=99999, title="Absent", estimated_minutes=10, created_at=NOW, updated_at=NOW))
        elif case == "active_unique":
            db.add_all([session_row(game, goal), session_row(game, goal)])
        elif case in {"duration", "json_object"}:
            row = session_row(game, goal, **({"actual_duration_minutes": 0} if case == "duration" else {"recommendation_snapshot": []}))
            db.add(row)
        elif case == "goal_status":
            db.get(Goal, goal["id"]).status = "invalid"
        else:
            setattr(db.get(Game, game["id"]), {"title": "title", "tags": "experience_tags", "interest": "current_interest"}[case],
                    {"title": " ", "tags": ["invalid"], "interest": 6}[case])
        with pytest.raises(IntegrityError):
            db.commit()


def test_utc_roundtrip_non_utc_server(persistence):
    client, engine, _ = persistence
    game, _ = seed(client)
    offset = NOW.astimezone(timezone(timedelta(hours=9, minutes=30)))
    with Session(engine) as db:
        if engine.dialect.name == "postgresql":
            db.execute(text("SET TIME ZONE 'Pacific/Auckland'"))
        row = db.get(Game, game["id"])
        row.created_at = row.updated_at = offset
        db.commit()
        db.expire_all()
        assert db.get(Game, game["id"]).updated_at == NOW
        assert db.get(Game, game["id"]).updated_at.tzinfo == timezone.utc


def test_fractional_snapshot_reopen(persistence):
    client, engine, path = persistence
    pairs = []
    for title, energy, tags, interest, friction, minutes in [
        ("Iron Summit", "high", ["challenge"], 5, 2, 45),
        ("Cloud Garden", "low", ["chill", "progression"], 4, 0, 30)]:
        game = client.post('/api/games', json={**GAME, "title": title, "energy_required": energy,
                          "experience_tags": tags, "current_interest": interest, "friction": friction}).json()
        goal = client.post('/api/goals', json={"game_id": game['id'], "title": 'Advance chapter', "estimated_minutes": minutes, "priority": 3}).json()
        pairs.append((game, goal))
    context = dict(available_minutes=90, energy="high", social_preference="either", desired_experience="challenge")
    game, goal = pairs[0]
    started = client.post('/api/sessions/start', json=dict(game_id=game['id'], goal_id=goal['id'], situation=context))
    assert started.status_code == 201
    original = started.json()
    cloud = original['recommendation_snapshot']['evaluation']['ranked'][1]
    assert cloud['score'] == 70.41666666666666
    assert cloud['breakdown']['time_fit'] == 6.666666666666667
    with Session(engine) as db:
        assert db.get(PlaySession, original['id']).recommendation_snapshot == original['recommendation_snapshot']
    with TestClient(create_app(path)) as reopened:
        assert reopened.get('/api/sessions/active').json() == original
        result = reopened.post(f'/api/sessions/{original["id"]}/finish', json=sessions.FINISH)
        assert result.status_code == 200
        assert result.json()['recommendation_snapshot'] == original['recommendation_snapshot']
        assert reopened.get('/api/sessions').json() == [result.json()]


def test_migration_history_and_wrong_stream(persistence, tmp_path):
    _, engine, _ = persistence
    pg = engine.dialect.name == "postgresql"
    with pytest.raises(RuntimeError, match="stream does not match"):
        upgrade(engine, MIGRATION_DIR if pg else POSTGRESQL_MIGRATION_DIR)
    source = (POSTGRESQL_MIGRATION_DIR if pg else MIGRATION_DIR) / '001_initial.sql'
    folder = tmp_path / 'changed'
    folder.mkdir()
    for path in source.parent.glob('[0-9][0-9][0-9]_*.sql'):
        (folder / path.name).write_bytes(path.read_bytes())
    (folder / source.name).write_text(source.read_text() + '\n-- changed checksum\n')
    with pytest.raises(RuntimeError, match="history mismatch"):
        upgrade(engine, folder)
    with engine.begin() as connection:
        connection.exec_driver_sql("UPDATE schema_migrations SET checksum = 'corrupted'")
    with pytest.raises(RuntimeError, match="history mismatch"):
        require_current_schema(engine)


def test_migration_failure_rollback(persistence, tmp_path):
    _, engine, _ = persistence
    source = (POSTGRESQL_MIGRATION_DIR if engine.dialect.name == 'postgresql' else MIGRATION_DIR) / '001_initial.sql'
    folder = tmp_path / 'rollback'
    folder.mkdir()
    for path in source.parent.glob('[0-9][0-9][0-9]_*.sql'):
        (folder / path.name).write_bytes(path.read_bytes())
    prefix = '-- sidequest-dialect: postgresql\n' if engine.dialect.name == 'postgresql' else ''
    (folder / '003_failure.sql').write_text(prefix + 'CREATE TABLE must_rollback(id INTEGER);\nSELECT * FROM absent_table;\n')
    from sqlalchemy.exc import SQLAlchemyError
    with pytest.raises(SQLAlchemyError):
        upgrade(engine, folder)
    assert 'must_rollback' not in inspect(engine).get_table_names()
    require_current_schema(engine)


def test_postgresql_library_writer_blocks_lifecycle(persistence):
    client, engine, _ = persistence
    if engine.dialect.name != 'postgresql':
        pytest.skip('PostgreSQL advisory-lock-specific ordering test')
    game, goal = seed(client)
    attempted = Event()
    def observed(conn, cursor, sql, parameters, context, many):
        if 'pg_advisory_xact_lock' in sql:
            attempted.set()
    with Session(engine) as writer:
        serialize_postgresql_write(writer)
        writer.get(Game, game['id']).archived_at = NOW
        event.listen(engine, 'before_cursor_execute', observed)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(sessions.start, client, game, goal)
            try:
                assert attempted.wait(timeout=5)
                assert not pending.done()
                writer.commit()
                assert pending.result(timeout=10).status_code == 409
            finally:
                writer.rollback()
        event.remove(engine, 'before_cursor_execute', observed)
    assert client.get('/api/sessions/active').json() is None


def test_explicit_cli_and_startup_guard(persistence):
    _, engine, path = persistence
    result = subprocess.run([sys.executable, "-m", "app.migrate"],
                            capture_output=True, text=True)
    assert result.returncode == 0, "Migration CLI failed (connection details withheld)"
    assert result.stdout.strip() == "Database at migration 002"
    with engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM schema_migrations")
    with pytest.raises(RuntimeError, match="not migrated"):
        with TestClient(create_app(path)):
            pass
    with engine.connect() as connection:
        assert connection.exec_driver_sql("SELECT count(*) FROM schema_migrations").scalar_one() == 0


def test_big_integer_domain_range(persistence):
    client, _, _ = persistence
    game, _ = seed(client)
    minutes = 2 ** 40
    response = client.post('/api/goals', json=dict(game_id=game['id'], title='Large estimate',
                                                estimated_minutes=minutes))
    assert response.status_code == 201
    assert client.get('/api/goals/' + str(response.json()['id'])).json()['estimated_minutes'] == minutes


def test_production_entrypoint_real_postgresql(persistence, tmp_path):
    client, engine, _ = persistence
    if engine.dialect.name != "postgresql":
        pytest.skip("Production entrypoint requires PostgreSQL")
    from test_production_packaging import packaged_process
    seed(client)
    code = """import index, app.main
from fastapi.testclient import TestClient
assert index.app is app.main.app
with TestClient(index.app) as client:
    assert client.get('/api/games').status_code == 200
    assert len(client.get('/api/games').json()) == 1
    assert client.get('/api/missing').status_code == 404
"""
    packaged_process(tmp_path, os.environ["DATABASE_URL"], code)
