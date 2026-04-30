"""
SQLAlchemy ORM models — PostgreSQL schema for ClipsGold SaaS.

Tables:
  organizations        — multi-tenant orgs (optional, for team plans)
  users                — auth + plan + quota tracking
  videos               — uploaded/imported video sources
  transcripts          — Whisper output per video (versioned)
  transcription_jobs   — async Whisper jobs (progress, transcript_id)
  clip_candidates      — AI-discovered viral moments per video
  render_jobs          — FFmpeg render tasks with status/progress
  usage_events         — billing ledger: every expensive action logged here
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, JSON, Enum as SAEnum,
    UniqueConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ─────────────────────────────────────────────────────────────
# Enums
# ─────────────────────────────────────────────────────────────

class UserPlan(str, enum.Enum):
    free = "free"
    pro = "pro"
    team = "team"


class VideoStatus(str, enum.Enum):
    pending = "pending"
    transcribing = "transcribing"
    transcribed = "transcribed"
    analyzing = "analyzing"
    analyzed = "analyzed"
    error = "error"


class RenderStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    complete = "complete"
    error = "error"
    cancelled = "cancelled"


class UsageEventType(str, enum.Enum):
    whisper_minutes = "whisper_minutes"
    gpt_tokens = "gpt_tokens"
    render_seconds = "render_seconds"
    storage_mb = "storage_mb"
    export = "export"


class TranscriptionJobStatus(str, enum.Enum):
    processing = "processing"
    done = "done"
    failed = "failed"


# ─────────────────────────────────────────────────────────────
# Organizations (multi-tenant, optional)
# ─────────────────────────────────────────────────────────────

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    plan = Column(SAEnum(UserPlan), nullable=False, default=UserPlan.free)
    stripe_customer_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    users = relationship("User", back_populates="organization")


# ─────────────────────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    email = Column(String(320), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)

    plan = Column(SAEnum(UserPlan), nullable=False, default=UserPlan.free)
    organization_id = Column(UUID(as_uuid=False), ForeignKey("organizations.id"), nullable=True)
    stripe_customer_id = Column(String(255), nullable=True)

    # Quota counters (reset monthly by billing cycle)
    renders_this_month = Column(Integer, default=0, nullable=False)
    whisper_minutes_this_month = Column(Float, default=0.0, nullable=False)
    storage_bytes_used = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    organization = relationship("Organization", back_populates="users")
    videos = relationship("Video", back_populates="owner", cascade="all, delete-orphan")
    render_jobs = relationship("RenderJob", back_populates="owner", cascade="all, delete-orphan")
    usage_events = relationship("UsageEvent", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_users_email_active", "email", "is_active"),
    )


# ─────────────────────────────────────────────────────────────
# Refresh tokens (revocable)
# ─────────────────────────────────────────────────────────────

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=_now, nullable=False)

    user = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("ix_refresh_tokens_hash", "token_hash"),
    )


# ─────────────────────────────────────────────────────────────
# Videos (uploaded or imported)
# ─────────────────────────────────────────────────────────────

class Video(Base):
    __tablename__ = "videos"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    file_id = Column(String(36), unique=True, nullable=False, index=True)  # legacy UUID key
    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    original_filename = Column(String(500), nullable=True)
    source_url = Column(Text, nullable=True)           # YouTube URL if imported
    s3_key = Column(String(1000), nullable=True)       # e.g. uploads/{owner_id}/{file_id}.mp4
    s3_bucket = Column(String(255), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    status = Column(SAEnum(VideoStatus), nullable=False, default=VideoStatus.pending)
    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    owner = relationship("User", back_populates="videos")
    transcript = relationship("Transcript", back_populates="video", uselist=False, cascade="all, delete-orphan")
    clip_candidates = relationship("ClipCandidate", back_populates="video", cascade="all, delete-orphan")
    render_jobs = relationship("RenderJob", back_populates="video", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_videos_owner_created", "owner_id", "created_at"),
    )


# ─────────────────────────────────────────────────────────────
# Transcripts
# ─────────────────────────────────────────────────────────────

class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    video_id = Column(UUID(as_uuid=False), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, unique=True)

    raw_text = Column(Text, nullable=True)
    refined_text = Column(Text, nullable=True)
    segments_json = Column(JSON, nullable=True)    # full Whisper segments with word timestamps
    language = Column(String(10), nullable=True)
    whisper_model = Column(String(50), nullable=True)
    duration_seconds = Column(Float, nullable=True)

    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    video = relationship("Video", back_populates="transcript")


# ─────────────────────────────────────────────────────────────
# Async transcription jobs (progress + result pointer)
# ─────────────────────────────────────────────────────────────


class TranscriptionJob(Base):
    __tablename__ = "transcription_jobs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    file_id = Column(String(36), nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    status = Column(
        SAEnum(TranscriptionJobStatus, values_callable=lambda x: [e.value for e in x], native_enum=False),
        nullable=False,
        default=TranscriptionJobStatus.processing,
    )
    progress = Column(Integer, nullable=False, default=0)
    total_chunks = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    transcript_id = Column(String(36), nullable=True)
    skipped_chunks_json = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    __table_args__ = (Index("ix_transcription_jobs_file_owner", "file_id", "owner_id"),)


# ─────────────────────────────────────────────────────────────
# Clip Candidates (AI-discovered viral moments)
# ─────────────────────────────────────────────────────────────

class ClipCandidate(Base):
    __tablename__ = "clip_candidates"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    video_id = Column(UUID(as_uuid=False), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)

    clip_index = Column(Integer, nullable=False)   # 0-based position in analysis result
    title = Column(String(500), nullable=True)
    hook = Column(String(500), nullable=True)
    reason = Column(Text, nullable=True)
    virality_score = Column(Float, nullable=True)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    emojis = Column(JSON, nullable=True)           # list of emoji strings
    hashtags = Column(JSON, nullable=True)
    crop_preview = Column(JSON, nullable=True)     # face detection crop data
    thumbnail_s3_key = Column(String(1000), nullable=True)

    created_at = Column(DateTime, default=_now, nullable=False)

    video = relationship("Video", back_populates="clip_candidates")
    render_jobs = relationship("RenderJob", back_populates="candidate", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("video_id", "clip_index", name="uq_candidate_video_index"),
        Index("ix_candidates_video", "video_id"),
    )


# ─────────────────────────────────────────────────────────────
# Render Jobs
# ─────────────────────────────────────────────────────────────

class RenderJob(Base):
    __tablename__ = "render_jobs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    task_id = Column(String(36), unique=True, nullable=False, index=True)  # Celery task ID / WS key
    owner_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    video_id = Column(UUID(as_uuid=False), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False)
    candidate_id = Column(UUID(as_uuid=False), ForeignKey("clip_candidates.id", ondelete="SET NULL"), nullable=True)

    platform = Column(String(50), nullable=True)
    subtitle_style = Column(String(50), default="hormozi", nullable=False)
    show_hook = Column(Boolean, default=True, nullable=False)
    enable_jump_cut = Column(Boolean, default=False, nullable=False)
    enable_sfx = Column(Boolean, default=True, nullable=False)
    manual_crop_x = Column(Integer, nullable=True)

    status = Column(SAEnum(RenderStatus), nullable=False, default=RenderStatus.queued)
    progress = Column(Integer, default=0, nullable=False)   # 0–100
    error_message = Column(Text, nullable=True)

    output_s3_key = Column(String(1000), nullable=True)
    output_filename = Column(String(500), nullable=True)
    output_size_bytes = Column(Integer, nullable=True)
    render_seconds = Column(Float, nullable=True)           # wall-clock time for billing

    social_meta = Column(JSON, nullable=True)               # GPT-generated title/desc/hashtags/cta

    created_at = Column(DateTime, default=_now, nullable=False)
    updated_at = Column(DateTime, default=_now, onupdate=_now, nullable=False)

    owner = relationship("User", back_populates="render_jobs")
    video = relationship("Video", back_populates="render_jobs")
    candidate = relationship("ClipCandidate", back_populates="render_jobs")

    __table_args__ = (
        Index("ix_render_jobs_owner_status", "owner_id", "status"),
    )


# ─────────────────────────────────────────────────────────────
# Usage Events (billing ledger)
# ─────────────────────────────────────────────────────────────

class UsageEvent(Base):
    __tablename__ = "usage_events"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    job_id = Column(UUID(as_uuid=False), ForeignKey("render_jobs.id", ondelete="SET NULL"), nullable=True)

    event_type = Column(SAEnum(UsageEventType), nullable=False)
    units = Column(Float, nullable=False)                   # minutes / tokens / seconds / MB
    cost_usd = Column(Float, nullable=True)                 # computed cost at time of event
    event_meta = Column(JSON, nullable=True)                 # extra context (model, file_id, etc.)

    created_at = Column(DateTime, default=_now, nullable=False)

    user = relationship("User", back_populates="usage_events")

    __table_args__ = (
        Index("ix_usage_events_user_type", "user_id", "event_type"),
        Index("ix_usage_events_created", "created_at"),
    )


# ─────────────────────────────────────────────────────────────
# Discovery Queue (Autonomous Factory)
# ─────────────────────────────────────────────────────────────

class DiscoveryStatus(str, enum.Enum):
    pending = "pending"
    downloading = "downloading"
    downloaded = "downloaded"
    transcribing = "transcribing"
    analyzing = "analyzing"
    rendering = "rendering"
    complete = "complete"
    failed = "failed"
    skipped = "skipped"


class DiscoveryQueue(Base):
    __tablename__ = "discovery_queue"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    youtube_url = Column(Text, nullable=False)
    youtube_video_id = Column(String(20), unique=True, nullable=False, index=True)
    
    niche = Column(String(100), nullable=True)
    search_query = Column(String(500), nullable=True)
    view_count = Column(Integer, nullable=True)
    like_count = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    status = Column(SAEnum(DiscoveryStatus), nullable=False, default=DiscoveryStatus.pending)
    file_id = Column(String(36), nullable=True)  # Links to Video after download
    error_message = Column(Text, nullable=True)
    
    discovered_at = Column(DateTime, default=_now, nullable=False)
    processed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index("ix_discovery_status", "status"),
        Index("ix_discovery_niche", "niche"),
    )


# ─────────────────────────────────────────────────────────────
# Processed Videos (Deduplication)
# ─────────────────────────────────────────────────────────────

class ProcessedVideo(Base):
    __tablename__ = "processed_videos"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    youtube_video_id = Column(String(20), unique=True, nullable=False, index=True)
    youtube_url = Column(Text, nullable=False)
    
    file_id = Column(String(36), nullable=True)
    niche = Column(String(100), nullable=True)
    clips_generated = Column(Integer, default=0, nullable=False)
    clips_uploaded = Column(Integer, default=0, nullable=False)
    
    processed_at = Column(DateTime, default=_now, nullable=False)
    
    __table_args__ = (
        Index("ix_processed_videos_niche", "niche"),
    )
