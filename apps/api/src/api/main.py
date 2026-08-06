"""API process composition root."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.adapters.http.client import close_client
from api.adapters.persistence.db import engine
from api.adapters.redis.broker import broker
from api.adapters.redis.frame_store import close_frame_store
from api.application.reconcile import reconcile_once, run_reconcile_loop
from api.config import settings
from api.entrypoints.http.errors import register_exception_handlers
from api.entrypoints.http.routers import (
    alerts,
    assets,
    auth,
    credentials,
    entitlements,
    health,
    models,
    workflows,
    ws,
)
from api.entrypoints.http.static import AuthenticatedStaticFiles
from api.entrypoints.redis.subscribers import router as redis_router

broker.include_router(redis_router)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await broker.start()
    reconcile_task = asyncio.create_task(
        run_reconcile_loop(settings.reconcile_interval_seconds, reconcile_once),
        name="camera-reconcile",
    )
    try:
        yield
    finally:
        reconcile_task.cancel()
        with suppress(asyncio.CancelledError):
            await reconcile_task
        await broker.stop()
        await close_frame_store()
        await close_client()
        await engine.dispose()


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name, lifespan=lifespan)
    application.add_middleware(
        CORSMiddleware,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(application)
    application.include_router(health.router)
    application.include_router(auth.router)
    application.include_router(entitlements.router)
    application.include_router(models.router)
    application.include_router(workflows.router)
    application.include_router(alerts.router)
    application.include_router(credentials.router)
    application.include_router(assets.router)
    application.include_router(ws.router)

    settings.snapshots_dir.mkdir(parents=True, exist_ok=True)
    application.mount(
        "/snapshots",
        AuthenticatedStaticFiles(directory=settings.snapshots_dir),
        name="snapshots",
    )

    return application


app = create_app()
