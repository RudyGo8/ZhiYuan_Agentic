'''
@create_time: 2026/4/27 下午8:18
@Author: GeChao
@File: version.py
'''

from fastapi import APIRouter
from app.version import get_app_version

router_r1 = APIRouter(
    prefix="/api/r1/version",
    tags=["version"],
)


@router_r1.get("/version")
async def version():
    return {
        "name": "ZhiYuan Agentic",
        "version": get_app_version(),
        "status": "ok",
    }
