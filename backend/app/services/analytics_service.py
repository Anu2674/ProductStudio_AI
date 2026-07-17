from pathlib import Path

from sqlalchemy.orm import Session

from app.models.generation import Generation
from app.models.image import Image
from app.services.project_service import ProjectService


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db
        self.projects = ProjectService(db)

    def get_project_analytics(self, user_id: int, project_id: int) -> dict:
        self.projects.get_owned(user_id, project_id)

        images = self.db.query(Image).filter(Image.project_id == project_id).all()
        generations = self.db.query(Generation).filter(Generation.project_id == project_id).all()

        generations_by_status: dict[str, int] = {}
        for generation in generations:
            generations_by_status[generation.status] = generations_by_status.get(generation.status, 0) + 1

        quality_scores = [
            generation.quality_score["overall"]
            for generation in generations
            if generation.quality_score and "overall" in generation.quality_score
        ]
        average_quality_score = (
            round(sum(quality_scores) / len(quality_scores), 1) if quality_scores else None
        )

        storage_usage_bytes = sum(image.size_bytes for image in images)
        for generation in generations:
            if generation.result_storage_path:
                path = Path(generation.result_storage_path)
                if path.exists():
                    storage_usage_bytes += path.stat().st_size

        recent_activity = sorted(generations, key=lambda g: g.created_at, reverse=True)[:10]

        return {
            "total_images": len(images),
            "total_generations": len(generations),
            "generations_by_status": generations_by_status,
            "average_quality_score": average_quality_score,
            "storage_usage_bytes": storage_usage_bytes,
            "recent_activity": [
                {
                    "id": generation.id,
                    "generation_type": generation.generation_type,
                    "status": generation.status,
                    "created_at": generation.created_at.isoformat(),
                }
                for generation in recent_activity
            ],
        }
