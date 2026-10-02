from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.db import get_db
from app.core.rate_limit import limiter
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse, UserOut
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
@limiter.limit("5/minute")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)) -> UserOut:
    try:
        user = auth_service.register(db, payload.email, payload.password)
    except auth_service.EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=409, detail="Email already registered") from exc
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = auth_service.authenticate(db, payload.email, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Incorrect email or password")

    access_token, refresh_token = auth_service.issue_tokens(user)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
@limiter.limit("20/minute")
def refresh(request: Request, payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenResponse:
    try:
        user = auth_service.refresh_access_token(db, payload.refresh_token)
    except auth_service.InvalidRefreshTokenError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token") from exc

    access_token, refresh_token = auth_service.issue_tokens(user)
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)) -> UserOut:
    return UserOut.model_validate(current_user)
