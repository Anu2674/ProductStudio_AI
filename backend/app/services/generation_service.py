from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.jobs.process_generation import run as process_generation
from app.repositories.generation_repository import GenerationRepository
from app.services.image_service import ImageService
from app.services.project_service import ProjectService
from app.services.prompt_builder import build_prompt


class GenerationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = GenerationRepository(db)
        self.projects = ProjectService(db)
        self.images = ImageService(db)

    def create_segmentation(self, user_id: int, project_id: int, image_id: int):
        self.projects.get_owned(user_id, project_id)
        image = self.images.get_owned(user_id, image_id)
        if image.project_id != project_id:
            raise NotFoundError("Image not found in this project")

        generation = self.repo.create(
            project_id=project_id,
            source_image_id=image_id,
            generation_type="segmentation",
            prompt=None,
            negative_prompt=None,
            params=None,
        )
        process_generation(generation.id, self.db)
        return generation

    def create_photo_generation(
        self, user_id: int, project_id: int, image_id: int, scene_type: str, lighting: str, camera_angle: str, custom_prompt: str | None = None
    ):
        self.projects.get_owned(user_id, project_id)
        image = self.images.get_owned(user_id, image_id)
        if image.project_id != project_id:
            raise NotFoundError("Image not found in this project")

        if custom_prompt:
            prompt = custom_prompt
            negative_prompt = None
        else:
            prompt, negative_prompt = build_prompt(scene_type, lighting, camera_angle)

        generation = self.repo.create(
            project_id=project_id,
            source_image_id=image_id,
            generation_type="photo",
            prompt=prompt,
            negative_prompt=negative_prompt,
            params={"scene_type": scene_type, "lighting": lighting, "camera_angle": camera_angle, "custom_prompt": custom_prompt},
        )
        process_generation(generation.id, self.db)
        return generation

    def list_for_project(self, user_id: int, project_id: int, search: str | None = None):
        self.projects.get_owned(user_id, project_id)
        return self.repo.list_for_project(project_id, search)

    def get_owned(self, user_id: int, generation_id: int):
        generation = self.repo.get_by_id(generation_id)
        if generation is None:
            raise NotFoundError("Generation not found")
        self.projects.get_owned(user_id, generation.project_id)
        return generation
