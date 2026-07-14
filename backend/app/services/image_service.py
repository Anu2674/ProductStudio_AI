from sqlalchemy.orm import Session

from app.core.exceptions import AppError, NotFoundError
from app.repositories.image_repository import ImageRepository
from app.services.project_service import ProjectService
from app.services.storage_service import StorageService

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_UPLOAD_SIZE_BYTES = 15 * 1024 * 1024


class ImageService:
    def __init__(self, db: Session, storage: StorageService | None = None):
        self.db = db
        self.repo = ImageRepository(db)
        self.projects = ProjectService(db)
        self.storage = storage or StorageService()

    def upload(self, user_id: int, project_id: int, filename: str, content_type: str, content: bytes):
        self.projects.get_owned(user_id, project_id)

        if content_type not in ALLOWED_CONTENT_TYPES:
            raise AppError(f"Unsupported file type: {content_type}", status_code=415)
        if len(content) > MAX_UPLOAD_SIZE_BYTES:
            raise AppError("File exceeds maximum upload size of 15MB", status_code=413)

        storage_path = self.storage.save(project_id, filename, content)
        return self.repo.create(project_id, filename, storage_path, content_type, len(content))

    def list_for_project(self, user_id: int, project_id: int):
        self.projects.get_owned(user_id, project_id)
        return self.repo.list_for_project(project_id)

    def get_owned(self, user_id: int, image_id: int):
        image = self.repo.get_by_id(image_id)
        if image is None:
            raise NotFoundError("Image not found")
        self.projects.get_owned(user_id, image.project_id)
        return image

    def delete(self, user_id: int, image_id: int):
        image = self.get_owned(user_id, image_id)
        self.storage.delete(image.storage_path)
        self.repo.delete(image)
