"""Local library/recommendation API; database migration is an explicit prerequisite."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import sessionmaker

from app.database import make_engine
from app.migrate import require_current_schema
from app.routes import router


def create_app(path=None):
    engine = make_engine(path)

    @asynccontextmanager
    async def lifespan(app):
        try:
            require_current_schema(engine)
            yield
        finally:
            engine.dispose()

    application = FastAPI(title="Sidequest API", version="0.1", lifespan=lifespan)
    application.state.engine = engine
    application.state.sessions = sessionmaker(engine, expire_on_commit=False)
    application.include_router(router)

    @application.exception_handler(IntegrityError)
    async def integrity_error(request: Request, error: IntegrityError):
        return JSONResponse(status_code=409, content={"detail": "Write conflicts with database relationships or constraints"})

    @application.exception_handler(OperationalError)
    async def operational_error(request: Request, error: OperationalError):
        if "locked" in str(error.orig).lower():
            return JSONResponse(status_code=503, content={"detail": "Database is busy; retry the request"})
        raise error

    return application


app = create_app()
