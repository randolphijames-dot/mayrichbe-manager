"""API v1 路由汇总"""
from fastapi import APIRouter
from app.api.v1.endpoints import accounts, materials, tasks, logs, youtube, tools, profile, inbox, traffic

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(accounts.router)
api_router.include_router(materials.router)
api_router.include_router(tasks.router)
api_router.include_router(logs.router)
api_router.include_router(youtube.router)
api_router.include_router(tools.router)
api_router.include_router(profile.router)
api_router.include_router(inbox.router)
api_router.include_router(traffic.router)
