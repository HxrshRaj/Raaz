from __future__ import annotations

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from . import db as dbmod
from . import metrics
from .api.v1 import router as v1_router
from .config import get_settings
from .errors import install_handlers
from .logging_setup import configure_logging, get_logger

log = get_logger("raaz")


def init_database() -> None:
    """Dev/test convenience: create tables when using SQLite. Production uses `alembic upgrade head`."""
    from .engine.game import ensure_catalog
    from .models import Base  # noqa: F401  (import registers all tables)

    s = get_settings()
    if dbmod.engine.dialect.name == "sqlite" or s.env == "test":
        dbmod.Base.metadata.create_all(dbmod.engine)
    with dbmod.SessionLocal() as db:
        ensure_catalog(db)
        from .rag.ingest import ensure_case_corpus

        ensure_case_corpus(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    s = get_settings()
    s.validate_for_runtime()
    configure_logging()
    init_database()
    log.info("raaz started", extra={"env": s.env, "db": dbmod.engine.dialect.name, "llm": s.llm_provider})
    yield
    from .jobs import shutdown_jobs

    shutdown_jobs()
    log.info("raaz stopped")


def create_app() -> FastAPI:
    s = get_settings()
    app = FastAPI(
        title="RAAZ: The AI Detective API", version="0.1.0", lifespan=lifespan,
        description="Game backend for RAAZ. The canonical case solution never leaves the server.",
        docs_url="/api/docs" if s.env != "prod" else None, openapi_url="/api/openapi.json" if s.env != "prod" else None,
    )
    app.add_middleware(
        CORSMiddleware, allow_origins=s.cors_list, allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
    )
    install_handlers(app)

    @app.middleware("http")
    async def observe(request: Request, call_next):
        rid = request.headers.get("x-request-id", "")[:64] or uuid.uuid4().hex[:16]
        request.state.request_id = rid
        t0 = time.perf_counter()
        response: Response = await call_next(request)
        dt = time.perf_counter() - t0
        route = request.scope.get("route")
        path = getattr(route, "path", "unmatched")
        metrics.observe("raaz_http_request_seconds", dt, method=request.method, route=path)
        metrics.inc("raaz_http_requests_total", method=request.method, route=path, status=str(response.status_code))
        response.headers["X-Request-ID"] = rid
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cache-Control"] = "no-store"
        if dt > 1.5:
            log.warning("slow request", extra={"path": path, "seconds": round(dt, 3), "request_id": rid})
        return response

    @app.get("/health", tags=["system"])
    def health():
        return {"status": "ok"}

    @app.get("/ready", tags=["system"])
    def ready(response: Response):
        try:
            with dbmod.engine.connect() as c:
                c.execute(text("select 1"))
        except Exception:  # noqa: BLE001
            response.status_code = 503
            return {"status": "unavailable", "db": False}
        return {"status": "ready", "db": True}

    @app.get("/metrics", tags=["system"], include_in_schema=False)
    def metrics_endpoint(request: Request):
        token = get_settings().metrics_token
        if token and request.headers.get("x-metrics-token") != token:
            return Response(status_code=404)
        return Response(metrics.render(), media_type="text/plain; version=0.0.4")

    app.include_router(v1_router, prefix="/api/v1")
    return app


app = create_app()
