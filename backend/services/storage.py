"""
S3-compatible object storage service.

Supports AWS S3, Cloudflare R2, MinIO (any boto3-compatible endpoint).

Environment variables:
  S3_BUCKET          — bucket name (required)
  S3_REGION          — AWS region (default: us-east-1)
  S3_ENDPOINT_URL    — custom endpoint for R2/MinIO (optional)
  AWS_ACCESS_KEY_ID  — access key
  AWS_SECRET_ACCESS_KEY — secret key
  S3_PRESIGN_EXPIRY  — presigned URL TTL in seconds (default: 3600)

Key layout:
  uploads/{user_id}/{file_id}.mp4
  outputs/{user_id}/{file_id}_transcription.json
  clips/{user_id}/{clip_filename}
  thumbnails/{user_id}/{thumb_filename}
  meta/{user_id}/{file_id}_clip_{n}_meta.json
"""

import os
from pathlib import Path
from typing import Optional

import boto3
from boto3.s3.transfer import TransferConfig
from botocore.exceptions import ClientError
from dotenv import load_dotenv

try:
    import sentry_sdk
    _SENTRY_AVAILABLE = True
except ImportError:
    _SENTRY_AVAILABLE = False

load_dotenv()

_S3_BUCKET = os.getenv("S3_BUCKET", "")
_S3_REGION = os.getenv("S3_REGION", "us-east-1")
_S3_ENDPOINT = os.getenv("S3_ENDPOINT_URL")          # None = use AWS
_PRESIGN_EXPIRY = int(os.getenv("S3_PRESIGN_EXPIRY", "3600"))

# ── Multipart transfer config ─────────────────────────────────
# Files > 8 MB use multipart; each part is 8 MB; max 10 concurrent threads.
# This ensures large video uploads are reliable and resumable.
_TRANSFER_CONFIG = TransferConfig(
    multipart_threshold=8 * 1024 * 1024,   # 8 MB
    multipart_chunksize=8 * 1024 * 1024,   # 8 MB per part
    max_concurrency=10,
    use_threads=True,
)


def _add_sentry_breadcrumb(message: str, data: dict, level: str = "error") -> None:
    """Add a Sentry breadcrumb for S3/FFmpeg failures if Sentry is configured."""
    if _SENTRY_AVAILABLE:
        sentry_sdk.add_breadcrumb(
            category="storage",
            message=message,
            data=data,
            level=level,
        )


def _client():
    return boto3.client(
        "s3",
        region_name=_S3_REGION,
        endpoint_url=_S3_ENDPOINT,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )


# ── Key builders ──────────────────────────────────────────────

def upload_key(user_id: str, file_id: str) -> str:
    return f"uploads/{user_id}/{file_id}.mp4"


def transcript_key(user_id: str, file_id: str) -> str:
    return f"outputs/{user_id}/{file_id}_transcription.json"


def clip_key(user_id: str, filename: str) -> str:
    return f"clips/{user_id}/{filename}"


def thumbnail_key(user_id: str, filename: str) -> str:
    return f"thumbnails/{user_id}/{filename}"


def meta_key(user_id: str, file_id: str, clip_n: int) -> str:
    return f"meta/{user_id}/{file_id}_clip_{clip_n}_meta.json"


# ── Upload ────────────────────────────────────────────────────

def upload_file(local_path: Path, s3_key: str, content_type: str = "application/octet-stream") -> str:
    """
    Upload a local file to S3 using multipart for files > 8 MB.
    Returns the s3_key.
    """
    if not _S3_BUCKET:
        raise RuntimeError("S3_BUCKET is not configured.")
    s3 = _client()
    try:
        s3.upload_file(
            str(local_path),
            _S3_BUCKET,
            s3_key,
            ExtraArgs={
                "ContentType": content_type,
                "ServerSideEncryption": "AES256",
            },
            Config=_TRANSFER_CONFIG,
        )
    except ClientError as exc:
        _add_sentry_breadcrumb(
            message="S3 upload_file failed",
            data={
                "s3_key": s3_key,
                "local_path": str(local_path),
                "bucket": _S3_BUCKET,
                "error": str(exc),
                "error_code": exc.response.get("Error", {}).get("Code", "unknown"),
            },
        )
        raise
    return s3_key


def upload_bytes(data: bytes, s3_key: str, content_type: str = "application/json") -> str:
    """Upload raw bytes to S3. Returns the s3_key."""
    if not _S3_BUCKET:
        raise RuntimeError("S3_BUCKET is not configured.")
    s3 = _client()
    s3.put_object(
        Bucket=_S3_BUCKET,
        Key=s3_key,
        Body=data,
        ContentType=content_type,
        ServerSideEncryption="AES256",
    )
    return s3_key


# ── Download ──────────────────────────────────────────────────

def download_file(s3_key: str, local_path: Path) -> None:
    """Download an S3 object to a local path using multipart for large files."""
    if not _S3_BUCKET:
        raise RuntimeError("S3_BUCKET is not configured.")
    local_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        _client().download_file(
            _S3_BUCKET,
            s3_key,
            str(local_path),
            Config=_TRANSFER_CONFIG,
        )
    except ClientError as exc:
        _add_sentry_breadcrumb(
            message="S3 download_file failed",
            data={
                "s3_key": s3_key,
                "local_path": str(local_path),
                "bucket": _S3_BUCKET,
                "error": str(exc),
                "error_code": exc.response.get("Error", {}).get("Code", "unknown"),
            },
        )
        raise


def get_presigned_download_url(s3_key: str, expiry: int = _PRESIGN_EXPIRY) -> str:
    """
    Generate a time-limited presigned GET URL.
    The file is never proxied through the API server — client downloads directly from S3/CDN.
    """
    if not _S3_BUCKET:
        raise RuntimeError("S3_BUCKET is not configured.")
    return _client().generate_presigned_url(
        "get_object",
        Params={"Bucket": _S3_BUCKET, "Key": s3_key},
        ExpiresIn=expiry,
    )


def get_presigned_upload_url(s3_key: str, content_type: str = "video/mp4", expiry: int = 900) -> str:
    """
    Generate a time-limited presigned PUT URL for direct browser → S3 upload.
    Avoids routing large files through the API server.
    """
    if not _S3_BUCKET:
        raise RuntimeError("S3_BUCKET is not configured.")
    return _client().generate_presigned_url(
        "put_object",
        Params={
            "Bucket": _S3_BUCKET,
            "Key": s3_key,
            "ContentType": content_type,
            "ServerSideEncryption": "AES256",
        },
        ExpiresIn=expiry,
    )


# ── Delete ────────────────────────────────────────────────────

def delete_object(s3_key: str) -> None:
    """Delete a single S3 object. Silently ignores NoSuchKey."""
    if not _S3_BUCKET:
        return
    try:
        _client().delete_object(Bucket=_S3_BUCKET, Key=s3_key)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code != "NoSuchKey":
            _add_sentry_breadcrumb(
                message="S3 delete_object failed",
                data={"s3_key": s3_key, "bucket": _S3_BUCKET, "error_code": code},
            )
            raise


def delete_prefix(prefix: str) -> int:
    """
    Delete all objects under a prefix (e.g. all files for a user).
    Returns count of deleted objects.
    Used by DELETE /account GDPR flow.
    """
    if not _S3_BUCKET:
        return 0
    s3 = _client()
    paginator = s3.get_paginator("list_objects_v2")
    deleted = 0
    for page in paginator.paginate(Bucket=_S3_BUCKET, Prefix=prefix):
        objects = page.get("Contents", [])
        if not objects:
            continue
        s3.delete_objects(
            Bucket=_S3_BUCKET,
            Delete={"Objects": [{"Key": obj["Key"]} for obj in objects]},
        )
        deleted += len(objects)
    return deleted


# ── Existence check ───────────────────────────────────────────

def object_exists(s3_key: str) -> bool:
    if not _S3_BUCKET:
        return False
    try:
        _client().head_object(Bucket=_S3_BUCKET, Key=s3_key)
        return True
    except ClientError:
        return False


# ── Fallback: local disk mode (when S3_BUCKET is empty) ──────

def is_s3_enabled() -> bool:
    return bool(_S3_BUCKET)
