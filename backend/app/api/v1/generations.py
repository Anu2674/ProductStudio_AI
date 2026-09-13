import io
import zipfile

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.schemas.generation import GenerationOut, GenerationRequest
from app.services.generation_service import GenerationService

router = APIRouter(tags=["generations"])


@router.post(
    "/projects/{project_id}/images/{image_id}/segment", response_model=GenerationOut, status_code=202
)
def create_segmentation(
    project_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return GenerationService(db).create_segmentation(current_user.id, project_id, image_id)


@router.post(
    "/projects/{project_id}/images/{image_id}/generate", response_model=GenerationOut, status_code=202
)
def create_photo_generation(
    project_id: int,
    image_id: int,
    payload: GenerationRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return GenerationService(db).create_photo_generation(
        current_user.id, project_id, image_id, payload.scene_type, payload.lighting, payload.camera_angle, payload.prompt
    )


@router.get("/projects/{project_id}/generations", response_model=list[GenerationOut])
def list_generations(
    project_id: int,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return GenerationService(db).list_for_project(current_user.id, project_id, search)


@router.get("/generations/{generation_id}", response_model=GenerationOut)
def get_generation(
    generation_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    return GenerationService(db).get_owned(current_user.id, generation_id)


@router.get("/generations/{generation_id}/file")
def download_generation_file(
    generation_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    service = GenerationService(db)
    generation = service.get_owned(current_user.id, generation_id)
    if not generation.result_storage_path:
        raise NotFoundError("Result not available yet")
    return FileResponse(
        generation.result_storage_path,
        media_type="image/png",
        filename=f"generation_{generation.id}.png",
    )


@router.get("/projects/{project_id}/generations/download")
def download_generations_zip(
    project_id: int,
    generation_ids: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    service = GenerationService(db)
    ids = [int(value) for value in generation_ids.split(",") if value]

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zip_file:
        for generation_id in ids:
            generation = service.get_owned(current_user.id, generation_id)
            if generation.project_id != project_id or not generation.result_storage_path:
                continue
            zip_file.write(generation.result_storage_path, arcname=f"generation_{generation_id}.png")
    buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=assets.zip"},
    )
