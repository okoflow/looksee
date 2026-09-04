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
from api.bootstrap import build_runtime, session_user_exists
from api.config import settings
from api.entrypoints.http.dependencies import close_rate_limiter
from api.entrypoints.http.errors import register_exception_handlers
from api.entrypoints.http.origin import TrustedOriginMiddleware
from api.entrypoints.http.routers import (
    alerts,
    assets,
    auth,
    credentials,
    deliveries,
    entitlements,
    health,
    media,
    models,
    workflows,
    ws,
)
from api.entrypoints.http.static import AuthenticatedStaticFiles
from api.entrypoints.redis.subscribers import create_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await broker.start()
    reconcile_task = asyncio.create_task(
        run_reconcile_loop(settings.reconcile_interval_seconds, reconcile_once),
        name="camera-reconcile",
    )
    delivery_task = asyncio.create_task(app.state.runtime.deliveries.run(), name="deliveries")
    try:
        yield
    finally:
        delivery_task.cancel()
        with suppress(asyncio.CancelledError):
            await delivery_task
        reconcile_task.cancel()
        with suppress(asyncio.CancelledError):
            await reconcile_task
        await broker.stop()
        await close_frame_store()
        await close_client()
        await close_rate_limiter()
        await engine.dispose()


def create_app() -> FastAPI:
    application = FastAPI(title=settings.app_name, lifespan=lifespan)
    application.state.runtime = build_runtime(settings)
    broker.include_router(create_router(application.state.runtime.frames))
    application.add_middleware(
        CORSMiddleware,
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.add_middleware(
        TrustedOriginMiddleware, allow_origin_regex=settings.cors_origin_regex
    )
    register_exception_handlers(application)
    application.include_router(health.router)
    application.include_router(media.router)
    application.include_router(auth.router)
    application.include_router(entitlements.router)
    application.include_router(models.router)
    application.include_router(workflows.router)
    application.include_router(alerts.router)
    application.include_router(credentials.router)
    application.include_router(deliveries.router)
    application.include_router(assets.router)
    application.include_router(ws.router)

    settings.snapshots_dir.mkdir(parents=True, exist_ok=True)
    application.mount(
        "/snapshots",
        AuthenticatedStaticFiles(directory=settings.snapshots_dir, user_exists=session_user_exists),
        name="snapshots",
    )

    return application


app = create_app()
