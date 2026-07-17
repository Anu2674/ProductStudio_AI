from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.marketing_content import MarketingContentOut, MarketingContentRequest
from app.services.marketing_content_service import MarketingContentService

router = APIRouter(tags=["marketing-content"])


@router.post(
    "/projects/{project_id}/images/{image_id}/marketing-content",
    response_model=MarketingContentOut,
    status_code=201,
)
def create_marketing_content(
    project_id: int,
    image_id: int,
    payload: MarketingContentRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return MarketingContentService(db).create(
        current_user.id,
        project_id,
        image_id,
        payload.product_name,
        payload.category,
        payload.key_features,
    )


@router.get("/projects/{project_id}/marketing-content", response_model=list[MarketingContentOut])
def list_marketing_content(
    project_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    return MarketingContentService(db).list_for_project(current_user.id, project_id)


@router.get("/marketing-content/{content_id}", response_model=MarketingContentOut)
def get_marketing_content(
    content_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    return MarketingContentService(db).get_owned(current_user.id, content_id)
