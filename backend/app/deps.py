from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from .config import get_settings
from .db import get_db
from .engine.state import SessionView, get_owned_session, load_view
from .errors import DomainError, Forbidden, TooManyRequests
from .models import AuditEvent, User
from .ratelimit import get_limiter
from .security import decode_token

bearer = HTTPBearer(auto_error=False)

DB = Annotated[Session, Depends(get_db)]


def current_user(
    db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)] = None,
) -> User:
    if creds is None:
        raise DomainError("unauthenticated", "Sign in to continue.", status=401)
    uid = decode_token(creds.credentials)
    user = db.get(User, uid) if uid else None
    if user is None or not user.is_active:
        raise DomainError("unauthenticated", "Your session has expired. Sign in again.", status=401)
    return user


CurrentUser = Annotated[User, Depends(current_user)]


def session_view(session_id: str, db: DB, user: CurrentUser) -> SessionView:
    """Resource-level authorization: the session must belong to the caller (404 otherwise)."""
    s = get_owned_session(db, user.id, session_id)
    return load_view(db, s)


View = Annotated[SessionView, Depends(session_view)]


def rate_limit(bucket: str, per_min: Callable[[], int] | int | None = None) -> Callable:
    def dep(request: Request, user: CurrentUser) -> None:
        s = get_settings()
        limit = per_min() if callable(per_min) else (per_min or s.rate_limit_per_min)
        ok, retry = get_limiter().hit(f"{bucket}:{user.id}", limit)
        if not ok:
            raise TooManyRequests(retry_after=retry)

    return dep


def ip_rate_limit(bucket: str, per_min: int) -> Callable:
    def dep(request: Request) -> None:
        ip = request.client.host if request.client else "unknown"
        ok, retry = get_limiter().hit(f"{bucket}:{ip}", per_min)
        if not ok:
            raise TooManyRequests(retry_after=retry)

    return dep


def audit(db: Session, *, user_id: str | None, action: str, session_id: str | None = None, request: Request | None = None,
          **detail) -> None:
    db.add(AuditEvent(user_id=user_id, session_id=session_id, action=action, detail=detail,
                      ip=request.client.host if request and request.client else None))
    db.commit()


def require_workbench() -> None:
    if not get_settings().workbench_on:
        raise Forbidden("workbench_disabled", "The ML workbench is disabled on this server.")
