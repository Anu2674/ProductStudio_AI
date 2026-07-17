import io

from PIL import Image

from app.jobs.process_generation import run
from app.services import ai_client as ai_client_module


def _sample_png_bytes(color=(200, 100, 50), size=(64, 64)):
    image = Image.new("RGB", size, color=color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_run_processes_photo_generation_with_enhancement_and_quality(
    client, auth_headers, db_session, monkeypatch
):
    headers = auth_headers("jobrunner@example.com", "StrongPass123")
    project = client.post("/api/v1/projects", json={"name": "Shoes"}, headers=headers).json()
    image = client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("shoe.png", io.BytesIO(_sample_png_bytes()), "image/png")},
        headers=headers,
    ).json()
    generation = client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/generate",
        json={"scene_type": "studio_white", "lighting": "soft", "camera_angle": "front"},
        headers=headers,
    ).json()

    def _fake_generate(self, image_bytes, filename, content_type, prompt, negative_prompt):
        return _sample_png_bytes(color=(240, 240, 240))

    monkeypatch.setattr(ai_client_module.AIServiceClient, "generate", _fake_generate)

    run(generation["id"], db=db_session)

    completed = client.get(f"/api/v1/generations/{generation['id']}", headers=headers).json()
    assert completed["status"] == "completed"
    assert completed["result_storage_path"] is not None
    assert completed["quality_score"] is not None
    assert set(completed["quality_score"]["scores"].keys()) == {
        "sharpness",
        "lighting",
        "contrast",
        "resolution",
        "background_quality",
        "product_visibility",
        "composition",
    }


def test_run_processes_segmentation_without_enhancement(client, auth_headers, db_session, monkeypatch):
    headers = auth_headers("segjobrunner@example.com", "StrongPass123")
    project = client.post("/api/v1/projects", json={"name": "Bags"}, headers=headers).json()
    image = client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("bag.png", io.BytesIO(_sample_png_bytes()), "image/png")},
        headers=headers,
    ).json()
    generation = client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/segment", headers=headers
    ).json()

    def _fake_segment(self, image_bytes, filename, content_type):
        return _sample_png_bytes()

    monkeypatch.setattr(ai_client_module.AIServiceClient, "segment", _fake_segment)

    run(generation["id"], db=db_session)

    completed = client.get(f"/api/v1/generations/{generation['id']}", headers=headers).json()
    assert completed["status"] == "completed"
    assert completed["quality_score"] is not None
