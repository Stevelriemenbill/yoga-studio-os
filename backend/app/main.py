from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import api_router, realtime
from app.core.config import settings
from app.core.events import start_listener, stop_listener


@asynccontextmanager
async def lifespan(app: FastAPI):
    await start_listener()
    yield
    await stop_listener()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        lifespan=lifespan,
    )

    if settings.SENTRY_DSN:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.ENVIRONMENT)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    app.include_router(realtime.router, prefix=settings.API_V1_PREFIX)

    # Serve uploaded files from the local media volume.
    media_root = Path(settings.MEDIA_ROOT)
    media_root.mkdir(parents=True, exist_ok=True)
    app.mount(
        settings.MEDIA_URL, StaticFiles(directory=str(media_root)), name="media"
    )

    # Prometheus metrics at /metrics (opt-in; skipped if lib unavailable).
    if settings.METRICS_ENABLED:
        try:
            from prometheus_fastapi_instrumentator import Instrumentator

            Instrumentator().instrument(app).expose(
                app, endpoint="/metrics", include_in_schema=False
            )
        except ImportError:
            pass

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.ENVIRONMENT}

    return app


app = create_app()
