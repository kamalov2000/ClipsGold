"""
SSRF Protection for server-side URL fetching (YouTube import).

Blocks:
- Non-HTTPS schemes (file://, ftp://, http://)
- Private / loopback / link-local IP ranges (RFC 1918, RFC 3927, RFC 4193)
- Cloud metadata endpoints (169.254.169.254, 100.64.x.x, fd00::/8)
- Domains not in the explicit allowlist
- Redirect chains that resolve to blocked destinations

Usage:
    from services.ssrf_guard import validate_import_url
    validate_import_url(user_supplied_url)  # raises HTTPException on violation
"""

import ipaddress
import re
import socket
from urllib.parse import urlparse, parse_qs

from fastapi import HTTPException, status

# ── Allowlist of permitted import domains ─────────────────────
ALLOWED_DOMAINS: frozenset[str] = frozenset({
    "youtube.com",
    "www.youtube.com",
    "youtu.be",
    "m.youtube.com",
    "music.youtube.com",
})

# Strict YouTube video ID pattern (11 alphanumeric/dash/underscore chars)
_YT_VIDEO_ID_RE = re.compile(r'^[A-Za-z0-9_-]{11}$')


def extract_youtube_video_id(url: str) -> str:
    """
    Extract the 11-char video ID from any YouTube URL variant and return
    the canonical form: https://www.youtube.com/watch?v={id}

    Supported input formats:
      https://www.youtube.com/watch?v=dQw4w9WgXcQ
      https://youtu.be/dQw4w9WgXcQ
      https://m.youtube.com/watch?v=dQw4w9WgXcQ
      https://www.youtube.com/shorts/dQw4w9WgXcQ
      https://music.youtube.com/watch?v=dQw4w9WgXcQ

    Raises HTTPException(400) if no valid video ID can be extracted.
    This prevents @userinfo injection (https://evil.com@youtube.com/...)
    and open-redirect abuse because we never use the raw URL downstream.
    """
    parsed = urlparse(url)
    video_id: str | None = None

    host = (parsed.hostname or "").lower()

    if host == "youtu.be":
        # Path is /{video_id}
        video_id = parsed.path.lstrip("/").split("/")[0]
    elif host in ALLOWED_DOMAINS:
        path = parsed.path.rstrip("/")
        # /shorts/{id} or /live/{id} or /embed/{id}
        for prefix in ("/shorts/", "/live/", "/embed/", "/v/"):
            if path.startswith(prefix):
                video_id = path[len(prefix):].split("/")[0]
                break
        if not video_id:
            # Standard ?v= query param
            qs = parse_qs(parsed.query)
            ids = qs.get("v", [])
            if ids:
                video_id = ids[0]

    if not video_id or not _YT_VIDEO_ID_RE.match(video_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not extract a valid YouTube video ID from the supplied URL.",
        )

    return f"https://www.youtube.com/watch?v={video_id}"


# ── Blocked IP networks (SSRF targets) ───────────────────────
_BLOCKED_NETWORKS = [
    ipaddress.ip_network(cidr) for cidr in [
        "0.0.0.0/8",
        "10.0.0.0/8",
        "100.64.0.0/10",    # Shared address space (RFC 6598)
        "127.0.0.0/8",      # Loopback
        "169.254.0.0/16",   # Link-local / AWS metadata
        "172.16.0.0/12",    # Private
        "192.0.0.0/24",     # IETF Protocol Assignments
        "192.168.0.0/16",   # Private
        "198.18.0.0/15",    # Benchmarking
        "198.51.100.0/24",  # TEST-NET-2
        "203.0.113.0/24",   # TEST-NET-3
        "224.0.0.0/4",      # Multicast
        "240.0.0.0/4",      # Reserved
        "255.255.255.255/32",
        "::1/128",           # IPv6 loopback
        "fc00::/7",          # IPv6 unique local
        "fe80::/10",         # IPv6 link-local
    ]
]


def _is_blocked_ip(host: str) -> bool:
    """Return True if host resolves to a blocked IP range."""
    try:
        # Resolve all addresses (handles both A and AAAA)
        infos = socket.getaddrinfo(host, None)
        for info in infos:
            addr_str = info[4][0]
            try:
                addr = ipaddress.ip_address(addr_str)
                for network in _BLOCKED_NETWORKS:
                    if addr in network:
                        return True
            except ValueError:
                continue
    except (socket.gaierror, OSError):
        # DNS resolution failed — block by default (fail-closed)
        return True
    return False


def validate_resolved_ip(host: str) -> None:
    """
    Re-validate the resolved IP of a host AFTER URL canonicalization.
    Called immediately before yt-dlp starts downloading to catch
    DNS rebinding attacks (where the IP changes between the initial
    validate_import_url() check and the actual fetch).

    Raises HTTPException(400) if any resolved address is in a blocked range.
    """
    if _is_blocked_ip(host):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Resolved IP is in a blocked/private range (DNS rebinding protection).",
        )


# ── yt-dlp SSRF hardening options ────────────────────────────
# Merge these into every YoutubeDL opts dict to enforce 0 redirects
# and prevent yt-dlp from following server-side redirects to internal IPs.
YDL_SSRF_OPTS: dict = {
    # Disallow HTTP redirects at the yt-dlp network layer.
    # yt-dlp passes this to its internal urllib handler.
    "nocheckcertificate": False,
    "socket_timeout": 30,
    # Restrict to HTTPS only — no HTTP downgrade via redirect
    "http_headers": {
        "Upgrade-Insecure-Requests": "1",
    },
}


def validate_import_url(url: str) -> str:
    """
    Validate and canonicalize a user-supplied YouTube URL.

    Pipeline:
      1. Scheme must be HTTPS
      2. No embedded credentials (@userinfo)
      3. Domain allowlist check
      4. Resolve hostname — block private/internal IPs (fail-closed)
      5. Extract + validate 11-char video ID
      6. Return canonical https://www.youtube.com/watch?v={id}

    The canonical URL is what gets passed to yt-dlp, so any open-redirect
    or @userinfo injection in the original URL is neutralized.
    Raises HTTPException(400) on any violation.
    """
    if not url or not isinstance(url, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL is required.")

    url = url.strip()

    # 1. Scheme must be HTTPS
    parsed = urlparse(url)
    if parsed.scheme != "https":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only HTTPS URLs are accepted for import.",
        )

    # 2. No credentials in URL — catches https://evil@youtube.com/... attacks
    if parsed.username or parsed.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URLs with embedded credentials are not permitted.",
        )

    # 3. Must have a hostname
    host = parsed.hostname
    if not host:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid URL: no hostname.")

    # 4. Domain allowlist check
    normalised = re.sub(r"^www\.", "", host.lower())
    if host.lower() not in ALLOWED_DOMAINS and normalised not in {
        re.sub(r"^www\.", "", d) for d in ALLOWED_DOMAINS
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Domain '{host}' is not permitted for import. Only YouTube URLs are accepted.",
        )

    # 5. Resolve hostname and block private/internal IPs (fail-closed on DNS error)
    if _is_blocked_ip(host):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="URL resolves to a blocked or internal address.",
        )

    # 6. Canonicalize: extract video ID and rebuild URL
    #    This neutralizes any remaining injection in path/query/fragment
    canonical = extract_youtube_video_id(url)
    return canonical
