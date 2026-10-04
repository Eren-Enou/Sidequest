"""Fictional read-only SQLite transfer and real PostgreSQL logical recovery."""
from contextlib import ExitStack
from datetime import timedelta
import hashlib
import os
from pathlib import Path
from uuid import uuid4
import shutil

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text, inspect
from app.database import make_engine
from app.main import create_app
from app.migrate import upgrade, require_current_schema
from app.maintenance import (MaintenanceError, readonly_sqlite, destination_engine, transfer,
                             backup, restore, records, digest, client_environment, postgres_url)
from app.routes import get_evaluation_time
from app.session_routes import get_operation_time
from test_library_api import NOW, GAME


@pytest.fixture
def pg_databases(monkeypatch):
    value=os.environ.get('SIDEQUEST_TEST_POSTGRES_URL')
    if not value: pytest.skip('Real isolated local PostgreSQL is required')
    url=postgres_url(value)
    if url.host not in {'localhost','127.0.0.1','::1'}:
        pytest.fail('Maintenance tests require a disposable loopback cluster',pytrace=False)
    names=[]; engines=[]
    def create(migrate=True):
        name='sidequest_test_'+uuid4().hex
        try:
            with psycopg.connect(url.set(drivername='postgresql').render_as_string(hide_password=False),autocommit=True) as admin:
                admin.execute(psycopg.sql.SQL('CREATE DATABASE {}').format(psycopg.sql.Identifier(name)))
        except Exception: pytest.fail('Cannot create isolated maintenance database',pytrace=False)
        names.append(name)
        target=url.set(database=name).render_as_string(hide_password=False)
        engine=destination_engine(target); engines.append(engine)
        if migrate: upgrade(engine)
        return target,engine
    yield create
    for engine in engines: engine.dispose()
    for name in names:
        with psycopg.connect(url.set(drivername='postgresql').render_as_string(hide_password=False),autocommit=True) as admin:
            admin.execute(psycopg.sql.SQL('DROP DATABASE {} WITH (FORCE)').format(psycopg.sql.Identifier(name)))


def configured_app(monkeypatch, path=None, url=None):
    monkeypatch.delenv('DATABASE_URL',raising=False)
    monkeypatch.delenv('SIDEQUEST_DB_PATH',raising=False)
    monkeypatch.delenv('SIDEQUEST_ALLOWED_ORIGINS',raising=False)
    if url: monkeypatch.setenv('DATABASE_URL',url)
    app=create_app(path)
    app.dependency_overrides[get_evaluation_time]=lambda: NOW
    app.dependency_overrides[get_operation_time]=lambda: NOW
    return app


@pytest.fixture
def fictional_source(monkeypatch,tmp_path):
    monkeypatch.delenv('DATABASE_URL',raising=False)
    monkeypatch.delenv('SIDEQUEST_DB_PATH',raising=False)
    monkeypatch.delenv('SIDEQUEST_ALLOWED_ORIGINS',raising=False)
    monkeypatch.setattr('app.routes.utcnow',lambda: NOW-timedelta(days=2))
    path=tmp_path/'source.sqlite3'
    engine=make_engine(path); upgrade(engine);engine.dispose()
    app=configured_app(monkeypatch,path)
    with TestClient(app) as client:
        pairs=[]
        for title,energy,tags,interest,friction,minutes in [
            ('Iron Summit','high',['challenge'],5,2,45),
            ('Cloud Garden','low',['chill','progression'],4,0,30),
            ('Old Harbor','low',['novelty'],3,1,20)]:
            game=client.post('/api/games',json={**GAME,'title':title,'energy_required':energy,
                'experience_tags':tags,'current_interest':interest,'friction':friction,'notes':'Fictional note'}).json()
            goal=client.post('/api/goals',json=dict(game_id=game['id'],title='Advance chapter',estimated_minutes=minutes,priority=3)).json()
            pairs.append((game,goal))
        context=dict(available_minutes=90,energy='high',social_preference='either',desired_experience='challenge')
        game,goal=pairs[0]
        for i in range(2):
            instant=NOW-timedelta(days=1)+timedelta(hours=i)
            app.dependency_overrides[get_operation_time]=lambda instant=instant: instant
            response=client.post('/api/sessions/start',json=dict(game_id=game['id'],goal_id=goal['id'],situation=context))
            assert response.status_code==201
            ranked=response.json()['recommendation_snapshot']['evaluation']['ranked']
            cloud=next(row for row in ranked if row['candidate']['game_id']==pairs[1][0]['id'])
            assert cloud['breakdown']['time_fit']==6.666666666666667
            app.dependency_overrides[get_operation_time]=lambda instant=instant: instant+timedelta(minutes=30)
            finished=client.post('/api/sessions/'+str(response.json()['id'])+'/finish',json=dict(
                actual_duration_minutes=30,enjoyment_rating=4,progress='Advanced fictional chapter',notes='Saved evidence',mark_goal_completed=i==1))
            assert finished.status_code==200
        assert client.post('/api/goals/'+str(pairs[2][1]['id'])+'/complete').status_code==200
        extra=client.post('/api/goals',json=dict(game_id=pairs[2][0]['id'],title='Archived objective',estimated_minutes=10)).json()
        assert client.delete('/api/goals/'+str(extra['id'])).status_code==204
        assert client.delete('/api/games/'+str(pairs[2][0]['id'])).status_code==204
        app.dependency_overrides[get_operation_time]=lambda: NOW
        game,goal=pairs[1]
        result=client.post('/api/sessions/start',json=dict(game_id=game['id'],goal_id=goal['id'],situation=dict(
            available_minutes=60,energy='low',social_preference='solo',desired_experience='chill')))
        assert result.status_code==201
        expected={endpoint:client.get(endpoint,params={'include_archived':True}).json() for endpoint in (
            '/api/games','/api/goals','/api/sessions','/api/sessions/active')}
        before=client.post('/api/recommendations',json=context).json()
    source=readonly_sqlite(path)
    yield path,source,expected,context,before
    source.dispose()


def verify_application(monkeypatch,url,expected,context,before):
    app=configured_app(monkeypatch,url=url)
    with TestClient(app) as client:
        for endpoint,data in expected.items():
            assert client.get(endpoint,params={'include_archived':True}).json()==data
        assert client.post('/api/recommendations',json=context).json()==before
        active=client.get('/api/sessions/active').json()
        assert active
        app.dependency_overrides[get_operation_time]=lambda: NOW+timedelta(minutes=30)
        assert client.post('/api/sessions/'+str(active['id'])+'/finish',json=dict(
            actual_duration_minutes=30,enjoyment_rating=5,progress='Recovered session')).status_code==200
        assert client.get('/api/sessions/active').json() is None
        game=client.post('/api/games',json=GAME).json()
        assert game['id']>max(row['id'] for row in expected['/api/games'])
        goal=client.post('/api/goals',json=dict(game_id=game['id'],title='New goal',estimated_minutes=30)).json()
        assert goal['id']>max(row['id'] for row in expected['/api/goals'])
        app.dependency_overrides[get_operation_time]=lambda: NOW+timedelta(hours=1)
        app.dependency_overrides[get_evaluation_time]=lambda: NOW+timedelta(hours=1)
        situation=dict(available_minutes=60,energy='low',social_preference='solo',desired_experience='chill')
        recommendation=client.post('/api/recommendations',json=situation).json()
        chosen=recommendation['winner']['candidate']
        assert any(row['breakdown']['recent_play']<0 for row in recommendation['ranked'])
        started=client.post('/api/sessions/start',json=dict(game_id=chosen['game_id'],goal_id=chosen['goal_id'],situation=situation))
        assert started.status_code==201
        assert started.json()['id']>max([active['id']]+[r['id'] for r in expected['/api/sessions']])
        assert client.post('/api/sessions/'+str(started.json()['id'])+'/finish',json=dict(
            actual_duration_minutes=20,enjoyment_rating=4,progress='New recovered write')).status_code==200


def test_real_transfer_application_and_source_preserved(fictional_source,pg_databases,monkeypatch):
    path,source,expected,context,before=fictional_source
    prior=hashlib.sha256(path.read_bytes()).hexdigest()
    url,target=pg_databases()
    result=transfer(source,target)
    assert result['counts']==dict(games=3,goals=4,play_sessions=3)
    with source.connect() as a,target.connect() as b:
        assert records(a)==records(b)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==prior
    verify_application(monkeypatch,url,expected,context,before)


def test_dry_run_and_identity_rollback(fictional_source,pg_databases):
    _,source,*_=fictional_source
    _,target=pg_databases()
    result=transfer(source,target,dry_run=True)
    assert result['dry_run']
    with target.connect() as connection:
        assert all(not rows for rows in records(connection).values())
        assert connection.exec_driver_sql("SELECT last_value, is_called FROM games_id_seq").one()==(1,False)
    assert transfer(source,target)['counts']==result['counts']


def test_transfer_injected_failure_rolls_back(fictional_source,pg_databases):
    _,source,*_=fictional_source
    _,target=pg_databases()
    def fail(conn,cursor,statement,parameters,context,many):
        if statement.startswith('INSERT INTO play_sessions'): raise RuntimeError('synthetic private failure')
    event.listen(target,'before_cursor_execute',fail)
    try:
        with pytest.raises(MaintenanceError,match='rolled back'): transfer(source,target)
    finally: event.remove(target,'before_cursor_execute',fail)
    with target.connect() as connection: assert all(not rows for rows in records(connection).values())
    assert transfer(source,target)['counts']['play_sessions']==3


def test_nonempty_destination_refused(fictional_source,pg_databases):
    _,source,*_=fictional_source
    _,target=pg_databases();transfer(source,target)
    with target.connect() as connection: prior=digest(records(connection))
    with pytest.raises(MaintenanceError,match='empty'):transfer(source,target)
    with target.connect() as connection: assert digest(records(connection))==prior


@pytest.mark.parametrize('case',['unmigrated','checksum','extra_table'])
def test_incompatible_destination_refused(fictional_source,pg_databases,case):
    _,source,*_=fictional_source
    _,target=pg_databases(migrate=case!='unmigrated')
    if case=='checksum':
        with target.begin() as conn: conn.exec_driver_sql("UPDATE schema_migrations SET checksum='bad'")
    if case=='extra_table':
        with target.begin() as conn: conn.exec_driver_sql('CREATE TABLE foreign_data(id INTEGER)')
    with pytest.raises(MaintenanceError):transfer(source,target)


@pytest.mark.parametrize('source_dialect,destination_dialect',[('sqlite','sqlite'),('postgresql','postgresql'),('postgresql','sqlite')])
def test_wrong_dialects_refused_without_connect(source_dialect,destination_dialect):
    from types import SimpleNamespace
    a=SimpleNamespace(dialect=SimpleNamespace(name=source_dialect))
    b=SimpleNamespace(dialect=SimpleNamespace(name=destination_dialect))
    with pytest.raises(MaintenanceError,match='SQLite source'):transfer(a,b)


def test_readonly_source_and_missing_file(tmp_path):
    with pytest.raises(MaintenanceError):readonly_sqlite(tmp_path/'missing.sqlite3')
    assert not (tmp_path/'missing.sqlite3').exists()
    path=tmp_path/'readonly.sqlite3';path.touch()
    engine=readonly_sqlite(path)
    try:
        with engine.connect() as connection:
            with pytest.raises(Exception):connection.exec_driver_sql('CREATE TABLE forbidden(id INTEGER)')
    finally:engine.dispose()


def pg_bin():
    directory=os.environ.get('SIDEQUEST_TEST_PG_BIN')
    if directory:return directory
    known=Path('C:/Program Files/PostgreSQL/16/bin')
    if known.is_dir():return known
    if shutil.which('pg_dump') and shutil.which('pg_restore'):return None
    pytest.skip('Actual pg_dump/pg_restore tools required')


def test_real_backup_restore_and_application(fictional_source,pg_databases,monkeypatch,tmp_path):
    _,source,expected,context,before=fictional_source
    url,target=pg_databases();transfer(source,target)
    with target.connect() as connection: prior=digest(records(connection))
    dump=backup(url,tmp_path,pg_bin())
    archive=tmp_path/dump['file']
    assert archive.is_file() and dump['bytes']>0
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==dump['sha256']
    restored_url,restored=pg_databases(migrate=False)
    result=restore(restored_url,archive,pg_bin())
    assert result['sha256']==prior
    require_current_schema(restored)
    verify_application(monkeypatch,restored_url,expected,context,before)


def test_restore_nonempty_refused(fictional_source,pg_databases,tmp_path):
    _,source,*_=fictional_source
    url,target=pg_databases();transfer(source,target)
    dump=backup(url,tmp_path,pg_bin())
    with pytest.raises(MaintenanceError,match='empty'):restore(url,tmp_path/dump['file'],pg_bin())


def test_bad_archive_restore_rolls_back(pg_databases,tmp_path):
    url,target=pg_databases(migrate=False)
    archive=tmp_path/'invalid.dump';archive.write_bytes(b'not an archive')
    with pytest.raises(MaintenanceError):restore(url,archive,pg_bin())
    assert inspect(target).get_table_names()==[]


def test_client_environment_no_credentials_in_arguments(monkeypatch):
    monkeypatch.setenv('PGSERVICE','wrong_service')
    env=client_environment('postgresql://owner:synthetic-secret@localhost/sample?sslmode=require')
    assert env['PGPASSWORD']=='synthetic-secret' and env['PGSSLMODE']=='require'
    assert 'PGSERVICE' not in env
    for value in ['not a URL','sqlite:///private.sqlite3','postgresql://owner:synthetic-secret@localhost/sample?unknown=1']:
        with pytest.raises(MaintenanceError) as caught:client_environment(value)
        assert 'synthetic-secret' not in str(caught.value)


@pytest.mark.parametrize('damage',['history','snapshot'])
def test_invalid_source_refused_and_destination_empty(fictional_source,pg_databases,damage):
    path,source,*_=fictional_source
    import sqlite3
    with sqlite3.connect(path) as connection:
        if damage=='history': connection.execute("UPDATE schema_migrations SET checksum='bad'")
        else: connection.execute("UPDATE play_sessions SET recommendation_snapshot='{}'")
    _,target=pg_databases()
    with pytest.raises(MaintenanceError):transfer(source,target)
    with target.connect() as connection: assert all(not rows for rows in records(connection).values())


def test_real_transfer_cli_dry_run(fictional_source,pg_databases):
    import subprocess,sys,json
    path,_,*_=fictional_source
    url,target=pg_databases()
    env=os.environ.copy();env['SIDEQUEST_MAINTENANCE_DATABASE_URL']=url
    result=subprocess.run([sys.executable,'-m','app.maintenance','transfer','--source',str(path),'--dry-run'],
                          env=env,capture_output=True,text=True)
    if result.returncode:pytest.fail('Maintenance CLI failed (private details withheld)',pytrace=False)
    assert json.loads(result.stdout)['counts']==dict(games=3,goals=4,play_sessions=3)
    with target.connect() as connection: assert all(not rows for rows in records(connection).values())


def test_backup_failure_removes_partial_output(pg_databases,tmp_path,monkeypatch):
    url,_=pg_databases()
    def fail(*args,**kwargs): raise MaintenanceError('Synthetic client failure')
    monkeypatch.setattr('app.maintenance.run',fail)
    with pytest.raises(MaintenanceError):backup(url,tmp_path,pg_bin())
    assert list(tmp_path.glob('*.dump'))==[]


def test_backup_does_not_overwrite(pg_databases,tmp_path,monkeypatch):
    url,_=pg_databases()
    from datetime import datetime
    class Fixed:
        @staticmethod
        def now(tz):return NOW
    monkeypatch.setattr('app.maintenance.datetime',Fixed)
    dump=backup(url,tmp_path,pg_bin()); archive=tmp_path/dump['file']; prior=archive.read_bytes()
    with pytest.raises(MaintenanceError,match='preserved'):backup(url,tmp_path,pg_bin())
    assert archive.read_bytes()==prior


def test_backup_refuses_repository_destination():
    from app.database import BACKEND_ROOT
    with pytest.raises(MaintenanceError,match='outside'):
        backup('postgresql://owner:synthetic@localhost/sample',BACKEND_ROOT)
