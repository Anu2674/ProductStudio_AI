from pydantic import BaseModel


class RecentActivityItem(BaseModel):
    id: int
    generation_type: str
    status: str
    created_at: str


class ProjectAnalyticsOut(BaseModel):
    total_images: int
    total_generations: int
    generations_by_status: dict[str, int]
    average_quality_score: float | None = None
    storage_usage_bytes: int
    recent_activity: list[RecentActivityItem]
