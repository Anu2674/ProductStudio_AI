import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app, get_generation_pipeline, get_segmentation_pipeline


class FakeSegmentationPipeline:
    requires_mask = False

    def segment(self, image: Image.Image) -> np.ndarray:
        w, h = image.size
        mask = np.zeros((h, w), dtype=bool)
        mask[h // 4 : 3 * h // 4, w // 4 : 3 * w // 4] = True
        return mask

    def remove_background(self, image: Image.Image) -> Image.Image:
        rgba = np.array(image.convert("RGBA"))
        rgba[..., 3] = (self.segment(image) * 255).astype(np.uint8)
        return Image.fromarray(rgba)


class FakeGenerationPipeline:
    requires_mask = True

    def generate(self, image, prompt, negative_prompt="", product_mask=None, **_):
        assert product_mask is not None, "generate() should receive the SAM2 mask"
        return image.convert("RGB")


@pytest.fixture()
def client():
    app.dependency_overrides[get_segmentation_pipeline] = lambda: FakeSegmentationPipeline()
    app.dependency_overrides[get_generation_pipeline] = lambda: FakeGenerationPipeline()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
