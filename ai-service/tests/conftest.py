import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app, get_generation_pipeline, get_segmentation_pipeline


class FakeSegmentationPipeline:
    def remove_background(self, image: Image.Image) -> Image.Image:
        return image.convert("RGBA")


class FakeGenerationPipeline:
    def generate(self, image: Image.Image, prompt: str, negative_prompt: str) -> Image.Image:
        return image.convert("RGB")


@pytest.fixture()
def client():
    app.dependency_overrides[get_segmentation_pipeline] = lambda: FakeSegmentationPipeline()
    app.dependency_overrides[get_generation_pipeline] = lambda: FakeGenerationPipeline()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
