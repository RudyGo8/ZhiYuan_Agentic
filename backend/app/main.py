'''
@create_time: 2026/3/30
@Author: GeChao
@File: main.py
'''
import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.config import logger
from app.database import init_db
from app.routes.common.auth import router_r1 as auth_router_r1
from app.routes.common.chat import router_r1 as chat_router_r1
from app.routes.common.document import router_r1 as document_router_r1

app = FastAPI(title="RAG Agent API")


@app.on_event("startup")
async def startup_event():
    init_db()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware('http')
async def log_request(request: Request, call_next):
    logger.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    logger.info(f"Response: {response.status_code} {request.url}")
    return response


app.include_router(auth_router_r1)
app.include_router(chat_router_r1)
app.include_router(document_router_r1)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
