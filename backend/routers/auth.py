"""
Auth router: register, login, refresh, logout, DELETE /account (GDPR).

Constant-time responses on login/register prevent user enumeration:
- /register always returns the same shape regardless of whether email exists
- /login always takes ~same time (bcrypt verify runs even for unknown emails)
"""

import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import User, UserPlan
from services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    rotate_refresh_token,
    revoke_all_refresh_tokens,
    get_current_user,
    TokenResponse,
    pwd_context,
)
from services import storage as s3
from services.observability import get_logger

router = APIRouter(prefix="/auth", tags=["auth"])
log = get_logger(__name__)

# ── Schemas ───────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Endpoints ─────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: Session = Depends(get_db)):
    """
    Create a new account.
    Always returns 201 — does NOT reveal whether email already exists
    (prevents user enumeration via timing/response differences).
    """
    existing = db.query(User).filter_by(email=body.email.lower()).first()
    if existing:
        # Run hash anyway to keep constant time — then return same shape
        hash_password(body.password)
        # Return 201 with a generic message (no leak of existence)
        return {"message": "If this email is new, your account has been created."}

    user = User(
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        plan=UserPlan.free,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    log.info("user_registered", user_id=str(user.id))
    return {"message": "If this email is new, your account has been created."}


class JsonLoginRequest(BaseModel):
    email: str
    password: str


@router.post("/json-login", response_model=TokenResponse)
async def json_login(body: JsonLoginRequest, db: Session = Depends(get_db)):
    """JSON-body login used by the frontend SPA (mirrors /login but accepts application/json)."""
    user = db.query(User).filter_by(email=body.email.lower(), is_active=True).first()
    _dummy_hash = "$2b$12$KIXbKkDqzFbMnJqX5QvXeOmNKLhVqFwMPqRsT7uVwXyZaAbBcCdDe"
    candidate_hash = user.hashed_password if user else _dummy_hash
    password_ok = verify_password(body.password, candidate_hash)
    if not user or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id), db)
    log.info("user_login", user_id=str(user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenResponse)
async def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Exchange email+password for access_token + refresh_token.
    Always runs bcrypt verify (constant time) to prevent timing attacks.
    """
    user = db.query(User).filter_by(email=form.username.lower(), is_active=True).first()

    # Always verify (even for unknown users) to prevent timing-based enumeration
    _dummy_hash = "$2b$12$KIXbKkDqzFbMnJqX5QvXeOmNKLhVqFwMPqRsT7uVwXyZaAbBcCdDe"
    candidate_hash = user.hashed_password if user else _dummy_hash
    password_ok = verify_password(form.password, candidate_hash)

    if not user or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id), db)

    log.info("user_login", user_id=str(user.id))
    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    """
    Rotate refresh token: invalidate old one, issue new access + refresh pair.
    """
    new_refresh = rotate_refresh_token(body.refresh_token, db)
    if not new_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )

    # Decode new refresh to get user_id (stored in DB record)
    from services.auth import _hash_refresh_token, RefreshToken
    import hashlib
    token_hash = hashlib.sha256(new_refresh.encode()).hexdigest()
    db_token = db.query(RefreshToken).filter_by(token_hash=token_hash).first()
    if not db_token:
        raise HTTPException(status_code=401, detail="Token error.")

    access_token = create_access_token(db_token.user_id)
    return TokenResponse(access_token=access_token, refresh_token=new_refresh)


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Revoke all refresh tokens for the current user."""
    revoke_all_refresh_tokens(str(current_user.id), db)
    log.info("user_logout", user_id=str(current_user.id))
    return {"message": "Logged out successfully."}


# ── GDPR: Right to Erasure ────────────────────────────────────

@router.delete("/account", status_code=status.HTTP_200_OK)
async def delete_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    GDPR Article 17 — Right to Erasure.

    Cascading deletion:
      1. All S3 objects under uploads/{user_id}/, clips/{user_id}/,
         outputs/{user_id}/, thumbnails/{user_id}/, meta/{user_id}/
      2. All DB records (cascade via FK: videos → transcripts,
         candidates, render_jobs, usage_events, refresh_tokens)
      3. User record itself

    This is irreversible. The endpoint requires a valid access token.
    """
    user_id = str(current_user.id)
    log.info("account_deletion_started", user_id=user_id)

    deleted_s3 = 0

    # 1. Delete all S3 objects for this user
    if s3.is_s3_enabled():
        for prefix in [
            f"uploads/{user_id}/",
            f"clips/{user_id}/",
            f"outputs/{user_id}/",
            f"thumbnails/{user_id}/",
            f"meta/{user_id}/",
        ]:
            try:
                deleted_s3 += s3.delete_prefix(prefix)
            except Exception as e:
                log.error("s3_delete_failed", user_id=user_id, prefix=prefix, error=str(e))

    # 2. Revoke all sessions
    revoke_all_refresh_tokens(user_id, db)

    # 3. Delete user (DB cascade handles all child records)
    db.delete(current_user)
    db.commit()

    log.info("account_deletion_complete", user_id=user_id, s3_objects_deleted=deleted_s3)
    return {
        "message": "Your account and all associated data have been permanently deleted.",
        "s3_objects_deleted": deleted_s3,
    }
