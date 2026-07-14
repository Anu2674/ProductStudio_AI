from sqlalchemy.orm import Session

from app.models.image import Image


class ImageRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self, project_id: int, original_filename: str, storage_path: str, content_type: str, size_bytes: int
    ) -> Image:
        image = Image(
            project_id=project_id,
            original_filename=original_filename,
            storage_path=storage_path,
            content_type=content_type,
            size_bytes=size_bytes,
        )
        self.db.add(image)
        self.db.commit()
        self.db.refresh(image)
        return image

    def get_by_id(self, image_id: int) -> Image | None:
        return self.db.query(Image).filter(Image.id == image_id).first()

    def list_for_project(self, project_id: int) -> list[Image]:
        return self.db.query(Image).filter(Image.project_id == project_id).all()

    def delete(self, image: Image) -> None:
        self.db.delete(image)
        self.db.commit()
