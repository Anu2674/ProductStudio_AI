import logging
from pathlib import Path

from app.db.session import SessionLocal
from app.repositories.generation_repository import GenerationRepository
from app.repositories.image_repository import ImageRepository
from app.services.ai_client import AIServiceClient
from app.services.enhancement_service import enhance
from app.services.quality_assessment_service import assess
from app.services.storage_service import StorageService

logger = logging.getLogger(__name__)


def run(generation_id: int, db=None) -> None:
    owns_session = db is None
    if db is None:
        db = SessionLocal()
    try:
        generations = GenerationRepository(db)
        images = ImageRepository(db)
        storage = StorageService()
        ai_client = AIServiceClient()

        generation = generations.get_by_id(generation_id)
        if generation is None:
            logger.warning("process_generation: generation %s not found", generation_id)
            return

        logger.info(
            "process_generation: starting generation %s (type=%s)",
            generation_id,
            generation.generation_type,
        )
        generations.mark_processing(generation)

        try:
            source_image = images.get_by_id(generation.source_image_id)
            image_bytes = Path(source_image.storage_path).read_bytes()

            if generation.generation_type == "segmentation":
                result_bytes = ai_client.segment(
                    image_bytes, source_image.original_filename, source_image.content_type
                )
            else:
                result_bytes = ai_client.generate(
                    image_bytes,
                    source_image.original_filename,
                    source_image.content_type,
                    generation.prompt or "",
                    generation.negative_prompt or "",
                )
                result_bytes = enhance(result_bytes)

            quality_score = assess(result_bytes)

            result_filename = f"generation_{generation.id}.png"
            result_path = storage.save(generation.project_id, result_filename, result_bytes)
            generations.mark_completed(generation, result_path, quality_score)
            logger.info("process_generation: generation %s completed", generation_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("process_generation: generation %s failed", generation_id)
            generations.mark_failed(generation, str(exc))
    finally:
        if owns_session:
            db.close()
