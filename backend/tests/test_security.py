import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.migrate import upgrade
from app.database import make_engine
from app.security import allowed_origins, HEADERS

@pytest.fixture
def protected(monkeypatch, tmp_path):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SIDEQUEST_DB_PATH", raising=False)
    monkeypatch.setenv("SIDEQUEST_ALLOWED_ORIGINS", "https://sidequest.example")
    path=tmp_path/'security.sqlite3'
    engine=make_engine(path); upgrade(engine); engine.dispose()
    with TestClient(create_app(path)) as client:
        yield client

@pytest.mark.parametrize('method,path', [('POST','/api/games'),('PATCH','/api/games/1'),
    ('DELETE','/api/games/1'),('POST','/api/goals/1/complete'),('POST','/api/games/1/restore'),
    ('POST','/api/sessions/start'),('POST','/api/sessions/1/finish'),('PUT','/api/missing')])
def test_missing_origin_rejected_before_mutation(protected,method,path):
    result=protected.request(method,path)
    assert result.status_code==403
    assert all(result.headers[key]==value for key,value in HEADERS.items())

@pytest.mark.parametrize('headers', [
    {'Origin':'https://evil.example'}, {'Origin':'null'},
    {'Origin':'https://sidequest.example.evil.example'},
    {'Origin':'https://sidequest.example:444'},
    {'Origin':'https://sidequest.example/path'},
    {'Origin':'http://sidequest.example'},
    {'Origin':'https://evil.example','Referer':'https://sidequest.example/'},
    {'Origin':'https://sidequest.example','Sec-Fetch-Site':'cross-site'},
    {'Referer':'https://evil.example/'},
    [('Origin','https://sidequest.example'),('Origin','https://evil.example')]])
def test_cross_origin_forms_and_spoofed_headers_rejected(protected,headers):
    result=protected.post('/api/games/1/restore',headers=headers,data={'ignored':'form'})
    assert result.status_code==403

@pytest.mark.parametrize('headers',[{'Origin':'https://sidequest.example'},
    {'Origin':'https://sidequest.example:443'}, {'Referer':'https://sidequest.example/library?view=all'}])
def test_same_origin_proceeds(protected,headers):
    assert protected.post('/api/games/999/restore',headers=headers).status_code==404

@pytest.mark.parametrize('value',['','*','https://sidequest.example/','http://evil.example',
    'https://name:password@sidequest.example','https://sidequest.example,','null'])
def test_bad_origin_configuration_fails_closed(monkeypatch,value):
    monkeypatch.setenv('SIDEQUEST_ALLOWED_ORIGINS',value)
    with pytest.raises(RuntimeError,match='explicit HTTPS origins'):
        allowed_origins()


def test_safe_api_errors_headers_and_no_cors(protected):
    result=protected.get('/api/missing')
    assert result.status_code==404 and result.headers['content-type']=='application/json'
    assert all(result.headers[key]==value for key,value in HEADERS.items())
    result=protected.options('/api/games',headers={'Origin':'https://evil.example','Access-Control-Request-Method':'POST'})
    assert 'access-control-allow-origin' not in result.headers


def test_local_default_unchanged(monkeypatch):
    monkeypatch.delenv('SIDEQUEST_ALLOWED_ORIGINS',raising=False)
    assert allowed_origins() is None
    with pytest.raises(RuntimeError): allowed_origins(required=True)
