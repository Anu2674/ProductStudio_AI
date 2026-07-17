import io

from PIL import Image

from app.jobs.process_generation import run
from app.services import ai_client as ai_client_module


def _sample_png_bytes():
    image = Image.new("RGB", (32, 32), color=(90, 100, 110))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_analytics_reflects_images_and_generations(client, auth_headers, db_session, monkeypatch):
    headers = auth_headers("analyst@example.com", "StrongPass123")
    project = client.post("/api/v1/projects", json={"name": "Sneakers"}, headers=headers).json()
    image = client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("sneaker.png", io.BytesIO(_sample_png_bytes()), "image/png")},
        headers=headers,
    ).json()
    generation = client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/segment", headers=headers
    ).json()

    def _fake_segment(self, image_bytes, filename, content_type):
        return _sample_png_bytes()

    monkeypatch.setattr(ai_client_module.AIServiceClient, "segment", _fake_segment)
    run(generation["id"], db=db_session)

    response = client.get(f"/api/v1/projects/{project['id']}/analytics", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_images"] == 1
    assert body["total_generations"] == 1
    assert body["generations_by_status"] == {"completed": 1}
    assert body["average_quality_score"] is not None
    assert body["storage_usage_bytes"] > 0
    assert len(body["recent_activity"]) == 1


def test_analytics_requires_project_ownership(client, auth_headers):
    headers_a = auth_headers("analystowner@example.com", "StrongPass123")
    headers_b = auth_headers("analystintruder@example.com", "StrongPass123")
    project = client.post("/api/v1/projects", json={"name": "Watches"}, headers=headers_a).json()

    response = client.get(f"/api/v1/projects/{project['id']}/analytics", headers=headers_b)
    assert response.status_code == 403
