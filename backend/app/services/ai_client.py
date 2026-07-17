import httpx

from app.core.config import settings


class AIServiceClient:
    """HTTP client for the separate AI inference service (SAM2 + SDXL/ControlNet)."""

    def __init__(self, base_url: str | None = None):
        self.base_url = base_url or settings.AI_SERVICE_URL

    def segment(self, image_bytes: bytes, filename: str, content_type: str) -> bytes:
        response = httpx.post(
            f"{self.base_url}/segment",
            files={"file": (filename, image_bytes, content_type)},
            timeout=60,
        )
        response.raise_for_status()
        return response.content

    def generate(
        self,
        image_bytes: bytes,
        filename: str,
        content_type: str,
        prompt: str,
        negative_prompt: str,
    ) -> bytes:
        response = httpx.post(
            f"{self.base_url}/generate",
            files={"file": (filename, image_bytes, content_type)},
            data={"prompt": prompt, "negative_prompt": negative_prompt},
            timeout=300,
        )
        response.raise_for_status()
        return response.content
