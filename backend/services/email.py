"""
Email verification service.

Tokens stored in Redis (TTL 24 h), falls back to in-memory dict for dev.
SMTP credentials read from env: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD.
If SMTP_USER / SMTP_PASSWORD are empty the send is silently skipped (useful in dev).
"""
from __future__ import annotations

import os
import secrets
import smtplib
from concurrent.futures import ThreadPoolExecutor
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
_VERIFY_TTL = 24 * 3600  # 24 h
_PREFIX = "cg:verify:"

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "") or SMTP_USER
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://clipsgold.ru")

_executor = ThreadPoolExecutor(max_workers=2)

# ── Redis client (optional) ────────────────────────────────────────────────

_rclient = None
_redis_ok = False
_mem_store: dict[str, str] = {}  # fallback for dev

try:
    import redis as _rlib
    _rclient = _rlib.Redis.from_url(_REDIS_URL, decode_responses=True, socket_connect_timeout=2)
    _rclient.ping()
    _redis_ok = True
except Exception as _e:
    print(f"[email] Redis unavailable ({_e}), using in-memory token store")


# ── Token helpers ──────────────────────────────────────────────────────────

def create_verification_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    if _redis_ok and _rclient:
        _rclient.setex(f"{_PREFIX}{token}", _VERIFY_TTL, user_id)
    else:
        _mem_store[token] = user_id
    return token


def consume_verification_token(token: str) -> Optional[str]:
    """Return user_id and delete the token (single-use). Returns None if invalid/expired."""
    if _redis_ok and _rclient:
        key = f"{_PREFIX}{token}"
        user_id = _rclient.get(key)
        if user_id:
            _rclient.delete(key)
        return user_id  # type: ignore[return-value]
    # in-memory fallback
    return _mem_store.pop(token, None)


# ── SMTP sender (runs in thread to avoid blocking event loop) ──────────────

def _send_sync(to_email: str, subject: str, html: str, text: str) -> None:
    if not SMTP_USER or not SMTP_PASSWORD:
        return
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"ClipsGold 🦖 <{SMTP_FROM}>"
    msg["To"] = to_email
    msg.attach(MIMEText(text, "plain", "utf-8"))
    msg.attach(MIMEText(html, "html", "utf-8"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as srv:
        srv.starttls()
        srv.login(SMTP_USER, SMTP_PASSWORD)
        srv.sendmail(SMTP_USER, [to_email], msg.as_string())


async def send_verification_email(to_email: str, token: str) -> None:
    import asyncio
    link = f"{FRONTEND_URL}/verify-email?token={token}"
    subject = "Подтвердите email — ClipsGold 🦖"
    text = (
        f"Привет!\n\n"
        f"Подтвердите email, перейдя по ссылке:\n{link}\n\n"
        f"Ссылка действует 24 часа.\n\n"
        f"— ClipsGold 🦖"
    )
    html = f"""<!DOCTYPE html>
<html lang="ru">
<head><meta charset="utf-8"/></head>
<body style="margin:0;padding:0;background:#FFF3D6;font-family:'Helvetica Neue',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr><td align="center" style="padding:40px 16px;">
      <table width="560" cellpadding="0" cellspacing="0"
             style="background:#FFFCF1;border:3px solid #3A2E2A;border-radius:24px;
                    box-shadow:6px 8px 0 #3A2E2A;padding:40px 44px;max-width:100%;">
        <tr><td style="text-align:center;padding-bottom:8px;">
          <span style="font-size:48px;">🦖</span>
        </td></tr>
        <tr><td style="text-align:center;padding-bottom:6px;">
          <h1 style="margin:0;font-size:38px;font-weight:700;color:#3A2E2A;
                     letter-spacing:.5px;">
            Подтвердите&nbsp;email
          </h1>
        </td></tr>
        <tr><td style="text-align:center;color:#6B574F;font-size:17px;
                       line-height:1.5;padding-bottom:28px;">
          Кликните кнопку ниже — и попадёте прямо в Студию.
        </td></tr>
        <tr><td style="text-align:center;padding-bottom:28px;">
          <a href="{link}"
             style="display:inline-block;background:#FF8FA3;color:#fff;
                    text-decoration:none;font-size:22px;font-weight:700;
                    padding:12px 30px 10px;border:3px solid #3A2E2A;
                    border-radius:18px;box-shadow:4px 5px 0 #3A2E2A;
                    text-shadow:1px 1px 0 rgba(58,46,42,.3);">
            Подтвердить email ✅
          </a>
        </td></tr>
        <tr><td style="text-align:center;color:#6B574F;font-size:14px;
                       line-height:1.5;border-top:2px dashed #D4C5BD;padding-top:20px;">
          Ссылка действует <strong>24 часа</strong>. Если вы не регистрировались —
          просто проигнорируйте это письмо.<br/><br/>
          <a href="{link}" style="color:#6B574F;font-size:12px;word-break:break-all;">{link}</a>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""

    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(_executor, _send_sync, to_email, subject, html, text)
    except Exception as e:
        print(f"[email] send failed to {to_email}: {e}")
