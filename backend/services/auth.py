"""
JWT Authentication service.

- Password hashing via passlib (bcrypt)
- Short-lived access tokens (15 min)
- Long-lived refresh tokens (30 days), stored hashed in DB, revocable
- Constant-time responses to prevent user enumeration
"""

import hashlib
import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import User, RefreshToken

# ── Config ────────────────────────────────────────────────────
load_dotenv()

# Single source of truth for the JWT signing secret. No insecure default:
# the app refuses to start if it is missing (prevents per-process random
# keys that would make tokens invalid across workers).
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError(
        "JWT_SECRET_KEY is not set — refusing to start with an insecure default. "
        "Generate one: python -c \"import secrets; print(secrets.token_hex(32))\""
    )
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=True)


# ── Pydantic schemas ──────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None


# ── Password helpers ──────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── Token helpers ─────────────────────────────────────────────

def create_access_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "exp": expire, "type": "access"}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _hash_refresh_token(raw: str) -> str:
    """Store only the SHA-256 hash of the refresh token in DB."""
    return hashlib.sha256(raw.encode()).hexdigest()


def create_refresh_token(user_id: str, db: Session) -> str:
    raw = secrets.token_urlsafe(48)
    token_hash = _hash_refresh_token(raw)
    expires_at = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    db_token = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(db_token)
    db.commit()
    return raw


def rotate_refresh_token(raw: str, db: Session) -> Optional[str]:
    """
    Validate + revoke old refresh token, issue a new one.
    Returns new raw token or None if invalid/expired/revoked.
    """
    token_hash = _hash_refresh_token(raw)
    db_token = db.query(RefreshToken).filter_by(token_hash=token_hash).first()
    if not db_token or db_token.revoked or db_token.expires_at < datetime.utcnow():
        return None
    # Revoke old token
    db_token.revoked = True
    db.commit()
    # Issue new token
    return create_refresh_token(db_token.user_id, db)


def revoke_all_refresh_tokens(user_id: str, db: Session) -> None:
    db.query(RefreshToken).filter_by(user_id=user_id, revoked=False).update({"revoked": True})
    db.commit()


# ── FastAPI dependencies ──────────────────────────────────────

def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Decode JWT access token, load User from DB.
    Raises 401 on any failure — uniform response prevents user enumeration.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            raise credentials_exc
        user_id: str = payload.get("sub")
        if not user_id:
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    user = db.query(User).filter_by(id=user_id, is_active=True).first()
    if not user:
        raise credentials_exc
    return user


def get_current_active_user(user: User = Depends(get_current_user)) -> User:
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return user
