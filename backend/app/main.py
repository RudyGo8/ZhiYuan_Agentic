"""
@create_time: 2025/08/14
@Author: GeChao
@File: main.py
"""

from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    import sys

    backend_dir = Path(__file__).resolve().parents[1]
    app_dir = Path(__file__).resolve().parent
    sys.path = [p for p in sys.path if Path(p).resolve() != app_dir]
    sys.path.insert(0, str(backend_dir))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from app.agent import rebuild_agent_with_external_tools
from app.config import logger
from app.database import init_db
from app.mcp.client_manager import mcp_client_manager
from app.routes.common.auth import router_r1 as auth_router_r1
from app.routes.common.chat import router_r1 as chat_router_r1
from app.routes.common.document import router_r1 as document_router_r1
from app.routes.common.version import router_r1 as version_router_r1
from app.version import get_app_version

# 前端打包
FRONTEND_DIR = Path(__file__).resolve().parents[2] / "frontend"
FRONTEND_DIST_DIR = FRONTEND_DIR / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    await mcp_client_manager.initialize()
    enabled_tools = rebuild_agent_with_external_tools()
    logger.info("Agent external toolset loaded: %s", enabled_tools)
    yield


app = FastAPI(
    title="ZhiYuan Agentic API",
    version=get_app_version(),
    description=__doc__,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_request(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code} {request.url}")
    return response


app.include_router(auth_router_r1)
app.include_router(chat_router_r1)
app.include_router(document_router_r1)
app.include_router(version_router_r1)

if FRONTEND_DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST_DIR), html=True), name="frontend")
else:
    logger.warning("Frontend dist not found at %s, skip static mount.", FRONTEND_DIST_DIR)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
