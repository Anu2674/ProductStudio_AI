from fastapi import APIRouter

from app.api.v1 import analytics, auth, generations, images, marketing_content, projects

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(projects.router)
api_router.include_router(images.router)
api_router.include_router(generations.router)
api_router.include_router(marketing_content.router)
api_router.include_router(analytics.router)
