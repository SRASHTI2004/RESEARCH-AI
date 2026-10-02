def test_login_is_rate_limited_after_repeated_attempts(client):
    """The limiter itself is real (not mocked) — this hits the configured
    10/minute limit on /auth/login directly rather than asserting on
    internal state."""
    client.post("/auth/register", json={"email": "ratelimit@example.com", "password": "password123"})

    for _ in range(10):
        res = client.post("/auth/login", json={"email": "ratelimit@example.com", "password": "password123"})
        assert res.status_code == 200

    res = client.post("/auth/login", json={"email": "ratelimit@example.com", "password": "password123"})
    assert res.status_code == 429
