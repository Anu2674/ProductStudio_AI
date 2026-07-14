from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.exceptions import AppError
from app.api.v1.router import api_router

app = FastAPI(title=settings.APP_NAME)
app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(AppError)
def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/health")
def health_check():
    return {"status": "ok"}
