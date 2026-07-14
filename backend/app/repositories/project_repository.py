from sqlalchemy.orm import Session

from app.models.project import Project


class ProjectRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: int, name: str, description: str | None) -> Project:
        project = Project(user_id=user_id, name=name, description=description)
        self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_by_id(self, project_id: int) -> Project | None:
        return self.db.query(Project).filter(Project.id == project_id).first()

    def list_for_user(self, user_id: int) -> list[Project]:
        return self.db.query(Project).filter(Project.user_id == user_id).all()

    def update(self, project: Project, name: str | None, description: str | None) -> Project:
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        self.db.commit()
        self.db.refresh(project)
        return project

    def delete(self, project: Project) -> None:
        self.db.delete(project)
        self.db.commit()
