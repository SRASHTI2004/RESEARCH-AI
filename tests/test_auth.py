def test_register_then_login_returns_tokens(client):
    reg = client.post("/auth/register", json={"email": "new@example.com", "password": "password123"})
    assert reg.status_code == 201
    assert reg.json()["role"] == "user"
    assert "hashed_password" not in reg.json()

    login = client.post("/auth/login", json={"email": "new@example.com", "password": "password123"})
    assert login.status_code == 200
    body = login.json()
    assert body["access_token"]
    assert body["refresh_token"]
    assert body["token_type"] == "bearer"


def test_register_duplicate_email_returns_409(client):
    client.post("/auth/register", json={"email": "dup@example.com", "password": "password123"})
    res = client.post("/auth/register", json={"email": "dup@example.com", "password": "password123"})
    assert res.status_code == 409


def test_register_rejects_short_password(client):
    res = client.post("/auth/register", json={"email": "short@example.com", "password": "short"})
    assert res.status_code == 422


def test_login_wrong_password_returns_401(client):
    client.post("/auth/register", json={"email": "wrongpw@example.com", "password": "password123"})
    res = client.post("/auth/login", json={"email": "wrongpw@example.com", "password": "nope12345"})
    assert res.status_code == 401


def test_login_unknown_email_returns_401(client):
    res = client.post("/auth/login", json={"email": "nobody@example.com", "password": "password123"})
    assert res.status_code == 401


def test_me_requires_valid_token(client, auth_headers):
    res = client.get("/auth/me", headers=auth_headers)
    assert res.status_code == 200
    assert res.json()["email"] == "user@example.com"

    res_no_token = client.get("/auth/me")
    assert res_no_token.status_code == 401

    res_bad_token = client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert res_bad_token.status_code == 401


def test_refresh_issues_a_new_token_pair(client):
    client.post("/auth/register", json={"email": "refresh@example.com", "password": "password123"})
    login = client.post("/auth/login", json={"email": "refresh@example.com", "password": "password123"})
    refresh_token = login.json()["refresh_token"]

    res = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert res.status_code == 200
    new_tokens = res.json()
    assert new_tokens["access_token"]
    assert new_tokens["refresh_token"]


def test_refresh_rejects_an_access_token(client):
    """An access token must not work as a refresh token."""
    client.post("/auth/register", json={"email": "noswap@example.com", "password": "password123"})
    login = client.post("/auth/login", json={"email": "noswap@example.com", "password": "password123"})
    access_token = login.json()["access_token"]

    res = client.post("/auth/refresh", json={"refresh_token": access_token})
    assert res.status_code == 401


def test_refresh_rejects_garbage_token(client):
    res = client.post("/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert res.status_code == 401
