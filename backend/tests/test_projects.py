def test_create_project(client, auth_headers):
    headers = auth_headers()
    response = client.post("/api/v1/projects", json={"name": "Summer Sneakers"}, headers=headers)
    assert response.status_code == 201
    assert response.json()["name"] == "Summer Sneakers"


def test_list_projects_only_returns_own(client, auth_headers):
    headers_a = auth_headers("a@example.com", "StrongPass123")
    headers_b = auth_headers("b@example.com", "StrongPass123")
    client.post("/api/v1/projects", json={"name": "A's project"}, headers=headers_a)
    client.post("/api/v1/projects", json={"name": "B's project"}, headers=headers_b)

    response = client.get("/api/v1/projects", headers=headers_a)
    names = [p["name"] for p in response.json()]
    assert names == ["A's project"]


def test_get_other_users_project_is_forbidden(client, auth_headers):
    headers_a = auth_headers("owner2@example.com", "StrongPass123")
    headers_b = auth_headers("intruder@example.com", "StrongPass123")
    created = client.post("/api/v1/projects", json={"name": "Private"}, headers=headers_a).json()

    response = client.get(f"/api/v1/projects/{created['id']}", headers=headers_b)
    assert response.status_code == 403


def test_get_missing_project_is_404(client, auth_headers):
    headers = auth_headers("missing@example.com", "StrongPass123")
    response = client.get("/api/v1/projects/9999", headers=headers)
    assert response.status_code == 404


def test_update_project(client, auth_headers):
    headers = auth_headers("updater@example.com", "StrongPass123")
    created = client.post("/api/v1/projects", json={"name": "Old Name"}, headers=headers).json()
    response = client.patch(f"/api/v1/projects/{created['id']}", json={"name": "New Name"}, headers=headers)
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"


def test_delete_project(client, auth_headers):
    headers = auth_headers("deleter@example.com", "StrongPass123")
    created = client.post("/api/v1/projects", json={"name": "Temp"}, headers=headers).json()
    response = client.delete(f"/api/v1/projects/{created['id']}", headers=headers)
    assert response.status_code == 204
    get_response = client.get(f"/api/v1/projects/{created['id']}", headers=headers)
    assert get_response.status_code == 404
