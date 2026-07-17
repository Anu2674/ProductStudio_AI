from sqlalchemy.orm import Session

from app.models.marketing_content import MarketingContent


class MarketingContentRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        project_id: int,
        source_image_id: int,
        title: str,
        description: str,
        bullet_points: list[str],
        social_caption: str,
        seo_keywords: list[str],
    ) -> MarketingContent:
        content = MarketingContent(
            project_id=project_id,
            source_image_id=source_image_id,
            title=title,
            description=description,
            bullet_points=bullet_points,
            social_caption=social_caption,
            seo_keywords=seo_keywords,
        )
        self.db.add(content)
        self.db.commit()
        self.db.refresh(content)
        return content

    def get_by_id(self, content_id: int) -> MarketingContent | None:
        return self.db.query(MarketingContent).filter(MarketingContent.id == content_id).first()

    def list_for_project(self, project_id: int) -> list[MarketingContent]:
        return (
            self.db.query(MarketingContent)
            .filter(MarketingContent.project_id == project_id)
            .order_by(MarketingContent.created_at.desc())
            .all()
        )
