"""
Health check utilities for ClipsGold.
Verifies connectivity to Redis, PostgreSQL, and FFmpeg availability.
"""

import subprocess
import os
from typing import Dict, Any
from pathlib import Path


def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity."""
    try:
        import redis
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client = redis.from_url(redis_url, socket_connect_timeout=2)
        client.ping()
        return {"status": "ok", "message": "Redis connected"}
    except Exception as e:
        return {"status": "error", "message": f"Redis connection failed: {str(e)}"}


def check_postgres() -> Dict[str, Any]:
    """Check PostgreSQL connectivity."""
    try:
        from sqlalchemy import create_engine, text
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            return {"status": "error", "message": "DATABASE_URL not set"}
        
        # Fix postgres:// to postgresql:// for SQLAlchemy 2.0+
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        
        engine = create_engine(database_url, connect_args={"connect_timeout": 5})
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
        return {"status": "ok", "message": "PostgreSQL connected"}
    except Exception as e:
        return {"status": "error", "message": f"PostgreSQL connection failed: {str(e)}"}


def check_ffmpeg() -> Dict[str, Any]:
    """Check FFmpeg installation and version."""
    try:
        # Try to find ffmpeg
        ffmpeg_path = "ffmpeg"
        
        # Check if ffmpeg is in PATH
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            # Extract version from first line
            version_line = result.stdout.split('\n')[0] if result.stdout else "unknown"
            return {
                "status": "ok",
                "message": "FFmpeg available",
                "version": version_line
            }
        else:
            return {"status": "error", "message": "FFmpeg command failed"}
    
    except FileNotFoundError:
        return {"status": "error", "message": "FFmpeg not found in PATH"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "FFmpeg version check timeout"}
    except Exception as e:
        return {"status": "error", "message": f"FFmpeg check failed: {str(e)}"}


def check_disk_space() -> Dict[str, Any]:
    """Check available disk space for uploads/outputs."""
    try:
        import shutil
        
        # Check space in current directory (where uploads/outputs are)
        total, used, free = shutil.disk_usage(".")
        
        free_gb = free / (1024**3)
        total_gb = total / (1024**3)
        used_percent = (used / total) * 100
        
        status = "ok" if free_gb > 5 else "warning" if free_gb > 1 else "critical"
        
        return {
            "status": status,
            "message": f"{free_gb:.2f} GB free ({used_percent:.1f}% used)",
            "free_gb": round(free_gb, 2),
            "total_gb": round(total_gb, 2),
            "used_percent": round(used_percent, 1)
        }
    except Exception as e:
        return {"status": "error", "message": f"Disk check failed: {str(e)}"}


def check_assets() -> Dict[str, Any]:
    """Check if required asset directories exist and have content."""
    try:
        assets_dir = Path(__file__).parent / "assets"
        bg_dir = assets_dir / "background_videos"
        sfx_dir = assets_dir / "sfx"
        
        issues = []
        
        # Check background videos
        if not bg_dir.exists():
            issues.append("background_videos directory missing")
        else:
            bg_count = len(list(bg_dir.glob("*.mp4")))
            if bg_count == 0:
                issues.append("No background videos found (run seed_assets.sh)")
        
        # Check SFX
        if not sfx_dir.exists():
            issues.append("sfx directory missing")
        else:
            sfx_count = len(list(sfx_dir.glob("*.mp3")))
            if sfx_count == 0:
                issues.append("No SFX files found (run seed_assets.sh)")
        
        if issues:
            return {
                "status": "warning",
                "message": "; ".join(issues)
            }
        else:
            return {
                "status": "ok",
                "message": "All assets available"
            }
    except Exception as e:
        return {"status": "error", "message": f"Assets check failed: {str(e)}"}


def perform_health_check() -> Dict[str, Any]:
    """Perform comprehensive health check of all system components."""
    checks = {
        "redis": check_redis(),
        "postgres": check_postgres(),
        "ffmpeg": check_ffmpeg(),
        "disk_space": check_disk_space(),
        "assets": check_assets()
    }
    
    # Determine overall status
    has_error = any(c["status"] == "error" for c in checks.values())
    has_warning = any(c["status"] == "warning" for c in checks.values())
    
    if has_error:
        overall_status = "unhealthy"
    elif has_warning:
        overall_status = "degraded"
    else:
        overall_status = "healthy"
    
    return {
        "status": overall_status,
        "checks": checks,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat()
    }
