from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.analytics import ProjectAnalyticsOut
from app.services.analytics_service import AnalyticsService

router = APIRouter(tags=["analytics"])


@router.get("/projects/{project_id}/analytics", response_model=ProjectAnalyticsOut)
def get_project_analytics(
    project_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    return AnalyticsService(db).get_project_analytics(current_user.id, project_id)
