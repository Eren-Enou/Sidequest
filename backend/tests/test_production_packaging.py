"""Production service-root imports and public routing contracts, without deployment."""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy.pool import NullPool, QueuePool
from app.database import make_engine

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / "vercel.json").read_text())


def service_for(path):
    for rule in CONFIG["rewrites"]:
        if re.fullmatch(rule["source"], path):
            return rule["destination"]["service"]
    return None


@pytest.mark.parametrize("path", ["/api", "/api/", "/api/games", "/api/sessions/42/finish", "/api/missing"])
def test_api_cannot_reach_spa(path):
    assert service_for(path) == "backend"
    fallback = CONFIG["services"]["frontend"]["rewrites"][0]["source"]
    assert not re.fullmatch(fallback, path)


@pytest.mark.parametrize("path", ["/", "/library", "/history/42", "/apiculture"])
def test_frontend_navigation_fallback(path):
    assert service_for(path) == "frontend"
    assert re.fullmatch(CONFIG["services"]["frontend"]["rewrites"][0]["source"], path)


def test_assets_do_not_use_spa():
    path = "/assets/missing.js"
    assert service_for(path) == "frontend"
    assert not re.fullmatch(CONFIG["services"]["frontend"]["rewrites"][0]["source"], path)
    assert CONFIG["services"]["frontend"]["outputDirectory"] == "dist"
    assert CONFIG["services"]["frontend"]["buildCommand"] == "npm run build"
    assert json.loads((ROOT / "frontend/package.json").read_text())["scripts"]["build"] == "vite build"


def packaged_process(tmp_path, url, code):
    destination = tmp_path / "package" / "backend"
    shutil.copytree(ROOT / "backend/app", destination / "app", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copytree(ROOT / "backend/migrations", destination / "migrations")
    shutil.copy(ROOT / "backend/index.py", destination / "index.py")
    cwd = tmp_path / "unrelated"
    cwd.mkdir()
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("SIDEQUEST_DB_PATH", None)
    env.pop("DATABASE_URL", None)
    if url:
        env["DATABASE_URL"] = url
    env["SIDEQUEST_POSTGRES_POOL"] = "null"
    source = "import sys; sys.dont_write_bytecode=True; sys.path.insert(0, " + repr(str(destination)) + ");\n" + code
    result = subprocess.run([sys.executable, "-I", "-c", source], cwd=cwd, env=env,
                            capture_output=True, text=True)
    if result.returncode != 0:
        pytest.fail("Packaged import failed (connection details withheld)", pytrace=False)
    assert not (destination / "data").exists()
    assert not list(destination.rglob("*.sqlite3"))
    return result.stdout


def test_packaged_import_identity_resources_no_writes(tmp_path):
    code = ("from pathlib import Path; from unittest.mock import patch; "
            "guard=patch.object(Path, 'mkdir', side_effect=AssertionError('runtime write')); guard.start(); "
            "import index, app.main, psycopg, pydantic, sqlalchemy, fastapi; "
            "from app.migrate import stream; "
            "assert index.app is app.main.app; "
            "assert index.app.state.engine.dialect.name=='postgresql'; "
            "files=stream(index.app.state.engine); assert len(files)==1 and files[0].is_absolute(); "
            "assert files[0].read_text().startswith('-- sidequest-dialect: postgresql'); "
            "from sqlalchemy.pool import NullPool; assert isinstance(index.app.state.engine.pool, NullPool); "
            "index.app.state.engine.dispose()")
    packaged_process(tmp_path, "postgresql://sample:synthetic@127.0.0.1:1/sample", code)


@pytest.mark.parametrize("url", [None, "sqlite:///data/forbidden.sqlite3"])
def test_production_entrypoint_refuses_local_fallback(tmp_path, url):
    code = """try:
    import index
except RuntimeError as error:
    assert str(error) == 'Production entrypoint requires a PostgreSQL DATABASE_URL'
else:
    raise AssertionError('must reject local persistence')
"""
    packaged_process(tmp_path, url, code)


@pytest.mark.parametrize("profile,kind", [("queue", QueuePool), ("null", NullPool)])
def test_pool_configuration_preserves_local_default(monkeypatch, profile, kind):
    monkeypatch.delenv("SIDEQUEST_DB_PATH", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://sample:synthetic@localhost/sample")
    monkeypatch.setenv("SIDEQUEST_POSTGRES_POOL", profile)
    engine = make_engine()
    assert isinstance(engine.pool, kind)
    engine.dispose()


def test_invalid_pool_profile_is_secret_safe(monkeypatch):
    monkeypatch.delenv("SIDEQUEST_DB_PATH", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql://sample:synthetic@localhost/sample")
    monkeypatch.setenv("SIDEQUEST_POSTGRES_POOL", "invalid")
    with pytest.raises(RuntimeError) as error:
        make_engine()
    assert "synthetic" not in str(error.value)


def test_configuration_has_no_secrets_or_migration_build():
    assert "env" not in CONFIG and "builds" not in CONFIG and "routes" not in CONFIG
    assert "DATABASE_URL" not in json.dumps(CONFIG)
    assert "migrate" not in json.dumps(CONFIG)
    assert CONFIG["services"]["backend"]["entrypoint"] == "index:app"
    assert (ROOT / "backend/.python-version").read_text().strip() == "3.12"
    assert not (ROOT / "requirements.txt").exists()  # existing service manifest is authoritative
