from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.repositories.marketing_content_repository import MarketingContentRepository
from app.services.image_service import ImageService
from app.services.marketing_copy_builder import build_marketing_content
from app.services.project_service import ProjectService


class MarketingContentService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = MarketingContentRepository(db)
        self.projects = ProjectService(db)
        self.images = ImageService(db)

    def create(
        self,
        user_id: int,
        project_id: int,
        image_id: int,
        product_name: str,
        category: str,
        key_features: list[str],
    ):
        self.projects.get_owned(user_id, project_id)
        image = self.images.get_owned(user_id, image_id)
        if image.project_id != project_id:
            raise NotFoundError("Image not found in this project")

        content = build_marketing_content(product_name, category, key_features)
        return self.repo.create(
            project_id=project_id,
            source_image_id=image_id,
            title=content["title"],
            description=content["description"],
            bullet_points=content["bullet_points"],
            social_caption=content["social_caption"],
            seo_keywords=content["seo_keywords"],
        )

    def list_for_project(self, user_id: int, project_id: int):
        self.projects.get_owned(user_id, project_id)
        return self.repo.list_for_project(project_id)

    def get_owned(self, user_id: int, content_id: int):
        content = self.repo.get_by_id(content_id)
        if content is None:
            raise NotFoundError("Marketing content not found")
        self.projects.get_owned(user_id, content.project_id)
        return content
