from fastapi import APIRouter

from app.api.v1 import auth, images, projects

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(images.router)
