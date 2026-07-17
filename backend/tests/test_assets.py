import io
import zipfile

from PIL import Image

from app.services import ai_client as ai_client_module
from app.jobs.process_generation import run


def _sample_png_bytes():
    image = Image.new("RGB", (32, 32), color=(120, 140, 160))
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_download_image_file(client, auth_headers):
    headers = auth_headers("downloader@example.com", "StrongPass123")
    project = client.post("/api/v1/projects", json={"name": "Hats"}, headers=headers).json()
    image = client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("hat.png", io.BytesIO(_sample_png_bytes()), "image/png")},
        headers=headers,
    ).json()

    response = client.get(f"/api/v1/images/{image['id']}/file", headers=headers)
    assert response.status_code == 200
    assert response.content == _sample_png_bytes()


def test_download_generation_file_before_completion_is_404(client, auth_headers):
    headers = auth_headers("earlydownloader@example.com", "StrongPass123")
    project = client.post("/api/v1/projects", json={"name": "Belts"}, headers=headers).json()
    image = client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("belt.png", io.BytesIO(_sample_png_bytes()), "image/png")},
        headers=headers,
    ).json()
    generation = client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/segment", headers=headers
    ).json()

    response = client.get(f"/api/v1/generations/{generation['id']}/file", headers=headers)
    assert response.status_code == 404


def test_download_generation_file_after_completion(client, auth_headers, db_session, monkeypatch):
    headers = auth_headers("completedownloader@example.com", "StrongPass123")
    project = client.post("/api/v1/projects", json={"name": "Caps"}, headers=headers).json()
    image = client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("cap.png", io.BytesIO(_sample_png_bytes()), "image/png")},
        headers=headers,
    ).json()
    generation = client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/segment", headers=headers
    ).json()

    def _fake_segment(self, image_bytes, filename, content_type):
        return _sample_png_bytes()

    monkeypatch.setattr(ai_client_module.AIServiceClient, "segment", _fake_segment)
    run(generation["id"], db=db_session)

    response = client.get(f"/api/v1/generations/{generation['id']}/file", headers=headers)
    assert response.status_code == 200
    assert response.content == _sample_png_bytes()


def test_bulk_download_zip_contains_completed_generations(client, auth_headers, db_session, monkeypatch):
    headers = auth_headers("zipdownloader@example.com", "StrongPass123")
    project = client.post("/api/v1/projects", json={"name": "Gloves"}, headers=headers).json()
    image = client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("glove.png", io.BytesIO(_sample_png_bytes()), "image/png")},
        headers=headers,
    ).json()
    generation = client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/segment", headers=headers
    ).json()

    def _fake_segment(self, image_bytes, filename, content_type):
        return _sample_png_bytes()

    monkeypatch.setattr(ai_client_module.AIServiceClient, "segment", _fake_segment)
    run(generation["id"], db=db_session)

    response = client.get(
        f"/api/v1/projects/{project['id']}/generations/download",
        params={"generation_ids": str(generation["id"])},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"

    archive = zipfile.ZipFile(io.BytesIO(response.content))
    assert archive.namelist() == [f"generation_{generation['id']}.png"]
