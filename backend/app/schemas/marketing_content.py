from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MarketingContentRequest(BaseModel):
    product_name: str
    category: str = "product"
    key_features: list[str] = []


class MarketingContentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    source_image_id: int
    title: str
    description: str
    bullet_points: list[str]
    social_caption: str
    seo_keywords: list[str]
    created_at: datetime
