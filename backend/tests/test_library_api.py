"""All library/persistence tests use freshly migrated, isolated file databases."""

from datetime import datetime, timedelta, timezone
from pathlib import Path
import hashlib

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from app.database import make_engine
from app.main import create_app
from app.migrate import upgrade, require_current_schema, MIGRATION_DIR
from app.models import Game, Goal, PlaySession

GAME = {"title": "Moonlit Orchard", "energy_required": "low", "social_mode": "solo",
        "experience_tags": ["progression", "chill"], "current_interest": 4, "friction": 1}
GOAL = {"title": "Harvest autumn crops", "estimated_minutes": 30, "priority": 2}
NOW = datetime(2026, 10, 3, 19, tzinfo=timezone.utc)


@pytest.fixture
def library(tmp_path):
    path = tmp_path / "library.sqlite3"
    engine = make_engine(path)
    upgrade(engine)
    engine.dispose()
    app = create_app(path)
    with TestClient(app) as client:
        yield client, app.state.engine, path


def seed(client):
    response = client.post("/api/games", json=GAME)
    assert response.status_code == 201, response.text
    game = response.json()
    response = client.post("/api/goals", json={**GOAL, "game_id": game["id"]})
    assert response.status_code == 201, response.text
    return game, response.json()


def session_row(game, goal, **changes):
    values = dict(game_id=game["id"], goal_id=goal["id"], game_title_snapshot=game["title"],
                  goal_title_snapshot=goal["title"], started_at=NOW,
                  situation_snapshot={"available_minutes": 30, "energy": "low", "social_preference": "solo", "desired_experience": "chill"},
                  recommendation_snapshot={"engine_version": "v0.1-final-004", "score": 80})
    values.update(changes)
    return PlaySession(**values)


def test_create_retrieve_and_defaults(library):
    client, engine, _ = library
    game, goal = seed(client)
    assert client.get(f'/api/games/{game["id"]}').json() == game
    assert client.get(f'/api/goals/{goal["id"]}').json() == goal
    assert client.get("/api/games").json() == [game]
    assert client.get("/api/goals", params={"game_id": game["id"]}).json() == [goal]
    assert game["experience_tags"] == ["chill", "progression"]
    assert game["created_at"].endswith("Z")
    assert goal["status"] == "active" and goal["completed_at"] is None
    assert game["created_at"] == game["updated_at"]
    defaults = client.post("/api/games", json={k:v for k,v in GAME.items() if k not in ("current_interest", "friction")}).json()
    assert defaults["current_interest"] == 3 and defaults["friction"] == 0
    with Session(engine) as db:
        persisted = db.get(Goal, goal["id"])
        assert persisted.game.title == game["title"]
        assert persisted.game.goals[0].id == goal["id"]


def test_partial_edits_and_clear_notes(library):
    client, _, _ = library
    game, goal = seed(client)
    response = client.patch(f'/api/games/{game["id"]}', json={"title": "  Updated Orchard  ", "notes": "remember the greenhouse", "current_interest": 5, "friction": 2, "social_mode": "both", "energy_required": "medium", "experience_tags": ["novelty", "chill", "chill"]})
    assert response.status_code == 200
    updated = response.json()
    assert updated["title"] == "Updated Orchard"
    assert updated["experience_tags"] == ["chill", "novelty"]
    assert updated["created_at"] == game["created_at"]
    assert updated["updated_at"] >= game["updated_at"]
    assert client.patch(f'/api/games/{game["id"]}', json={"notes": None}).json()["notes"] is None
    response = client.patch(f'/api/goals/{goal["id"]}', json={"estimated_minutes": 20, "priority": 3, "title": "Upgrade the greenhouse", "notes": "save seeds"})
    assert response.status_code == 200
    assert response.json()["game_id"] == game["id"]
    assert response.json()["priority"] == 3
    assert client.patch(f'/api/goals/{goal["id"]}', json={"notes": None}).json()["notes"] is None
    before = client.get(f'/api/goals/{goal["id"]}').json()
    assert client.patch(f'/api/goals/{goal["id"]}', json={}).json() == before


@pytest.mark.parametrize("change", [
    {"title": " "}, {"title": "x"*201}, {"title": None}, {"title": 123},
    {"current_interest": 0}, {"current_interest": 6}, {"current_interest": True}, {"current_interest": "3"},
    {"friction": -1}, {"friction": 6}, {"friction": 1.2},
    {"energy_required": "extreme"}, {"social_mode": "either"},
    {"experience_tags": []}, {"experience_tags": ["invalid"]}, {"experience_tags": [None]},
    {"experience_tags": "chill"}, {"archived_at": "2026-01-01"},
])
def test_game_validation(library, change):
    client, _, _ = library
    assert client.post("/api/games", json={**GAME, **change}).status_code == 422
    game = client.post("/api/games", json=GAME).json()
    assert client.patch(f'/api/games/{game["id"]}', json=change).status_code == 422
    assert client.get(f'/api/games/{game["id"]}').json() == game


@pytest.mark.parametrize("change", [
    {"title": "\t\n"}, {"estimated_minutes": 0}, {"estimated_minutes": -1},
    {"estimated_minutes": True}, {"estimated_minutes": "30"}, {"estimated_minutes": 2.5},
    {"priority": 0}, {"priority": 4}, {"priority": None}, {"status": "completed"},
])
def test_goal_validation(library, change):
    client, _, _ = library
    game, goal = seed(client)
    assert client.post("/api/goals", json={**GOAL, "game_id": game["id"], **change}).status_code == 422
    assert client.patch(f'/api/goals/{goal["id"]}', json=change).status_code == 422


@pytest.mark.parametrize("route", ["/api/games", "/api/goals"])
def test_required_fields(library, route):
    assert library[0].post(route, json={}).status_code == 422


def test_patch_nulls_and_immutable_relationship(library):
    client, _, _ = library
    game, goal = seed(client)
    for name in ("energy_required", "social_mode", "experience_tags", "friction"):
        assert client.patch(f'/api/games/{game["id"]}', json={name: None}).status_code == 422
    for body in ({"game_id":game["id"]}, {"completed_at":None}, {"estimated_minutes":None}):
        assert client.patch(f'/api/goals/{goal["id"]}', json=body).status_code == 422


def test_integer_storage_limits_are_validation_errors(library):
    client, _, _ = library
    game, goal = seed(client)
    assert client.post("/api/goals",json={**GOAL,"game_id":game["id"],"estimated_minutes":2**63}).status_code == 422
    assert client.post("/api/goals",json={**GOAL,"game_id":2**63}).status_code == 422
    assert client.get(f'/api/games/{2**63}').status_code == 422
    assert client.get(f'/api/goals/{2**63}').status_code == 422
    assert client.get("/api/games/0").status_code == 422
    assert client.get(f'/api/goals?game_id={2**63}').status_code == 422


def test_missing_records_and_query_validation(library):
    client, _, _ = library
    for route in ("/api/games/999", "/api/goals/999"):
        assert client.get(route).status_code == 404
        assert client.patch(route, json={"title":"missing"}).status_code == 404
        assert client.delete(route).status_code == 404
        assert client.post(route+"/restore").status_code == 404
    assert client.post("/api/goals/999/complete").status_code == 404
    assert client.post("/api/goals", json={**GOAL, "game_id": 999}).status_code == 404
    assert client.get("/api/goals?game_id=999").status_code == 404
    assert client.get("/api/goals?game_id=0").status_code == 422
    assert client.get("/api/goals?status=unknown").status_code == 422


def test_archive_game_keeps_goals_and_is_idempotent(library):
    client, engine, _ = library
    game, goal = seed(client)
    assert client.delete(f'/api/games/{game["id"]}').status_code == 204
    archived = client.get(f'/api/games/{game["id"]}').json()
    assert archived["archived_at"] is not None
    assert client.delete(f'/api/games/{game["id"]}').status_code == 204
    assert client.get(f'/api/games/{game["id"]}').json() == archived
    assert client.get("/api/games").json() == []
    assert client.get("/api/goals").json() == []
    assert client.get("/api/games?include_archived=true").json() == [archived]
    assert client.get("/api/goals?include_archived=true").json() == [goal]
    assert client.post("/api/goals", json={**GOAL, "game_id": game["id"]}).status_code == 409
    assert client.post(f'/api/goals/{goal["id"]}/complete').status_code == 409
    assert client.post(f'/api/goals/{goal["id"]}/restore').status_code == 409
    assert client.post(f'/api/games/{game["id"]}/restore').json()["archived_at"] is None
    assert client.get("/api/goals").json() == [goal]
    with Session(engine) as db:
        assert db.get(Goal, goal["id"]).status == "active"


def test_completion_archive_restore_and_filters(library):
    client, _, _ = library
    _, goal = seed(client)
    path = f'/api/goals/{goal["id"]}'
    completed = client.post(path+"/complete").json()
    assert completed["status"] == "completed" and completed["completed_at"].endswith("Z")
    assert client.post(path+"/complete").json() == completed
    assert client.get("/api/goals?status=active").json() == []
    assert client.get("/api/goals?status=completed").json() == [completed]
    assert client.delete(path).status_code == 204
    archived = client.get(path).json()
    assert archived["status"] == "archived"
    assert archived["completed_at"] == completed["completed_at"]
    client.delete(path)
    assert client.get(path).json() == archived
    assert client.post(path+"/complete").status_code == 409
    assert client.get("/api/goals").json() == []
    assert client.get("/api/goals?status=archived&include_archived=true").json() == [archived]
    restored = client.post(path+"/restore").json()
    assert restored["status"] == "active" and restored["completed_at"] is None


def test_list_order_and_game_relationship_filter(library):
    client, _, _ = library
    first, goal = seed(client)
    other = client.post("/api/games", json={**GAME,"title":"Other game"}).json()
    second = client.post("/api/goals", json={**GOAL,"game_id":other["id"]}).json()
    assert [x["id"] for x in client.get("/api/games").json()] == [first["id"],other["id"]]
    assert client.get(f'/api/goals?game_id={other["id"]}').json() == [second]


def test_foreign_keys_on_every_new_connection_and_delete_restriction(library):
    client, engine, _ = library
    game, goal = seed(client)
    for _ in range(2):
        engine.dispose()
        with engine.connect() as conn:
            assert conn.exec_driver_sql("PRAGMA foreign_keys").scalar() == 1
            assert conn.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    with Session(engine) as db:
        bad = Goal(game_id=999,title="Missing parent",estimated_minutes=30)
        db.add(bad)
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    with engine.begin() as conn:
        with pytest.raises(IntegrityError):
            conn.exec_driver_sql("DELETE FROM games WHERE id=?", (game["id"],))


@pytest.mark.parametrize("table,column,value", [
    ("games","current_interest",0), ("games","current_interest",2.5),
    ("games","friction",6), ("games","energy_required","extreme"),
    ("games","social_mode","either"), ("games","title"," "),
    ("games","experience_tags",'[]'), ("games","experience_tags",'["invalid"]'),
    ("games","experience_tags",'[null]'), ("goals","estimated_minutes",0),
    ("goals","priority",4), ("goals","status","invalid"),
    ("goals","status","completed"),
])
def test_database_constraints_without_api(library, table, column, value):
    client, engine, _ = library
    game, goal = seed(client)
    record_id = game["id"] if table == "games" else goal["id"]
    with engine.begin() as conn:
        with pytest.raises(IntegrityError):
            conn.exec_driver_sql(f"UPDATE {table} SET {column}=? WHERE id=?", (value,record_id))


def test_session_relationship_consistency_and_history_retention(library):
    client, engine, _ = library
    game, goal = seed(client)
    other = client.post("/api/games", json={**GAME,"title":"Other game"}).json()
    with Session(engine) as db:
        db.add(session_row(other,goal))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        row = session_row(game,goal,finished_at=NOW+timedelta(minutes=30),
                          actual_duration_minutes=30,enjoyment_rating=4,progress="Harvested crops",notes="Relaxing")
        db.add(row)
        db.commit()
        row_id = row.id
        assert row.goal.game.id == game["id"]
    client.patch(f'/api/games/{game["id"]}',json={"title":"Renamed"})
    client.patch(f'/api/goals/{goal["id"]}',json={"title":"Renamed goal"})
    client.delete(f'/api/games/{game["id"]}')
    client.delete(f'/api/goals/{goal["id"]}')
    with Session(engine) as db:
        row = db.get(PlaySession,row_id)
        assert row.game_title_snapshot == game["title"]
        assert row.goal_title_snapshot == goal["title"]
        assert row.recommendation_snapshot["engine_version"] == "v0.1-final-004"
        assert row.started_at == NOW
    with engine.begin() as conn:
        with pytest.raises(IntegrityError):
            conn.exec_driver_sql("DELETE FROM goals WHERE id=?",(goal["id"],))


@pytest.mark.parametrize("changes", [
    {"goal_id":999}, {"game_id":999}, {"enjoyment_rating":6},
    {"actual_duration_minutes":0}, {"finished_at":NOW-timedelta(seconds=1)},
    {"progress":None}, {"situation_snapshot":[]}, {"recommendation_snapshot":None},
])
def test_session_schema_constraints_only(library, changes):
    client, engine, _ = library
    game, goal = seed(client)
    values = dict(finished_at=NOW+timedelta(minutes=30),actual_duration_minutes=30,enjoyment_rating=4,progress="Harvested")
    values.update(changes)
    with Session(engine) as db:
        db.add(session_row(game,goal,**values))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_single_active_session_schema_constraint(library):
    client, engine, _ = library
    game, goal = seed(client)
    with Session(engine) as db:
        db.add(session_row(game,goal))
        db.commit()
        db.add(session_row(game,goal))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        assert len(db.scalars(select(PlaySession)).all()) == 1


def test_persistence_after_full_database_reopen(library):
    client, engine, path = library
    game, goal = seed(client)
    client.patch(f'/api/games/{game["id"]}',json={"notes":"Persist me"})
    client.post(f'/api/goals/{goal["id"]}/complete')
    client.delete(f'/api/games/{game["id"]}')
    with Session(engine) as db:
        db.add(session_row(game,goal,finished_at=NOW+timedelta(minutes=30),actual_duration_minutes=30,enjoyment_rating=5,progress="Finished harvest"))
        db.commit()
    engine.dispose()
    fresh_app = create_app(path)
    with TestClient(fresh_app) as fresh:
        assert fresh.get(f'/api/games/{game["id"]}').json()["notes"] == "Persist me"
        assert fresh.get(f'/api/games/{game["id"]}').json()["archived_at"] is not None
        assert fresh.get(f'/api/goals/{goal["id"]}').json()["status"] == "completed"
        with Session(fresh_app.state.engine) as db:
            assert db.scalars(select(PlaySession)).one().enjoyment_rating == 5


def test_persisted_fields_supply_frozen_candidate_without_policy_changes(library):
    from app.scoring import Candidate, recommend, SessionContext
    client, engine, _ = library
    game, goal = seed(client)
    with Session(engine) as db:
        db.add(session_row(game,goal,finished_at=NOW+timedelta(minutes=30),actual_duration_minutes=30,enjoyment_rating=4,progress="Harvested"))
        db.commit()
    engine.dispose()
    with Session(engine) as db:
        g = db.get(Game,game["id"])
        target = db.get(Goal,goal["id"])
        last = db.scalars(select(PlaySession.finished_at).where(PlaySession.game_id==g.id,PlaySession.finished_at.is_not(None)).order_by(PlaySession.finished_at.desc())).first()
        candidate = Candidate(g.id,target.id,g.title,target.title,target.estimated_minutes,g.energy_required,
                              g.social_mode,tuple(g.experience_tags),g.current_interest,target.priority,g.friction,last,
                              g.archived_at is not None,target.status)
        result = recommend([candidate],SessionContext(30,"low","solo","chill"),evaluated_at=NOW+timedelta(days=7))
        assert result.engine_version == "v0.1-final-004"
        assert result.winner.candidate == candidate


def test_naive_timestamp_rejected(library):
    client,engine,_ = library
    game,goal=seed(client)
    with Session(engine) as db:
        db.add(session_row(game,goal,started_at=NOW.replace(tzinfo=None)))
        with pytest.raises(StatementError,match="timezone aware"):
            db.commit()
        db.rollback()


def test_timezone_offset_is_normalized_and_restored_after_reopen(library):
    client,engine,path=library
    game,goal=seed(client)
    local=NOW.astimezone(timezone(timedelta(hours=-7)))
    with Session(engine) as db:
        record=session_row(game,goal,started_at=local)
        db.add(record)
        db.commit()
        key=record.id
    engine.dispose()
    fresh=make_engine(path)
    with Session(fresh) as db:
        assert db.get(PlaySession,key).started_at == NOW
        assert db.get(PlaySession,key).started_at.utcoffset() == timedelta(0)
    fresh.dispose()


def test_migrations_explicit_idempotent_and_required(tmp_path):
    engine = make_engine(tmp_path/"empty.sqlite3")
    with pytest.raises(RuntimeError,match="not migrated"):
        require_current_schema(engine)
    assert upgrade(engine) == 2
    assert upgrade(engine) == 2
    require_current_schema(engine)
    assert {"games","goals","play_sessions","schema_migrations"} == set(inspect(engine).get_table_names())
    with engine.connect() as conn:
        assert conn.exec_driver_sql("SELECT count(*) FROM schema_migrations").scalar() == 2
    engine.dispose()
    with pytest.raises(RuntimeError,match="not migrated"):
        with TestClient(create_app(tmp_path/"unmigrated.sqlite3")):
            pass


def test_migration_checksum_detects_changes(library,tmp_path):
    _,engine,_=library
    folder=tmp_path/"migrations"
    folder.mkdir()
    for path in MIGRATION_DIR.glob("[0-9][0-9][0-9]_*.sql"):
        (folder/path.name).write_bytes(path.read_bytes())
    source=(MIGRATION_DIR/"001_initial.sql").read_text(encoding="utf-8")
    (folder/"001_initial.sql").write_text(source+"\n-- Edited historical migration\n",encoding="utf-8")
    with pytest.raises(RuntimeError,match="history mismatch"):
        upgrade(engine,folder)


def test_migration_checksum_is_portable_across_line_endings(library,tmp_path):
    _,engine,_=library
    folder=tmp_path/"migrations"
    folder.mkdir()
    for path in MIGRATION_DIR.glob("[0-9][0-9][0-9]_*.sql"):
        (folder/path.name).write_bytes(path.read_bytes())
    source=(MIGRATION_DIR/"001_initial.sql").read_text(encoding="utf-8")
    (folder/"001_initial.sql").write_bytes(source.replace("\n","\r\n").encode("utf-8"))
    assert upgrade(engine,folder)==2


def test_future_revision_refused(library):
    _,engine,_=library
    with engine.begin() as conn:
        conn.exec_driver_sql("INSERT INTO schema_migrations VALUES (3, '003_unknown.sql', 'unknown', '2026-10-03T00:00:00Z')")
    with pytest.raises(RuntimeError,match="newer"):
        require_current_schema(engine)
    with pytest.raises(RuntimeError,match="newer"):
        upgrade(engine)


@pytest.mark.parametrize("bad_name",["002_first.sql","000_initial.sql"])
def test_invalid_migration_sequence_rejected(tmp_path,bad_name):
    folder=tmp_path/"migrations"
    folder.mkdir()
    (folder/bad_name).write_text("CREATE TABLE test (id INTEGER);",encoding="utf-8")
    engine=make_engine(tmp_path/"sequence.sqlite3")
    with pytest.raises(RuntimeError,match="contiguous"):
        upgrade(engine,folder)
    engine.dispose()


@pytest.mark.parametrize("previously_migrated",[False,True])
def test_failed_migration_rolls_back_ddl_and_revision(tmp_path,previously_migrated):
    engine=make_engine(tmp_path/"rollback.sqlite3")
    if previously_migrated:
        upgrade(engine)
    folder=tmp_path/"migrations"
    folder.mkdir()
    for path in MIGRATION_DIR.glob("[0-9][0-9][0-9]_*.sql"):
        (folder/path.name).write_bytes(path.read_bytes())
    (folder/"003_broken.sql").write_text("CREATE TABLE partial_write (id INTEGER);\nINVALID SQL;\n",encoding="utf-8")
    from sqlalchemy.exc import OperationalError
    with pytest.raises(OperationalError):
        upgrade(engine,folder)
    tables=set(inspect(engine).get_table_names())
    assert "partial_write" not in tables
    if previously_migrated:
        with engine.connect() as conn:
            assert conn.exec_driver_sql("SELECT count(*) FROM schema_migrations").scalar()==2
    else:
        assert tables == set()
    engine.dispose()


def test_unversioned_database_refused(tmp_path):
    engine=make_engine(tmp_path/"unknown.sqlite3")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE unrelated (id INTEGER)")
    with pytest.raises(RuntimeError,match="unversioned"):
        upgrade(engine)
    engine.dispose()


def test_scope_and_frozen_scoring(library):
    client,_,_=library
    paths=client.get("/openapi.json").json()["paths"]
    assert all(path.startswith(("/api/games","/api/goals","/api/sessions")) or path == "/api/recommendations" for path in paths)
    source=Path(__file__).resolve().parents[1]/"app/scoring.py"
    assert hashlib.sha256(source.read_bytes()).hexdigest()=="b422d327741a4d269104db1a5769ed2122a92067e1be302dd39961932f6acc1a"
