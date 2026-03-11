"""
test_public_beta_readiness.py
─────────────────────────────
"Evil Schoolboy" security & resilience test suite — ClipsGold Public Beta.

Sections:
  1. SSRF / Import Guard  — malicious payloads to /download-youtube
  2. BOLA                 — cross-user ownership enumeration (User A vs User B)
  3. Integrity            — broken files, empty audio, edge-case inputs

JWT tokens are minted locally using the same algorithm as auth.py:
  HS256, payload: {"sub": user_id, "exp": ..., "type": "access"}
Set JWT_SECRET_KEY env var to match the running server's secret.

Usage:
    pytest test_public_beta_readiness.py -v
    pytest test_public_beta_readiness.py -v -m "not slow"
    BASE_URL=https://staging.clipsgold.io JWT_SECRET_KEY=<s> pytest -v

Requirements:
    pip install pytest requests pytest-timeout python-jose[cryptography]
"""

import base64
import json as _json
import os
import statistics
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone

UTC = timezone.utc
from pathlib import Path
from typing import Optional

import pytest
import requests
from jose import jwt as jose_jwt

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

BASE_URL   = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
JWT_SECRET = os.getenv("JWT_SECRET_KEY", "test-secret-key-for-ci")
JWT_ALGO   = "HS256"

_USER_A_EMAIL = os.getenv("TEST_USER_A_EMAIL", "beta_user_a@clipsgold-test.com")
_USER_A_PASS  = os.getenv("TEST_USER_A_PASS",  "BetaUserA_1!")
_USER_B_EMAIL = os.getenv("TEST_USER_B_EMAIL", "beta_user_b@clipsgold-test.com")
_USER_B_PASS  = os.getenv("TEST_USER_B_PASS",  "BetaUserB_2!")

# bola.py _MIN_RESPONSE_TIME_S = 0.05; allow 40 ms for network variance
_BOLA_FLOOR_S = 0.03
_BOLA_CEIL_S  = 5.0

_S = requests.Session()


# ─────────────────────────────────────────────────────────────────────────────
# Token helpers — mirror auth.py exactly
# ─────────────────────────────────────────────────────────────────────────────

def _mint_token(user_id: str, secret: str = JWT_SECRET, ttl_min: int = 15) -> str:
    """Mint a valid HS256 access token matching auth.py's create_access_token()."""
    return jose_jwt.encode(
        {"sub": user_id, "exp": datetime.now(UTC) + timedelta(minutes=ttl_min), "type": "access"},
        secret, algorithm=JWT_ALGO,
    )


def _mint_expired_token(user_id: str) -> str:
    return jose_jwt.encode(
        {"sub": user_id, "exp": datetime.now(UTC) - timedelta(hours=1), "type": "access"},
        JWT_SECRET, algorithm=JWT_ALGO,
    )


def _mint_none_alg_token(user_id: str) -> str:
    """Craft an unsigned JWT (alg=none) — classic JWT vulnerability probe."""
    def _b64url(data: dict) -> str:
        return base64.urlsafe_b64encode(_json.dumps(data).encode()).rstrip(b"=").decode()
    header  = _b64url({"alg": "none", "typ": "JWT"})
    payload = _b64url({
        "sub": user_id,
        "exp": int((datetime.now(UTC) + timedelta(minutes=15)).timestamp()),
        "type": "access",
    })
    return f"{header}.{payload}."


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────────
# HTTP helpers
# ─────────────────────────────────────────────────────────────────────────────

def _register_and_login(email: str, password: str) -> str:
    """
    Register (idempotent) then login.
    If login returns 401 the DB was wiped since the last run — re-register
    with a fresh unique email and try once more.
    """
    def _attempt(e: str, p: str) -> Optional[str]:
        _S.post(f"{BASE_URL}/auth/register", json={"email": e, "password": p})
        r = _S.post(
            f"{BASE_URL}/auth/login",
            data={"username": e, "password": p},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if r.status_code == 200:
            return r.json()["access_token"]
        return None

    token = _attempt(email, password)
    if token:
        return token

    # DB was wiped (fresh server restart) — register with a unique email
    fresh_email = f"{email.split('@')[0]}_{uuid.uuid4().hex[:6]}@clipsgold-test.com"
    token = _attempt(fresh_email, password)
    assert token is not None, (
        f"Login failed for both {email!r} and {fresh_email!r}. "
        f"Check server logs for auth errors."
    )
    return token


def _yt(url: str, token: Optional[str] = None, timeout: int = 10) -> requests.Response:
    return _S.post(
        f"{BASE_URL}/download-youtube",
        json={"url": url},
        headers=_auth(token) if token else {},
        timeout=timeout,
    )


def _server_alive() -> bool:
    try:
        return _S.get(f"{BASE_URL}/", timeout=3).status_code < 500
    except Exception:
        return False


# ─────────────────────────────────────────────────────────────────────────────
# Minimal test media factories
# ─────────────────────────────────────────────────────────────────────────────

def _minimal_mp4() -> bytes:
    """25-byte valid MP4 container (ftyp + mdat). No audio/video tracks."""
    ftyp = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"
    mdat = b"\x00\x00\x00\x09mdat\x00"
    return ftyp + mdat


def _corrupt_mp4() -> bytes:
    """Valid ftyp box header followed by random garbage — structurally broken."""
    return b"\x00\x00\x00\x08ftyp" + os.urandom(512)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def server():
    if not _server_alive():
        pytest.skip(f"Server not reachable at {BASE_URL} — start it first.")


@pytest.fixture(scope="session")
def token_a(server):
    return _register_and_login(_USER_A_EMAIL, _USER_A_PASS)


@pytest.fixture(scope="session")
def token_b(server):
    return _register_and_login(_USER_B_EMAIL, _USER_B_PASS)


@pytest.fixture(scope="session")
def file_id_a(token_a):
    """Upload a minimal MP4 as User A. Returns file_id for BOLA tests."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(_minimal_mp4())
        tmp = Path(f.name)
    try:
        with tmp.open("rb") as fh:
            resp = _S.post(
                f"{BASE_URL}/upload",
                files={"file": ("fixture.mp4", fh, "video/mp4")},
                headers=_auth(token_a),
                timeout=15,
            )
        if resp.status_code not in (200, 201):
            pytest.skip(f"/upload returned {resp.status_code} — BOLA fixture unavailable.")
        body = resp.json()
        fid  = body.get("file_id") or body.get("id")
        if not fid:
            pytest.skip(f"/upload response has no file_id: {body}")
        return fid
    finally:
        tmp.unlink(missing_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# 1. SSRF / Import Guard
# ─────────────────────────────────────────────────────────────────────────────

SSRF_PAYLOADS = [
    pytest.param("http://127.0.0.1",                                                    id="http-loopback"),
    pytest.param("http://localhost:8000",                                                id="http-localhost"),
    pytest.param("https://127.0.0.1",                                                   id="https-loopback"),
    pytest.param("https://127.0.0.1:8000/admin",                                        id="https-loopback-admin"),
    pytest.param("javascript:alert(1)",                                                  id="javascript-scheme"),
    pytest.param("file:///etc/passwd",                                                   id="file-scheme"),
    pytest.param("ftp://youtube.com/watch?v=dQw4w9WgXcQ",                               id="ftp-scheme"),
    pytest.param("https://169.254.169.254/latest/meta-data/",                           id="aws-imds"),
    pytest.param("https://169.254.169.254/latest/meta-data/iam/security-credentials/",  id="aws-imds-iam"),
    pytest.param("https://metadata.google.internal/computeMetadata/v1/",                id="gcp-metadata"),
    pytest.param("https://youtube.com@169.254.169.254/latest/meta-data/",               id="userinfo-aws"),
    pytest.param("https://www.youtube.com@127.0.0.1/watch?v=dQw4w9WgXcQ",              id="userinfo-loopback"),
    pytest.param("https://evil.com@www.youtube.com/watch?v=dQw4w9WgXcQ",               id="userinfo-evil"),
    pytest.param("https://evil.com/watch?v=dQw4w9WgXcQ",                               id="wrong-domain"),
    pytest.param("https://youtube.com.evil.com/watch?v=dQw4w9WgXcQ",                   id="subdomain-spoof"),
    pytest.param("https://notyoutube.com/watch?v=dQw4w9WgXcQ",                         id="lookalike-domain"),
    pytest.param("https://[::1]/watch?v=dQw4w9WgXcQ",                                  id="ipv6-loopback"),
    pytest.param("https://[::1]:8000/watch?v=dQw4w9WgXcQ",                             id="ipv6-loopback-port"),
    pytest.param("https://10.0.0.1/watch?v=dQw4w9WgXcQ",                               id="rfc1918-10"),
    pytest.param("https://192.168.1.1/watch?v=dQw4w9WgXcQ",                            id="rfc1918-192"),
    pytest.param("https://172.16.0.1/watch?v=dQw4w9WgXcQ",                             id="rfc1918-172"),
    pytest.param("https://user:pass@www.youtube.com/watch?v=dQw4w9WgXcQ",              id="embedded-creds"),
    pytest.param("https://www.youtube.com/redirect?q=https://169.254.169.254/",         id="open-redirect"),
    pytest.param("https://www.youtube.com/watch",                                       id="no-video-id"),
    pytest.param("https://www.youtube.com/watch?v=",                                    id="empty-video-id"),
    pytest.param("https://www.youtube.com/watch?v=abc",                                 id="short-video-id"),
    pytest.param("https://www.youtube.com/watch?v=AAAAAAAAAAAAAAAAAAAA",                id="long-video-id"),
    pytest.param("https://www.youtube.com/watch?v=<script>alert(1)</script>",           id="xss-video-id"),
    pytest.param("https://www.youtube.com/watch?v=../../../../etc/passwd",              id="traversal-video-id"),
    pytest.param("",                                                                     id="empty-string"),
    pytest.param("   ",                                                                  id="whitespace"),
    pytest.param("null",                                                                 id="null-string"),
    pytest.param("not-a-url",                                                            id="garbage"),
]


class TestSSRFGuard:

    @pytest.mark.parametrize("url", SSRF_PAYLOADS)
    def test_rejected_with_4xx(self, server, url):
        resp = _yt(url, timeout=10)
        assert 400 <= resp.status_code < 500, (
            f"SSRF BYPASS — '{url}' returned HTTP {resp.status_code}\n"
            f"Body: {resp.text[:400]}"
        )

    @pytest.mark.parametrize("url", SSRF_PAYLOADS)
    def test_does_not_hang(self, server, url):
        t0 = time.monotonic()
        try:
            _yt(url, timeout=10)
        except requests.Timeout:
            pytest.fail(f"Server hung {time.monotonic()-t0:.1f}s on: '{url}'")

    def test_valid_youtube_url_passes_guard(self, server):
        resp = _yt("https://www.youtube.com/watch?v=dQw4w9WgXcQ", timeout=15)
        assert resp.status_code != 400, f"Valid URL rejected by guard: {resp.text[:300]}"

    def test_shorts_url_passes_guard(self, server):
        resp = _yt("https://www.youtube.com/shorts/dQw4w9WgXcQ", timeout=15)
        assert resp.status_code != 400, f"/shorts/ URL rejected: {resp.text[:200]}"

    def test_youtu_be_url_passes_guard(self, server):
        resp = _yt("https://youtu.be/dQw4w9WgXcQ", timeout=15)
        assert resp.status_code != 400, f"youtu.be URL rejected: {resp.text[:200]}"

    def test_no_traceback_in_error_response(self, server):
        resp = _yt("http://127.0.0.1", timeout=10)
        assert "Traceback" not in resp.text, (
            f"Python traceback leaked in SSRF rejection:\n{resp.text[:500]}"
        )

    def test_rapid_fire_never_returns_5xx(self, server):
        for i in range(10):
            resp = _yt("http://127.0.0.1", timeout=5)
            assert resp.status_code < 500, (
                f"Probe #{i+1} returned {resp.status_code}: {resp.text[:200]}"
            )


# ─────────────────────────────────────────────────────────────────────────────
# 2. BOLA — Broken Object Level Authorization
# ─────────────────────────────────────────────────────────────────────────────

_OWNED_ENDPOINTS = [
    pytest.param("GET",    "/transcription/{fid}",    id="GET-transcription"),
    pytest.param("POST",   "/transcribe/{fid}",       id="POST-transcribe"),
    pytest.param("POST",   "/analyze/{fid}",          id="POST-analyze"),
    pytest.param("GET",    "/clips/{fid}/candidates", id="GET-candidates"),
    pytest.param("POST",   "/extract-clips/{fid}",    id="POST-extract-clips"),
    pytest.param("GET",    "/download/{fid}",         id="GET-download"),
    pytest.param("DELETE", "/cleanup/{fid}",          id="DELETE-cleanup"),
]


class TestBOLA:

    @pytest.mark.slow
    @pytest.mark.parametrize("method,path_tpl", _OWNED_ENDPOINTS)
    def test_cross_user_access_denied(self, token_b, file_id_a, method, path_tpl):
        url  = f"{BASE_URL}{path_tpl.format(fid=file_id_a)}"
        resp = _S.request(method, url, headers=_auth(token_b), timeout=10, json={})
        assert resp.status_code == 404, (
            f"BOLA: User B got HTTP {resp.status_code} on {method} {path_tpl}\n"
            f"Expected 404 (not 403, not 200). Body: {resp.text[:300]}"
        )

    @pytest.mark.slow
    @pytest.mark.parametrize("method,path_tpl", _OWNED_ENDPOINTS)
    def test_constant_time_floor(self, token_b, file_id_a, method, path_tpl):
        """404 must take >= _BOLA_FLOOR_S — sub-ms 404 is a timing oracle."""
        url = f"{BASE_URL}{path_tpl.format(fid=file_id_a)}"
        t0  = time.monotonic()
        _S.request(method, url, headers=_auth(token_b), timeout=10, json={})
        elapsed = time.monotonic() - t0
        assert elapsed >= _BOLA_FLOOR_S, (
            f"Timing oracle on {method} {path_tpl}: {elapsed*1000:.1f} ms "
            f"(floor {_BOLA_FLOOR_S*1000:.0f} ms). _constant_time_404() may be inactive."
        )
        assert elapsed <= _BOLA_CEIL_S, (
            f"Response too slow ({elapsed:.2f}s) — possible deadlock."
        )

    @pytest.mark.slow
    def test_fabricated_file_id_returns_404(self, token_a):
        resp = _S.get(
            f"{BASE_URL}/transcription/{uuid.uuid4().hex}",
            headers=_auth(token_a), timeout=10,
        )
        assert resp.status_code == 404, (
            f"Fabricated file_id returned {resp.status_code}: {resp.text[:200]}"
        )

    @pytest.mark.slow
    def test_sequential_enumeration_timing_variance(self, token_a):
        """Std-dev of 6 sequential fake-ID probes must be < 30 ms."""
        timings = []
        for _ in range(6):
            t0 = time.monotonic()
            _S.get(
                f"{BASE_URL}/transcription/{uuid.uuid4().hex}",
                headers=_auth(token_a), timeout=10,
            )
            timings.append(time.monotonic() - t0)
        stdev_ms = statistics.stdev(timings) * 1000
        assert stdev_ms < 30, (
            f"High timing variance ({stdev_ms:.1f} ms std-dev) — timing oracle risk.\n"
            f"Samples: {[f'{t*1000:.1f}ms' for t in timings]}"
        )

    def test_unauthenticated_returns_401_or_403(self, server):
        """POST /auth/logout with no token must return 401/403."""
        resp = _S.post(f"{BASE_URL}/auth/logout", timeout=10)
        assert resp.status_code in (401, 403), (
            f"Unauthenticated request returned {resp.status_code}: {resp.text[:200]}"
        )

    def test_forged_jwt_wrong_secret_rejected(self, server):
        """JWT signed with wrong secret must be rejected by /auth/logout."""
        bad = _mint_token(user_id="evil-user", secret="completely-wrong-secret")
        resp = _S.post(
            f"{BASE_URL}/auth/logout",
            headers=_auth(bad), timeout=10,
        )
        assert resp.status_code in (401, 403), (
            f"Forged JWT (wrong secret) accepted! HTTP {resp.status_code}: {resp.text[:200]}"
        )

    def test_expired_jwt_rejected(self, server):
        """Expired JWT must be rejected by /auth/logout."""
        expired = _mint_expired_token("some-user-id")
        resp = _S.post(
            f"{BASE_URL}/auth/logout",
            headers=_auth(expired), timeout=10,
        )
        assert resp.status_code in (401, 403), (
            f"Expired JWT accepted! HTTP {resp.status_code}: {resp.text[:200]}"
        )

    def test_alg_none_jwt_rejected(self, server):
        """alg=none unsigned JWT must be rejected — classic JWT vulnerability."""
        none_tok = _mint_none_alg_token("evil-user-id")
        resp = _S.post(
            f"{BASE_URL}/auth/logout",
            headers=_auth(none_tok), timeout=10,
        )
        assert resp.status_code in (401, 403), (
            f"alg=none JWT accepted! HTTP {resp.status_code}: {resp.text[:200]}"
        )

    def test_user_a_can_access_own_resource(self, token_a, file_id_a):
        """Sanity: User A must not be blocked by the ownership guard on their own file."""
        resp = _S.get(
            f"{BASE_URL}/transcription/{file_id_a}",
            headers=_auth(token_a), timeout=10,
        )
        assert resp.status_code not in (401, 403), (
            f"User A blocked from own resource: HTTP {resp.status_code}: {resp.text[:200]}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# 3. Integrity — Broken Files & Edge-Case Inputs
# ─────────────────────────────────────────────────────────────────────────────

class TestIntegrity:

    @pytest.mark.slow
    def test_corrupt_mp4_does_not_cause_500(self, token_a):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(_corrupt_mp4())
            tmp = Path(f.name)
        try:
            with tmp.open("rb") as fh:
                resp = _S.post(
                    f"{BASE_URL}/upload",
                    files={"file": ("corrupt.mp4", fh, "video/mp4")},
                    headers=_auth(token_a), timeout=15,
                )
            assert resp.status_code != 500, f"Corrupt MP4 caused 500: {resp.text[:300]}"
            assert "Traceback" not in resp.text, "Raw traceback leaked in response."
        finally:
            tmp.unlink(missing_ok=True)

    @pytest.mark.slow
    def test_no_audio_mp4_transcribe_fails_gracefully(self, token_a):
        """Audio-less MP4: upload succeeds or is rejected cleanly; /transcribe must not 500."""
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(_minimal_mp4())
            tmp = Path(f.name)
        try:
            with tmp.open("rb") as fh:
                up = _S.post(
                    f"{BASE_URL}/upload",
                    files={"file": ("silent.mp4", fh, "video/mp4")},
                    headers=_auth(token_a), timeout=15,
                )
            if up.status_code not in (200, 201):
                pytest.skip(f"/upload returned {up.status_code}.")
            body    = up.json()
            file_id = body.get("file_id") or body.get("id")
            if not file_id:
                pytest.skip(f"No file_id in upload response: {body}")

            resp = _S.post(
                f"{BASE_URL}/transcribe/{file_id}",
                headers=_auth(token_a), timeout=60,
            )
            assert resp.status_code != 500, (
                f"Audio-less MP4 caused unhandled 500 on /transcribe: {resp.text[:300]}"
            )
            assert "Traceback" not in resp.text, (
                f"Raw traceback leaked in /transcribe response: {resp.text[:400]}"
            )
        finally:
            tmp.unlink(missing_ok=True)

    @pytest.mark.slow
    def test_zero_byte_file_rejected(self, token_a):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(b"")
            tmp = Path(f.name)
        try:
            with tmp.open("rb") as fh:
                resp = _S.post(
                    f"{BASE_URL}/upload",
                    files={"file": ("empty.mp4", fh, "video/mp4")},
                    headers=_auth(token_a), timeout=10,
                )
            assert 400 <= resp.status_code < 500, (
                f"Zero-byte file not rejected: HTTP {resp.status_code} {resp.text[:200]}"
            )
        finally:
            tmp.unlink(missing_ok=True)

    @pytest.mark.slow
    def test_non_mp4_extension_rejected(self, token_a):
        with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as f:
            f.write(b"MZ" + os.urandom(256))
            tmp = Path(f.name)
        try:
            with tmp.open("rb") as fh:
                resp = _S.post(
                    f"{BASE_URL}/upload",
                    files={"file": ("malware.exe", fh, "application/octet-stream")},
                    headers=_auth(token_a), timeout=10,
                )
            assert 400 <= resp.status_code < 500, (
                f".exe file not rejected: HTTP {resp.status_code} {resp.text[:200]}"
            )
        finally:
            tmp.unlink(missing_ok=True)

    @pytest.mark.slow
    def test_oversized_filename_does_not_500(self, token_a):
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            f.write(_minimal_mp4())
            tmp = Path(f.name)
        try:
            with tmp.open("rb") as fh:
                resp = _S.post(
                    f"{BASE_URL}/upload",
                    files={"file": ("A" * 1000 + ".mp4", fh, "video/mp4")},
                    headers=_auth(token_a), timeout=10,
                )
            assert resp.status_code != 500, (
                f"Oversized filename caused 500: {resp.text[:200]}"
            )
        finally:
            tmp.unlink(missing_ok=True)

    def test_render_nonexistent_file_id_returns_4xx(self, token_a):
        """Render job for a nonexistent file_id must return 4xx — no Redis lock leak."""
        resp = _S.post(
            f"{BASE_URL}/extract-clips/{uuid.uuid4().hex}",
            headers=_auth(token_a), json={}, timeout=10,
        )
        assert 400 <= resp.status_code < 500, (
            f"Nonexistent file_id for render returned {resp.status_code}: {resp.text[:200]}"
        )

    def test_private_video_id_does_not_hang(self, server):
        """Valid URL shape, non-existent video ID — must not hang or leak traceback."""
        t0 = time.monotonic()
        try:
            resp = _yt("https://www.youtube.com/watch?v=XXXXXXXXXXX", timeout=30)
            if resp.status_code == 500:
                assert "Traceback" not in resp.text, (
                    f"Raw traceback leaked in 500 response: {resp.text[:400]}"
                )
        except requests.Timeout:
            pytest.fail(f"Server hung {time.monotonic()-t0:.1f}s on private video ID.")

    def test_sql_injection_in_file_id_path(self, token_a):
        """SQL injection in file_id path param must return 4xx, not 500."""
        payloads = [
            "' OR '1'='1",
            "1; DROP TABLE videos; --",
            "../../etc/passwd",
            "<script>alert(1)</script>",
        ]
        for payload in payloads:
            resp = _S.get(
                f"{BASE_URL}/transcription/{payload}",
                headers=_auth(token_a), timeout=10,
            )
            assert resp.status_code < 500, (
                f"SQL/path injection '{payload}' caused {resp.status_code}: {resp.text[:200]}"
            )
            assert "Traceback" not in resp.text, (
                f"Traceback leaked for injection payload '{payload}'"
            )
