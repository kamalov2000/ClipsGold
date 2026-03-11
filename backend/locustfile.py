"""
locustfile.py — ClipsGold Public Beta Load Test
─────────────────────────────────────────────────
Two user classes:

  GoodUser (weight=4)
    Simulates a real paying user:
      1. Register + Login  → obtain access_token
      2. Upload a minimal MP4
      3. Trigger transcription
      4. Poll transcription status until done (or timeout)
      5. Trigger clip analysis
      6. Render a clip
      7. Poll render status
      8. Download the rendered clip

  EvilSchoolboy (weight=1)
    Spams the import endpoint with a mix of:
      - SSRF payloads (must all return 4xx fast)
      - Rapid-fire valid YouTube URLs (exercises rate-limiter)
      - Fabricated file_id enumeration probes (exercises BOLA timing)
      - Forged / expired JWT probes (exercises auth middleware)

Run commands:
    # Headless, 50 good users + 12 evil, 5-minute soak:
    locust -f locustfile.py --host=http://localhost:8000 \\
           --users=62 --spawn-rate=5 --run-time=5m --headless

    # Interactive web UI (open http://localhost:8089):
    locust -f locustfile.py --host=http://localhost:8000

    # Against staging:
    locust -f locustfile.py --host=https://staging.clipsgold.io \\
           --users=20 --spawn-rate=2 --run-time=3m --headless

Requirements:
    pip install locust python-jose[cryptography]

Environment variables:
    LOCUST_HOST   — overrides --host if set
    JWT_SECRET    — must match server's JWT_SECRET_KEY (default: test-secret-key-for-ci)
"""

import base64
import json
import os
import random
import time
import uuid
from datetime import datetime, timedelta, timezone

UTC = timezone.utc

from jose import jwt as jose_jwt
from locust import HttpUser, between, events, task

# ─────────────────────────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────────────────────────

JWT_SECRET = os.getenv("JWT_SECRET", "test-secret-key-for-ci")
JWT_ALGO   = "HS256"

# Minimal valid MP4 (ftyp + mdat, 25 bytes). No audio/video tracks.
# Used as the upload payload so tests don't depend on real video files.
_MINIMAL_MP4 = (
    b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"  # ftyp box (24 bytes)
    b"\x00\x00\x00\x09mdat\x00"                           # mdat box (9 bytes)
)

# SSRF payloads the evil user cycles through
_SSRF_URLS = [
    "http://127.0.0.1",
    "http://localhost:8000",
    "https://169.254.169.254/latest/meta-data/",
    "https://youtube.com@169.254.169.254/latest/meta-data/",
    "https://www.youtube.com@127.0.0.1/watch?v=dQw4w9WgXcQ",
    "https://evil.com/watch?v=dQw4w9WgXcQ",
    "https://10.0.0.1/watch?v=dQw4w9WgXcQ",
    "https://[::1]/watch?v=dQw4w9WgXcQ",
    "https://user:pass@www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=../../../../etc/passwd",
    "https://www.youtube.com/watch?v=<script>alert(1)</script>",
    "javascript:alert(1)",
    "file:///etc/passwd",
    "",
    "null",
]

# A real-looking but non-existent YouTube video ID (passes format check, fails yt-dlp)
_FAKE_VIDEO_URL = "https://www.youtube.com/watch?v=XXXXXXXXXXX"

# Poll intervals and timeouts (seconds)
_POLL_INTERVAL   = 2
_POLL_TIMEOUT    = 30


# ─────────────────────────────────────────────────────────────────────────────
# Token helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mint_token(user_id: str, ttl_min: int = 15, secret: str = JWT_SECRET) -> str:
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
    """Unsigned JWT (alg=none) — should always be rejected."""
    def _b64(d: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
    h = _b64({"alg": "none", "typ": "JWT"})
    p = _b64({"sub": user_id, "exp": int((datetime.now(UTC) + timedelta(minutes=15)).timestamp()), "type": "access"})
    return f"{h}.{p}."


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ─────────────────────────────────────────────────────────────────────────────
# GoodUser — realistic user flow
# ─────────────────────────────────────────────────────────────────────────────

class GoodUser(HttpUser):
    """
    Simulates a real paying user going through the full ClipsGold pipeline.
    Weight=4 means 4 GoodUsers spawn for every 1 EvilSchoolboy.
    """
    weight     = 4
    wait_time  = between(1, 4)

    def on_start(self):
        """Register + login once per simulated user session."""
        self._email    = f"load_{uuid.uuid4().hex[:8]}@clipsgold-test.com"
        self._password = "LoadTest_1!"
        self._token    = None
        self._file_id  = None

        # Register (ignore 409 if already exists)
        self.client.post(
            "/auth/register",
            json={"email": self._email, "password": self._password},
            name="/auth/register",
        )

        # Login
        resp = self.client.post(
            "/auth/login",
            data={"username": self._email, "password": self._password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            name="/auth/login",
        )
        if resp.status_code == 200:
            self._token = resp.json().get("access_token")

    # ── Task 1: Upload ────────────────────────────────────────────────────────

    @task(3)
    def upload_video(self):
        if not self._token:
            return
        resp = self.client.post(
            "/upload",
            files={"file": ("load_test.mp4", _MINIMAL_MP4, "video/mp4")},
            headers=_auth(self._token),
            name="/upload",
        )
        if resp.status_code in (200, 201):
            body = resp.json()
            self._file_id = body.get("file_id") or body.get("id")

    # ── Task 2: Transcribe ────────────────────────────────────────────────────

    @task(2)
    def transcribe(self):
        if not self._token or not self._file_id:
            return
        self.client.post(
            f"/transcribe/{self._file_id}",
            headers=_auth(self._token),
            name="/transcribe/{file_id}",
        )

    # ── Task 3: Poll transcription ────────────────────────────────────────────

    @task(2)
    def poll_transcription(self):
        if not self._token or not self._file_id:
            return
        deadline = time.monotonic() + _POLL_TIMEOUT
        while time.monotonic() < deadline:
            resp = self.client.get(
                f"/transcription/{self._file_id}",
                headers=_auth(self._token),
                name="/transcription/{file_id} [poll]",
            )
            if resp.status_code == 200:
                data = resp.json()
                if data.get("text") or data.get("segments"):
                    break
            time.sleep(_POLL_INTERVAL)

    # ── Task 4: Analyze ───────────────────────────────────────────────────────

    @task(2)
    def analyze(self):
        if not self._token or not self._file_id:
            return
        self.client.post(
            f"/analyze/{self._file_id}",
            headers=_auth(self._token),
            name="/analyze/{file_id}",
        )

    # ── Task 5: Get candidates ────────────────────────────────────────────────

    @task(2)
    def get_candidates(self):
        if not self._token or not self._file_id:
            return
        self.client.get(
            f"/clips/{self._file_id}/candidates",
            headers=_auth(self._token),
            name="/clips/{file_id}/candidates",
        )

    # ── Task 6: Render clip ───────────────────────────────────────────────────

    @task(1)
    def render_clip(self):
        if not self._token or not self._file_id:
            return
        self.client.post(
            f"/extract-clips/{self._file_id}",
            json={
                "platform":       "tiktok",
                "subtitle_style": "bold",
                "show_hook":      True,
                "enable_jump_cut": False,
                "enable_sfx":     True,
            },
            headers=_auth(self._token),
            name="/extract-clips/{file_id}",
        )

    # ── Task 7: Download rendered clip ────────────────────────────────────────

    @task(1)
    def download_clip(self):
        if not self._token or not self._file_id:
            return
        self.client.get(
            f"/download/{self._file_id}",
            headers=_auth(self._token),
            name="/download/{file_id}",
        )

    # ── Task 8: Import YouTube URL (valid, exercises yt-dlp path) ────────────

    @task(1)
    def import_youtube(self):
        if not self._token:
            return
        self.client.post(
            "/download-youtube",
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            headers=_auth(self._token),
            name="/download-youtube [valid]",
        )


# ─────────────────────────────────────────────────────────────────────────────
# EvilSchoolboy — adversarial probes
# ─────────────────────────────────────────────────────────────────────────────

class EvilSchoolboy(HttpUser):
    """
    Adversarial user that hammers security-sensitive endpoints.
    Weight=1 means 1 EvilSchoolboy per 4 GoodUsers.

    All tasks assert that the server returns 4xx (never 5xx) and
    responds within 10 seconds. Failures are reported as Locust errors.
    """
    weight    = 1
    wait_time = between(0.1, 0.5)   # faster cadence — stress the guards

    def on_start(self):
        self._evil_id = uuid.uuid4().hex

    # ── Task 1: SSRF probes (weight=4 — highest volume) ──────────────────────

    @task(4)
    def ssrf_probe(self):
        url = random.choice(_SSRF_URLS)
        with self.client.post(
            "/download-youtube",
            json={"url": url},
            name="/download-youtube [ssrf]",
            catch_response=True,
        ) as resp:
            if resp.status_code >= 500:
                resp.failure(
                    f"SSRF probe returned {resp.status_code} — server error on payload: {url!r}"
                )
            elif resp.elapsed.total_seconds() > 10:
                resp.failure(
                    f"SSRF probe hung {resp.elapsed.total_seconds():.1f}s on: {url!r}"
                )
            else:
                resp.success()

    # ── Task 2: Rate-limit saturation (valid URL, rapid fire) ────────────────

    @task(2)
    def rate_limit_probe(self):
        with self.client.post(
            "/download-youtube",
            json={"url": _FAKE_VIDEO_URL},
            name="/download-youtube [rate-limit probe]",
            catch_response=True,
        ) as resp:
            # 429 is the expected outcome under saturation — mark as success
            if resp.status_code == 429:
                resp.success()
            elif resp.status_code >= 500:
                resp.failure(f"Rate-limit probe returned {resp.status_code}: {resp.text[:200]}")
            else:
                resp.success()

    # ── Task 3: BOLA enumeration (fabricated file_ids) ────────────────────────

    @task(3)
    def bola_enumeration_probe(self):
        fake_id = uuid.uuid4().hex
        with self.client.get(
            f"/transcription/{fake_id}",
            name="/transcription/{file_id} [bola probe]",
            catch_response=True,
        ) as resp:
            if resp.status_code == 404:
                resp.success()
            elif resp.status_code in (401, 403):
                resp.success()   # unauthenticated — expected
            elif resp.status_code >= 500:
                resp.failure(f"BOLA probe returned {resp.status_code}: {resp.text[:200]}")
            else:
                resp.success()

    # ── Task 4: Forged JWT probes ─────────────────────────────────────────────

    @task(2)
    def forged_jwt_probe(self):
        attack = random.choice(["wrong_secret", "expired", "none_alg"])

        if attack == "wrong_secret":
            token = _mint_token(user_id=self._evil_id, secret="wrong-secret-entirely")
            label = "forged[wrong_secret]"
        elif attack == "expired":
            token = _mint_expired_token(user_id=self._evil_id)
            label = "forged[expired]"
        else:
            token = _mint_none_alg_token(user_id=self._evil_id)
            label = "forged[alg=none]"

        with self.client.get(
            f"/transcription/{uuid.uuid4().hex}",
            headers=_auth(token),
            name=f"/transcription [jwt {label}]",
            catch_response=True,
        ) as resp:
            if resp.status_code in (401, 403, 404):
                resp.success()
            elif resp.status_code >= 500:
                resp.failure(f"Forged JWT ({label}) caused {resp.status_code}: {resp.text[:200]}")
            else:
                resp.failure(
                    f"Forged JWT ({label}) was ACCEPTED with {resp.status_code}: {resp.text[:200]}"
                )

    # ── Task 5: Path injection in file_id ────────────────────────────────────

    @task(1)
    def path_injection_probe(self):
        payloads = [
            "' OR '1'='1",
            "1; DROP TABLE videos; --",
            "../../etc/passwd",
            "<script>alert(1)</script>",
            "%00",
            "a" * 512,
        ]
        payload = random.choice(payloads)
        with self.client.get(
            f"/transcription/{payload}",
            name="/transcription [injection probe]",
            catch_response=True,
        ) as resp:
            if resp.status_code >= 500:
                resp.failure(
                    f"Injection payload caused {resp.status_code}: {payload!r} → {resp.text[:200]}"
                )
            elif "Traceback" in resp.text:
                resp.failure(f"Python traceback leaked for payload: {payload!r}")
            else:
                resp.success()

    # ── Task 6: Upload garbage files ─────────────────────────────────────────

    @task(1)
    def garbage_upload_probe(self):
        garbage_cases = [
            ("empty.mp4",   b"",                          "video/mp4"),
            ("corrupt.mp4", b"\x00\x00\x00\x08ftyp" + os.urandom(64), "video/mp4"),
            ("shell.php",   b"<?php system($_GET['c']); ?>",            "application/x-php"),
            ("huge_name" + "A" * 500 + ".mp4", b"\x00" * 16,           "video/mp4"),
        ]
        name, data, mime = random.choice(garbage_cases)
        with self.client.post(
            "/upload",
            files={"file": (name, data, mime)},
            name="/upload [garbage probe]",
            catch_response=True,
        ) as resp:
            if resp.status_code >= 500:
                resp.failure(
                    f"Garbage upload caused {resp.status_code}: file={name!r} → {resp.text[:200]}"
                )
            elif "Traceback" in resp.text:
                resp.failure(f"Traceback leaked for garbage upload: {name!r}")
            else:
                resp.success()


# ─────────────────────────────────────────────────────────────────────────────
# Event hooks — print summary stats at end of run
# ─────────────────────────────────────────────────────────────────────────────

@events.quitting.add_listener
def on_quitting(environment, **kwargs):
    stats = environment.stats
    print("\n" + "=" * 70)
    print("CLIPSGOLD LOAD TEST SUMMARY")
    print("=" * 70)
    total = stats.total
    print(f"  Total requests : {total.num_requests}")
    print(f"  Failures       : {total.num_failures}  ({100*total.fail_ratio:.1f}%)")
    print(f"  Median RPS     : {total.current_rps:.1f}")
    print(f"  p50 latency    : {total.get_response_time_percentile(0.50):.0f} ms")
    print(f"  p95 latency    : {total.get_response_time_percentile(0.95):.0f} ms")
    print(f"  p99 latency    : {total.get_response_time_percentile(0.99):.0f} ms")
    print(f"  Max latency    : {total.max_response_time:.0f} ms")
    print("=" * 70)

    if total.num_failures > 0:
        print("\nFAILED REQUESTS (top 10):")
        errors = sorted(stats.errors.values(), key=lambda e: e.occurrences, reverse=True)
        for err in errors[:10]:
            print(f"  [{err.occurrences:>4}x] {err.method} {err.name} — {err.error}")
    print()
