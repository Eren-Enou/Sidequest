"""Readiness contracts on isolated SQLite and opt-in loopback PostgreSQL."""
from copy import deepcopy
from datetime import timedelta
import hashlib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import MetaData, Table, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from pydantic import ValidationError

from app import scoring
from app.main import create_app
from app.migrate import upgrade, stream, checksum, require_current_schema
from app.models import Game, Goal, PlaySession
from app.recommendations import load_candidates
from app.session_routes import get_operation_time
from app.session_schemas import ReadinessRecommendationSnapshot
from test_persistence_contract import persistence
from test_library_api import GAME, GOAL, NOW
from test_sessions_api import start, finish
from test_recommendation_api import CONTEXT


def add(client, **changes):
    game = client.post('/api/games', json=GAME).json()
    goal = client.post('/api/goals', json={**GOAL, 'game_id': game['id'], **changes})
    assert goal.status_code == 201, goal.text
    return game, goal.json()


def ask(client, **changes):
    response = client.post('/api/recommendations', json={**CONTEXT, **changes})
    assert response.status_code == 200
    return response.json()


def patch(client, goal, **changes):
    return client.patch(f'/api/goals/{goal["id"]}', json=changes)


@pytest.mark.parametrize('readiness', ['omitted', 'current', 'later'])
def test_creation_defaults_and_explicit_readiness(persistence, readiness):
    client, _, _ = persistence
    _, goal = add(client, **({} if readiness == 'omitted' else {'readiness': readiness}))
    assert goal['readiness'] == ('current' if readiness == 'omitted' else readiness)
    assert client.get(f'/api/goals/{goal["id"]}').json() == goal
    assert client.get('/api/goals').json() == [goal]


@pytest.mark.parametrize('invalid', [None, '', 'active', 'CURRENT', 1, True, ['later']])
def test_validation_both_create_and_patch(persistence, invalid):
    client, _, _ = persistence
    game, goal = add(client)
    assert client.post('/api/goals', json={**GOAL, 'game_id': game['id'], 'readiness': invalid}).status_code == 422
    assert patch(client, goal, readiness=invalid).status_code == 422
    assert client.get(f'/api/goals/{goal["id"]}').json() == goal


def test_explicit_moves_and_unrelated_edits(persistence):
    client, _, _ = persistence
    _, goal = add(client)
    assert patch(client, goal, readiness='later').json()['readiness'] == 'later'
    assert patch(client, goal, title='New title', notes='Keep for later', priority=3,
                 estimated_minutes=20).json()['readiness'] == 'later'
    assert patch(client, goal).json()['readiness'] == 'later'
    assert patch(client, goal, readiness='current').json()['readiness'] == 'current'


def test_later_readiness_survives_application_reopen(persistence):
    client, _, path = persistence
    _, goal = add(client, readiness='later')
    app = create_app(path)
    with TestClient(app) as reopened:
        assert reopened.get(f'/api/goals/{goal["id"]}').json() == goal
        assert ask(reopened)['status'] == 'no_eligible'
        assert 'later' in ask(reopened)['excluded'][0]['reasons'][0]


def test_parallel_current_later_priority_and_pre_scoring_boundary(persistence, monkeypatch):
    client, engine, _ = persistence
    game, current = add(client, priority=1)
    another = client.post('/api/goals', json={**GOAL, 'game_id': game['id'], 'priority': 1}).json()
    later = [client.post('/api/goals', json={**GOAL, 'game_id': game['id'],
                 'readiness': 'later', 'priority': 3}).json() for _ in range(2)]
    original = scoring.recommend
    seen = []
    def spy(candidates, *args, **kwargs):
        values = tuple(candidates)
        seen.extend(c.goal_id for c in values)
        return original(values, *args, **kwargs)
    monkeypatch.setattr(scoring, 'recommend', spy)
    before = ask(client)
    assert seen == [current['id'], another['id']]
    assert before == ask(client)
    assert before['status'] == 'multiple_equivalent'
    assert [r['candidate']['goal_id'] for r in before['recommendations']] == [current['id'], another['id']]
    assert {r['candidate']['goal_id'] for r in before['excluded']} == {g['id'] for g in later}
    assert all('later' in r['reasons'][0] and 'score' not in r for r in before['excluded'])
    with Session(engine) as db:
        direct = original(load_candidates(db), scoring.SessionContext(**CONTEXT), evaluated_at=NOW)
    assert [r['score'] for r in before['ranked']] == [r.score for r in direct.ranked]
    assert before['eligibility_version'] == 'goal-readiness-020'
    assert before['engine_version'] == 'v0.1-final-004'


def test_current_time_exclusion_does_not_promote_later(persistence):
    client, _, _ = persistence
    game, current = add(client, estimated_minutes=120)
    later = client.post('/api/goals', json={**GOAL, 'game_id': game['id'], 'estimated_minutes': 20,
                                          'priority': 3, 'readiness': 'later'}).json()
    result = ask(client, available_minutes=30)
    assert result['status'] == 'no_eligible' and result['ranked'] == []
    exclusions = {r['candidate']['goal_id']: r['reasons'] for r in result['excluded']}
    assert '120' in exclusions[current['id']][0]
    assert 'later' in exclusions[later['id']][0]


@pytest.mark.parametrize('status', ['completed', 'archived', 'parent_archived'])
@pytest.mark.parametrize('readiness', ['current', 'later'])
def test_lifecycle_authoritative_and_restore_current(persistence, status, readiness):
    client, _, _ = persistence
    game, goal = add(client, readiness=readiness)
    if status == 'completed':
        assert client.post(f'/api/goals/{goal["id"]}/complete').status_code == 200
    elif status == 'archived':
        assert client.delete(f'/api/goals/{goal["id"]}').status_code == 204
    else:
        assert client.delete(f'/api/games/{game["id"]}').status_code == 204
    result = ask(client)
    assert result['status'] == 'no_eligible' and not result['ranked']
    assert ('archived' if status == 'parent_archived' else status) in ' '.join(result['excluded'][0]['reasons']).lower()
    if status != 'parent_archived':
        assert patch(client, goal, readiness='later').status_code == 409
        reopened = client.post(f'/api/goals/{goal["id"]}/restore').json()
        assert reopened['status'] == 'active' and reopened['readiness'] == 'current'
        assert reopened['completed_at'] is None
    else:
        assert client.post(f'/api/goals/{goal["id"]}/restore').status_code == 409
        client.post(f'/api/games/{game["id"]}/restore')
        assert client.get(f'/api/goals/{goal["id"]}').json()['readiness'] == readiness


def test_stale_start_rechecks_readiness(persistence):
    client, engine, _ = persistence
    game, goal = add(client)
    assert ask(client)['winner']['candidate']['goal_id'] == goal['id']
    assert patch(client, goal, readiness='later').status_code == 200
    response = start(client, game, goal)
    assert response.status_code == 409
    assert 'later' in response.json()['detail']['recommendation']['excluded'][0]['reasons'][0]
    with Session(engine) as db:
        assert db.scalars(select(PlaySession)).all() == []


@pytest.mark.parametrize('mark_complete', [False, True])
def test_active_finish_history_and_outcomes_survive_readiness_change(persistence, mark_complete):
    client, engine, _ = persistence
    game, goal = add(client)
    row = start(client, game, goal).json()
    assert row['recommendation_snapshot']['snapshot_version'] == 2
    snapshot = deepcopy(row['recommendation_snapshot'])
    assert patch(client, goal, readiness='later').status_code == 200
    assert client.get('/api/sessions/active').json() == row
    saved = finish(client, row, mark_goal_completed=mark_complete)
    assert saved.status_code == 200
    assert saved.json()['recommendation_snapshot'] == snapshot
    outcomes = client.get(f'/api/games/{game["id"]}/outcomes').json()
    assert patch(client, goal, title='Renamed objective').status_code == 200
    if not mark_complete:
        assert patch(client, goal, readiness='current').status_code == 200
    assert client.get(f'/api/games/{game["id"]}/outcomes').json() == outcomes
    assert client.get('/api/sessions').json()[0]['recommendation_snapshot'] == snapshot
    # Load an actual old-format saved row, without fabricated historical readiness.
    old = deepcopy(snapshot)
    old['snapshot_version'] = 1
    del old['evaluation']['eligibility_version']
    with Session(engine) as db:
        stored = db.get(PlaySession, row['id'])
        stored.recommendation_snapshot = old
        db.commit()
    assert client.get('/api/sessions').json()[0]['recommendation_snapshot'] == old
    assert client.get(f'/api/games/{game["id"]}/outcomes').json() == outcomes


@pytest.mark.parametrize('invalid', [None, 'ready'])
def test_database_constraint(persistence, invalid):
    client, engine, _ = persistence
    _, goal = add(client)
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(Goal.__table__.update().where(Goal.id == goal['id']).values(readiness=invalid))


def test_version_two_requires_explicit_eligibility_marker(persistence):
    client, _, _ = persistence
    game, goal = add(client)
    row = start(client, game, goal).json()
    snapshot = deepcopy(row['recommendation_snapshot'])
    del snapshot['evaluation']['eligibility_version']
    with pytest.raises(ValidationError):
        ReadinessRecommendationSnapshot.model_validate(snapshot)


def test_pre_readiness_migration_preserves_existing_data(persistence, tmp_path):
    client, engine, path = persistence
    game, goal = add(client)
    first = start(client, game, goal).json()
    assert finish(client, first).status_code == 200
    client.app.dependency_overrides[get_operation_time] = lambda: NOW + timedelta(minutes=31)
    second = start(client, game, goal).json()
    assert 'id' in second
    completed = client.post('/api/goals', json={**GOAL, 'game_id': game['id']}).json()
    client.post(f'/api/goals/{completed["id"]}/complete')
    archived = client.post('/api/goals', json={**GOAL, 'game_id': game['id']}).json()
    client.delete(f'/api/goals/{archived["id"]}')
    # Capture representative real records, then seed an actual 001-only schema.
    with engine.begin() as conn:
        data = {model.__tablename__: [dict(r) for r in conn.execute(select(model.__table__).order_by(model.id)).mappings()]
                for model in (Game, Goal, PlaySession)}
        for r in data['goals']: del r['readiness']
        for r in data['play_sessions']:
            r['recommendation_snapshot']['snapshot_version'] = 1
            del r['recommendation_snapshot']['evaluation']['eligibility_version']
        for table in ('play_sessions', 'goals', 'games', 'schema_migrations'):
            conn.exec_driver_sql(f'DROP TABLE {table}')
    folder = tmp_path/'old-stream'
    folder.mkdir()
    initial = stream(engine)[0]
    (folder/initial.name).write_bytes(initial.read_bytes())
    assert upgrade(engine, folder) == 1
    metadata = MetaData()
    with engine.begin() as conn:
        for model in (Game, Goal, PlaySession):
            table = Table(model.__tablename__, metadata, autoload_with=conn)
            for column in table.columns:
                column.type = model.__table__.c[column.name].type
            conn.execute(table.insert(), data[model.__tablename__])
        old_history = tuple(conn.exec_driver_sql('SELECT version,name,checksum FROM schema_migrations').first())
    with pytest.raises(RuntimeError, match='not migrated'):
        require_current_schema(engine)
    assert upgrade(engine) == 2 and upgrade(engine) == 2
    require_current_schema(engine)
    with engine.connect() as conn:
        for model in (Game, Goal, PlaySession):
            rows = [dict(r) for r in conn.execute(select(model.__table__).order_by(model.id)).mappings()]
            if model is Goal:
                assert all(r.pop('readiness') == 'current' for r in rows)
            assert rows == data[model.__tablename__]
        assert tuple(conn.exec_driver_sql('SELECT version,name,checksum FROM schema_migrations WHERE version=1').first()) == old_history
        for version, name, value in conn.exec_driver_sql('SELECT version,name,checksum FROM schema_migrations'):
            assert value == checksum(stream(engine)[version-1])
    assert client.get('/api/sessions/active').status_code == 200
    assert client.get('/api/sessions').status_code == 200
    # The populated migration retained the database's single-active-session index.
    duplicate = deepcopy(data['play_sessions'][1])
    duplicate['id'] = 999
    with pytest.raises(IntegrityError):
        with engine.begin() as conn:
            conn.execute(PlaySession.__table__.insert(), duplicate)
    # Compare against the frozen engine, not a new expected ranking implementation.
    with Session(engine) as db:
        direct = scoring.recommend(load_candidates(db), scoring.SessionContext(**CONTEXT), evaluated_at=NOW)
    result = ask(client)
    assert [r['score'] for r in result['ranked']] == [r.score for r in direct.ranked]


def test_frozen_scorer():
    assert hashlib.sha256(Path(scoring.__file__).read_bytes()).hexdigest() == 'b422d327741a4d269104db1a5769ed2122a92067e1be302dd39961932f6acc1a'
