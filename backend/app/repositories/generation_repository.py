from sqlalchemy.orm import Session

from app.models.generation import Generation


class GenerationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        project_id: int,
        source_image_id: int,
        generation_type: str,
        prompt: str | None,
        negative_prompt: str | None,
        params: dict | None,
    ) -> Generation:
        generation = Generation(
            project_id=project_id,
            source_image_id=source_image_id,
            generation_type=generation_type,
            status="pending",
            prompt=prompt,
            negative_prompt=negative_prompt,
            params=params,
        )
        self.db.add(generation)
        self.db.commit()
        self.db.refresh(generation)
        return generation

    def get_by_id(self, generation_id: int) -> Generation | None:
        return self.db.query(Generation).filter(Generation.id == generation_id).first()

    def list_for_project(self, project_id: int, search: str | None = None) -> list[Generation]:
        query = self.db.query(Generation).filter(Generation.project_id == project_id)
        if search:
            query = query.filter(Generation.prompt.ilike(f"%{search}%"))
        return query.order_by(Generation.created_at.desc()).all()

    def mark_processing(self, generation: Generation) -> Generation:
        generation.status = "processing"
        self.db.commit()
        self.db.refresh(generation)
        return generation

    def mark_completed(
        self, generation: Generation, result_storage_path: str, quality_score: dict | None = None
    ) -> Generation:
        generation.status = "completed"
        generation.result_storage_path = result_storage_path
        generation.quality_score = quality_score
        self.db.commit()
        self.db.refresh(generation)
        return generation

    def mark_failed(self, generation: Generation, error_message: str) -> Generation:
        generation.status = "failed"
        generation.error_message = error_message
        self.db.commit()
        self.db.refresh(generation)
        return generation
