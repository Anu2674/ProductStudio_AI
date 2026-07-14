import io


def test_upload_image(client, auth_headers):
    headers = auth_headers("uploader@example.com", "StrongPass123")
    project = client.post("/api/v1/projects", json={"name": "Shoes"}, headers=headers).json()

    file_content = b"fake-image-bytes"
    response = client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("sneaker.png", io.BytesIO(file_content), "image/png")},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "sneaker.png"
    assert body["size_bytes"] == len(file_content)


def test_upload_rejects_unsupported_content_type(client, auth_headers):
    headers = auth_headers("badtype@example.com", "StrongPass123")
    project = client.post("/api/v1/projects", json={"name": "Shoes"}, headers=headers).json()

    response = client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("doc.pdf", io.BytesIO(b"not an image"), "application/pdf")},
        headers=headers,
    )
    assert response.status_code == 415


def test_list_images_for_project(client, auth_headers):
    headers = auth_headers("lister@example.com", "StrongPass123")
    project = client.post("/api/v1/projects", json={"name": "Bags"}, headers=headers).json()
    client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("bag.jpg", io.BytesIO(b"data"), "image/jpeg")},
        headers=headers,
    )

    response = client.get(f"/api/v1/projects/{project['id']}/images", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_delete_image(client, auth_headers):
    headers = auth_headers("imgdeleter@example.com", "StrongPass123")
    project = client.post("/api/v1/projects", json={"name": "Hats"}, headers=headers).json()
    uploaded = client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("hat.jpeg", io.BytesIO(b"data"), "image/jpeg")},
        headers=headers,
    ).json()

    response = client.delete(f"/api/v1/images/{uploaded['id']}", headers=headers)
    assert response.status_code == 204

    get_response = client.get(f"/api/v1/images/{uploaded['id']}", headers=headers)
    assert get_response.status_code == 404


def test_cannot_access_other_users_image(client, auth_headers):
    headers_a = auth_headers("imgowner@example.com", "StrongPass123")
    headers_b = auth_headers("imgintruder@example.com", "StrongPass123")
    project = client.post("/api/v1/projects", json={"name": "Watches"}, headers=headers_a).json()
    uploaded = client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("watch.png", io.BytesIO(b"data"), "image/png")},
        headers=headers_a,
    ).json()

    response = client.get(f"/api/v1/images/{uploaded['id']}", headers=headers_b)
    assert response.status_code == 403
