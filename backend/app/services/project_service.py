from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, NotFoundError
from app.repositories.project_repository import ProjectRepository


class ProjectService:
    def __init__(self, db: Session):
        self.repo = ProjectRepository(db)

    def create(self, user_id: int, name: str, description: str | None):
        return self.repo.create(user_id, name, description)

    def list_for_user(self, user_id: int):
        return self.repo.list_for_user(user_id)

    def get_owned(self, user_id: int, project_id: int):
        project = self.repo.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project not found")
        if project.user_id != user_id:
            raise ForbiddenError("You do not have access to this project")
        return project

    def update(self, user_id: int, project_id: int, name: str | None, description: str | None):
        project = self.get_owned(user_id, project_id)
        return self.repo.update(project, name, description)

    def delete(self, user_id: int, project_id: int):
        project = self.get_owned(user_id, project_id)
        self.repo.delete(project)
