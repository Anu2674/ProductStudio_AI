from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.image import ImageOut
from app.services.image_service import ImageService

router = APIRouter(tags=["images"])


@router.post("/projects/{project_id}/images", response_model=ImageOut, status_code=201)
async def upload_image(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    content = await file.read()
    return ImageService(db).upload(current_user.id, project_id, file.filename, file.content_type, content)


@router.get("/projects/{project_id}/images", response_model=list[ImageOut])
def list_images(
    project_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    return ImageService(db).list_for_project(current_user.id, project_id)


@router.get("/images/{image_id}", response_model=ImageOut)
def get_image(image_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return ImageService(db).get_owned(current_user.id, image_id)


@router.delete("/images/{image_id}", status_code=204)
def delete_image(image_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ImageService(db).delete(current_user.id, image_id)


@router.get("/images/{image_id}/file")
def download_image_file(
    image_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    image = ImageService(db).get_owned(current_user.id, image_id)
    return FileResponse(
        image.storage_path, media_type=image.content_type, filename=image.original_filename
    )
