import io


def _create_project_with_image(client, headers):
    project = client.post("/api/v1/projects", json={"name": "Shoes"}, headers=headers).json()
    image = client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("sneaker.png", io.BytesIO(b"fake-bytes"), "image/png")},
        headers=headers,
    ).json()
    return project, image


def test_create_segmentation(client, auth_headers):
    headers = auth_headers("segowner@example.com", "StrongPass123")
    project, image = _create_project_with_image(client, headers)

    response = client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/segment", headers=headers
    )
    assert response.status_code == 202
    body = response.json()
    assert body["generation_type"] == "segmentation"
    assert body["status"] == "pending"


def test_create_photo_generation_builds_prompt(client, auth_headers):
    headers = auth_headers("genowner@example.com", "StrongPass123")
    project, image = _create_project_with_image(client, headers)

    response = client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/generate",
        json={"scene_type": "lifestyle", "lighting": "natural", "camera_angle": "top_down"},
        headers=headers,
    )
    assert response.status_code == 202
    body = response.json()
    assert body["generation_type"] == "photo"
    assert "lifestyle product photograph" in body["prompt"]
    assert "natural daylight lighting" in body["prompt"]
    assert "top-down flat lay shot" in body["prompt"]
    assert body["negative_prompt"]


def test_list_generations_for_project(client, auth_headers):
    headers = auth_headers("listgen@example.com", "StrongPass123")
    project, image = _create_project_with_image(client, headers)
    client.post(f"/api/v1/projects/{project['id']}/images/{image['id']}/segment", headers=headers)

    response = client.get(f"/api/v1/projects/{project['id']}/generations", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_generation_by_id(client, auth_headers):
    headers = auth_headers("getgen@example.com", "StrongPass123")
    project, image = _create_project_with_image(client, headers)
    created = client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/segment", headers=headers
    ).json()

    response = client.get(f"/api/v1/generations/{created['id']}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_cannot_access_other_users_generation(client, auth_headers):
    headers_a = auth_headers("genowner2@example.com", "StrongPass123")
    headers_b = auth_headers("genintruder@example.com", "StrongPass123")
    project, image = _create_project_with_image(client, headers_a)
    created = client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/segment", headers=headers_a
    ).json()

    response = client.get(f"/api/v1/generations/{created['id']}", headers=headers_b)
    assert response.status_code == 403


def test_search_generations_by_prompt(client, auth_headers):
    headers = auth_headers("searcher@example.com", "StrongPass123")
    project, image = _create_project_with_image(client, headers)
    client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/generate",
        json={"scene_type": "lifestyle", "lighting": "natural", "camera_angle": "front"},
        headers=headers,
    )
    client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/generate",
        json={"scene_type": "outdoor", "lighting": "dramatic", "camera_angle": "front"},
        headers=headers,
    )

    response = client.get(
        f"/api/v1/projects/{project['id']}/generations",
        params={"search": "lifestyle"},
        headers=headers,
    )
    assert response.status_code == 200
    results = response.json()
    assert len(results) == 1
    assert "lifestyle" in results[0]["prompt"]


def test_segment_requires_image_to_belong_to_project(client, auth_headers):
    headers = auth_headers("mismatch@example.com", "StrongPass123")
    project_a, image_a = _create_project_with_image(client, headers)
    project_b = client.post("/api/v1/projects", json={"name": "Bags"}, headers=headers).json()

    response = client.post(
        f"/api/v1/projects/{project_b['id']}/images/{image_a['id']}/segment", headers=headers
    )
    assert response.status_code == 404
