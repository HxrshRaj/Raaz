from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select

from ...config import get_settings
from ...deps import DB, CurrentUser, audit, ip_rate_limit
from ...errors import DomainError, Forbidden
from ...models import PlayerProfile, User
from ...schemas.requests import GuestIn, LoginIn, RegisterIn
from ...security import create_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


def _out(user: User) -> dict:
    return {"access_token": create_token(user.id), "token_type": "bearer",
            "user": {"id": user.id, "display_name": user.display_name, "is_guest": user.is_guest, "email": user.email}}


@router.post("/register", dependencies=[Depends(ip_rate_limit("register", 10))], status_code=201)
def register(body: RegisterIn, db: DB, request: Request):
    email = body.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        # generic message; avoid confirming which emails are registered
        raise DomainError("registration_failed", "Could not create that account.", status=409)
    user = User(email=email, display_name=body.display_name, password_hash=hash_password(body.password))
    user.profile = PlayerProfile()
    db.add(user)
    db.commit()
    audit(db, user_id=user.id, action="auth.register", request=request)
    return _out(user)


@router.post("/login", dependencies=[Depends(ip_rate_limit("login", 20))])
def login(body: LoginIn, db: DB, request: Request):
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash) or not user.is_active:
        audit(db, user_id=None, action="auth.login_failed", request=request)
        raise DomainError("invalid_credentials", "Email or password is incorrect.", status=401)
    audit(db, user_id=user.id, action="auth.login", request=request)
    return _out(user)


@router.post("/guest", dependencies=[Depends(ip_rate_limit("guest", 20))], status_code=201)
def guest(body: GuestIn, db: DB, request: Request):
    if not get_settings().allow_guest:
        raise Forbidden("guests_disabled", "Guest play is disabled on this server.")
    user = User(display_name=body.display_name, is_guest=True)
    user.profile = PlayerProfile()
    db.add(user)
    db.commit()
    audit(db, user_id=user.id, action="auth.guest", request=request)
    return _out(user)


@router.get("/me")
def me(user: CurrentUser):
    return {"id": user.id, "display_name": user.display_name, "is_guest": user.is_guest, "email": user.email}
