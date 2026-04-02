"""
Temodar Agent FastAPI Application

REST API and WebSocket endpoints for the web dashboard.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import urlparse

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from slowapi.errors import RateLimitExceeded
from starlette.responses import PlainTextResponse

from app_meta import __version__
from server import update_manager
from server.limiter import limiter
from server.routers import ai, catalog, favorites, scans, semgrep, system
from server.websockets import manager

logger = logging.getLogger("temodar_agent")
ALLOWED_HOSTS = ["localhost", "127.0.0.1"]
ALLOWED_HOST_SET = set(ALLOWED_HOSTS)
STATIC_DIR = Path(__file__).parent / "static"


def rate_limit_exceeded_handler(request: Request, exc: Exception):
    """Custom rate limit exceeded handler."""
    return PlainTextResponse(
        "Rate limit exceeded. Please try again later.",
        status_code=429,
    )


def setup_logging():
    """Configure application logging."""
    log_file = Path("temodar_agent.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(log_file, maxBytes=10 * 1024 * 1024, backupCount=5),
            logging.StreamHandler(),
        ],
    )
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    setup_logging()
    logger.info("Starting Temodar Agent Server...")

    app = FastAPI(
        title="Temodar Agent Dashboard",
        description="WordPress Plugin & Theme Security Scanner",
        version=__version__,
    )
    configure_application(app)
    return app


def configure_application(app: FastAPI) -> None:
    """Apply middleware, routes, startup wiring, and static mounts."""
    app.state.update_manager = update_manager.manager
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
    warmup_update_manager()
    register_routers(app)
    mount_static_directories(app, STATIC_DIR)
    register_root_route(app, STATIC_DIR)
    register_scan_websocket(app)


def warmup_update_manager() -> None:
    """Warm up release status cache without failing app startup."""
    try:
        update_manager.manager.get_status(force=False)
    except Exception:
        logger.warning("Startup release warmup failed.", exc_info=True)


def register_routers(app: FastAPI) -> None:
    """Register API routers."""
    for router in (
        scans.router,
        semgrep.router,
        favorites.router,
        catalog.router,
        system.router,
        ai.router,
    ):
        app.include_router(router)


def mount_static_directories(app: FastAPI, static_dir: Path) -> None:
    """Mount static and asset directories if present."""
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")


def register_root_route(app: FastAPI, static_dir: Path) -> None:
    """Register the dashboard root page route."""

    @app.get("/", response_class=HTMLResponse)
    @limiter.limit("10000/minute")
    async def root(request: Request):
        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return HTMLResponse("<h1>Temodar Agent Dashboard</h1><p>Static files not found.</p>")


def register_scan_websocket(app: FastAPI) -> None:
    """Register scan progress WebSocket endpoint."""

    @app.websocket("/ws/scans/{session_id}")
    async def websocket_endpoint(websocket: WebSocket, session_id: int):
        origin = websocket.headers.get("origin")
        if not is_allowed_websocket_origin(origin):
            await websocket.close(code=1008)
            return

        await manager.connect(websocket, session_id)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await manager.disconnect(websocket, session_id)


def is_allowed_websocket_origin(origin: str | None) -> bool:
    """Validate WebSocket origin against local-only host policy."""
    if not origin:
        return True
    try:
        origin_host = (urlparse(origin).hostname or "").lower()
    except Exception:
        return False
    return origin_host in ALLOWED_HOST_SET
