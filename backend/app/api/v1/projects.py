from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.schemas.project import ProjectCreate, ProjectOut, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=201)
def create_project(
    payload: ProjectCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    return ProjectService(db).create(current_user.id, payload.name, payload.description)


@router.get("", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return ProjectService(db).list_for_user(current_user.id)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    return ProjectService(db).get_owned(current_user.id, project_id)


@router.patch("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    return ProjectService(db).update(current_user.id, project_id, payload.name, payload.description)


@router.delete("/{project_id}", status_code=204)
def delete_project(
    project_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    ProjectService(db).delete(current_user.id, project_id)
