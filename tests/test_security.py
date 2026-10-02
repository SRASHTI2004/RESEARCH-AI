import pytest

from app.core import security


def test_hash_password_roundtrip():
    hashed = security.hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert security.verify_password("correct horse battery staple", hashed)
    assert not security.verify_password("wrong password", hashed)


def test_access_and_refresh_tokens_carry_distinct_type_claim():
    access = security.create_access_token("user-1", "user")
    refresh = security.create_refresh_token("user-1", "user")

    assert security.decode_token(access)["type"] == "access"
    assert security.decode_token(refresh)["type"] == "refresh"


def test_decode_token_rejects_garbage():
    with pytest.raises(security.TokenError):
        security.decode_token("not-a-jwt")


def test_decode_token_rejects_expired_token():
    from datetime import timedelta

    expired = security._create_token("user-1", "user", "access", timedelta(seconds=-1))

    with pytest.raises(security.TokenError):
        security.decode_token(expired)
