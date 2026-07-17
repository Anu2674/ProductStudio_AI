import io

from PIL import Image

from app.jobs.process_generation import run
from app.services import ai_client as ai_client_module


def _sample_png_bytes():
    image = Image.new("RGB", (48, 48), color=(150, 120, 90))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_full_product_photography_flow(client, db_session, monkeypatch):
    # Register and log in
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": "founder@example.com", "password": "StrongPass123", "full_name": "Founder"},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login", json={"email": "founder@example.com", "password": "StrongPass123"}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a project
    project = client.post("/api/v1/projects", json={"name": "Ceramic Mugs"}, headers=headers).json()

    # Upload a product photo
    image = client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("mug.png", io.BytesIO(_sample_png_bytes()), "image/png")},
        headers=headers,
    ).json()

    # Kick off background removal and a styled photo generation
    segmentation = client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/segment", headers=headers
    ).json()
    generation = client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/generate",
        json={"scene_type": "studio_white", "lighting": "soft", "camera_angle": "three_quarter"},
        headers=headers,
    ).json()

    def _fake_segment(self, image_bytes, filename, content_type):
        return _sample_png_bytes()

    def _fake_generate(self, image_bytes, filename, content_type, prompt, negative_prompt):
        return _sample_png_bytes()

    monkeypatch.setattr(ai_client_module.AIServiceClient, "segment", _fake_segment)
    monkeypatch.setattr(ai_client_module.AIServiceClient, "generate", _fake_generate)

    # Process both jobs (normally picked up by the RQ worker)
    run(segmentation["id"], db=db_session)
    run(generation["id"], db=db_session)

    # Generate marketing content from the original upload
    marketing = client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/marketing-content",
        json={"product_name": "Ceramic Mug", "category": "mug", "key_features": ["dishwasher safe"]},
        headers=headers,
    )
    assert marketing.status_code == 201

    # Verify generation history, quality scoring, and download all work end-to-end
    listed = client.get(f"/api/v1/projects/{project['id']}/generations", headers=headers).json()
    assert len(listed) == 2
    assert all(g["status"] == "completed" for g in listed)
    assert all(g["quality_score"] is not None for g in listed)

    download = client.get(f"/api/v1/generations/{generation['id']}/file", headers=headers)
    assert download.status_code == 200

    analytics = client.get(f"/api/v1/projects/{project['id']}/analytics", headers=headers).json()
    assert analytics["total_images"] == 1
    assert analytics["total_generations"] == 2
    assert analytics["generations_by_status"] == {"completed": 2}
