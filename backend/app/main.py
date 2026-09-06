from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.logging_conf import setup_logging
from app.routers import assistants, webhook


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title="AI Bot Constructor")

    # The panel is served from a separate origin, so the browser needs CORS.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(assistants.router)
    app.include_router(webhook.router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
