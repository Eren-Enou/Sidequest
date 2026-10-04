"""Production ASGI entrypoint; the local Uvicorn entrypoint remains app.main:app."""
from app.database import database_configuration

# Fail before importing main (and before SQLite directory creation) if misconfigured.
if database_configuration().dialect != "postgresql":
    raise RuntimeError("Production entrypoint requires a PostgreSQL DATABASE_URL")

from app.main import app  # noqa: E402,F401 -- reuse the canonical application
