import io


def _create_project_with_image(client, headers):
    project = client.post("/api/v1/projects", json={"name": "Wallets"}, headers=headers).json()
    image = client.post(
        f"/api/v1/projects/{project['id']}/images",
        files={"file": ("wallet.png", io.BytesIO(b"fake-bytes"), "image/png")},
        headers=headers,
    ).json()
    return project, image


def test_create_marketing_content(client, auth_headers):
    headers = auth_headers("marketer@example.com", "StrongPass123")
    project, image = _create_project_with_image(client, headers)

    response = client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/marketing-content",
        json={
            "product_name": "Leather Wallet",
            "category": "wallet",
            "key_features": ["RFID blocking", "slim profile"],
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Leather Wallet - Premium Wallet"
    assert "RFID blocking" in body["description"]
    assert len(body["bullet_points"]) == 3
    assert "rfid blocking" in body["seo_keywords"]


def test_marketing_content_defaults_without_features(client, auth_headers):
    headers = auth_headers("marketer2@example.com", "StrongPass123")
    project, image = _create_project_with_image(client, headers)

    response = client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/marketing-content",
        json={"product_name": "Travel Mug"},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["bullet_points"] == ["High-quality product", "Designed for durability and everyday use"]


def test_list_marketing_content_for_project(client, auth_headers):
    headers = auth_headers("marketer3@example.com", "StrongPass123")
    project, image = _create_project_with_image(client, headers)
    client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/marketing-content",
        json={"product_name": "Backpack"},
        headers=headers,
    )

    response = client.get(f"/api/v1/projects/{project['id']}/marketing-content", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_cannot_access_other_users_marketing_content(client, auth_headers):
    headers_a = auth_headers("marketer4@example.com", "StrongPass123")
    headers_b = auth_headers("intruder2@example.com", "StrongPass123")
    project, image = _create_project_with_image(client, headers_a)
    created = client.post(
        f"/api/v1/projects/{project['id']}/images/{image['id']}/marketing-content",
        json={"product_name": "Backpack"},
        headers=headers_a,
    ).json()

    response = client.get(f"/api/v1/marketing-content/{created['id']}", headers=headers_b)
    assert response.status_code == 403
