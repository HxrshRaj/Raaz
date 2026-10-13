from __future__ import annotations

from datetime import UTC, datetime, timedelta

import bcrypt
import jwt

from .config import get_settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    # bcrypt only looks at the first 72 bytes; reject anything longer rather than silently truncating.
    raw = password.encode()
    if len(raw) > 72:
        raise ValueError("password too long")
    return bcrypt.hashpw(raw, bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str | None) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(password.encode()[:72], hashed.encode())
    except ValueError:
        return False


def create_token(user_id: str, *, minutes: int | None = None) -> str:
    s = get_settings()
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=minutes or s.jwt_expire_minutes)
    return jwt.encode({"sub": user_id, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}, s.jwt_secret,
                      algorithm=ALGORITHM)


def decode_token(token: str) -> str | None:
    s = get_settings()
    try:
        data = jwt.decode(token, s.jwt_secret, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
    sub = data.get("sub")
    return sub if isinstance(sub, str) else None
