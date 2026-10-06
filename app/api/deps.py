from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core import security
from app.core.db import get_db
from app.models.user import User
from app.repositories import user_repository as repo
from app.services import usage_service

# tokenUrl is for Swagger UI's "Authorize" button only — /auth/login itself
# accepts JSON, not an OAuth2 form body (simpler for the React client).
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = security.decode_token(token)
    except security.TokenError as exc:
        raise credentials_error from exc

    if payload.get("type") != "access":
        raise credentials_error

    user = repo.get_user_by_id(db, payload.get("sub", ""))
    if user is None:
        raise credentials_error

    return user


def require_llm_budget(db: Session = Depends(get_db)) -> None:
    """Rejects the request with 429 once the site-wide daily LLM budget is spent
    (see app/services/usage_service.py)."""
    try:
        usage_service.ensure_budget(db)
    except usage_service.DailyLimitReachedError as exc:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=str(exc)) from exc
