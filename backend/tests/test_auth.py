def test_register_creates_user(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "seller@example.com", "password": "StrongPass123", "full_name": "Test Seller"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "seller@example.com"
    assert "hashed_password" not in body


def test_register_duplicate_email_fails(client):
    client.post("/api/v1/auth/register", json={"email": "dupe@example.com", "password": "StrongPass123"})
    response = client.post("/api/v1/auth/register", json={"email": "dupe@example.com", "password": "AnotherPass123"})
    assert response.status_code == 400


def test_login_returns_token(client):
    client.post("/api/v1/auth/register", json={"email": "login@example.com", "password": "StrongPass123"})
    response = client.post("/api/v1/auth/login", json={"email": "login@example.com", "password": "StrongPass123"})
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_login_wrong_password_fails(client):
    client.post("/api/v1/auth/register", json={"email": "wrongpass@example.com", "password": "StrongPass123"})
    response = client.post("/api/v1/auth/login", json={"email": "wrongpass@example.com", "password": "WrongOne123"})
    assert response.status_code == 401


def test_me_requires_token(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_returns_current_user(client):
    client.post("/api/v1/auth/register", json={"email": "me@example.com", "password": "StrongPass123"})
    login_response = client.post("/api/v1/auth/login", json={"email": "me@example.com", "password": "StrongPass123"})
    token = login_response.json()["access_token"]
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"
