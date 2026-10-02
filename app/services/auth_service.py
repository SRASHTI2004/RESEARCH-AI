from sqlalchemy.orm import Session

from app.core import security
from app.models.user import User
from app.repositories import user_repository as repo


class EmailAlreadyRegisteredError(Exception):
    pass


class InvalidRefreshTokenError(Exception):
    pass


def register(db: Session, email: str, password: str) -> User:
    if repo.get_user_by_email(db, email) is not None:
        raise EmailAlreadyRegisteredError(email)

    user = User(email=email, hashed_password=security.hash_password(password))
    return repo.create_user(db, user)


def authenticate(db: Session, email: str, password: str) -> User | None:
    user = repo.get_user_by_email(db, email)
    if user is None or not security.verify_password(password, user.hashed_password):
        return None
    return user


def issue_tokens(user: User) -> tuple[str, str]:
    return (
        security.create_access_token(user.id, user.role),
        security.create_refresh_token(user.id, user.role),
    )


def refresh_access_token(db: Session, refresh_token: str) -> User:
    """Validate a refresh token and return the user it belongs to.

    Rejects access tokens presented here (via the "type" claim) so a
    short-lived access token can't be replayed as a refresh token.
    """
    try:
        payload = security.decode_token(refresh_token)
    except security.TokenError as exc:
        raise InvalidRefreshTokenError(str(exc)) from exc

    if payload.get("type") != "refresh":
        raise InvalidRefreshTokenError("Token is not a refresh token")

    user = repo.get_user_by_id(db, payload.get("sub", ""))
    if user is None:
        raise InvalidRefreshTokenError("User no longer exists")
    return user
