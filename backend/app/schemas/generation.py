from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SegmentationRequest(BaseModel):
    pass


class GenerationRequest(BaseModel):
    scene_type: str = "studio_white"
    lighting: str = "soft"
    camera_angle: str = "front"


class GenerationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    source_image_id: int
    generation_type: str
    status: str
    prompt: str | None = None
    negative_prompt: str | None = None
    params: dict | None = None
    result_storage_path: str | None = None
    quality_score: dict | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
