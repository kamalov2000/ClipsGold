"""
YouTube Auto-Uploader Service - Upload rendered clips to YouTube Shorts.
Uses Google API Python Client for OAuth2 authentication and video upload.
"""

import os
import pickle
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from services.observability import get_logger

log = get_logger(__name__)

# YouTube API scopes
SCOPES = ['https://www.googleapis.com/auth/youtube.upload']

# Token storage path
TOKEN_PATH = Path(__file__).parent.parent / "youtube_token.pickle"
CREDENTIALS_PATH = Path(__file__).parent.parent / "youtube_credentials.json"


def get_youtube_service():
    """
    Authenticate and return YouTube API service.
    Uses OAuth2 flow with token caching.
    """
    creds = None
    
    # Load cached token if exists
    if TOKEN_PATH.exists():
        with open(TOKEN_PATH, 'rb') as token:
            creds = pickle.load(token)
    
    # Refresh or get new credentials
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            log.info("Refreshing YouTube API credentials...")
            creds.refresh(Request())
        else:
            if not CREDENTIALS_PATH.exists():
                log.error("YouTube credentials.json not found!")
                log.error("Download from Google Cloud Console: https://console.cloud.google.com/apis/credentials")
                return None
            
            log.info("Starting OAuth2 flow for YouTube API...")
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open(TOKEN_PATH, 'wb') as token:
            pickle.dump(creds, token)
        log.info("YouTube credentials saved")
    
    return build('youtube', 'v3', credentials=creds)


def upload_video_to_youtube(
    video_path: Path,
    title: str,
    description: str,
    tags: list,
    category_id: str = "22",  # People & Blogs
    privacy_status: str = "private",  # private, unlisted, public
    is_shorts: bool = True,
) -> Optional[Dict]:
    """
    Upload video to YouTube.
    
    Args:
        video_path: Path to video file
        title: Video title (max 100 chars)
        description: Video description (max 5000 chars)
        tags: List of tags (max 500 chars total)
        category_id: YouTube category ID
        privacy_status: private, unlisted, or public
        is_shorts: Whether this is a YouTube Short
    
    Returns:
        Dict with video_id and url, or None if failed
    """
    if not video_path.exists():
        log.error(f"Video file not found: {video_path}")
        return None
    
    try:
        youtube = get_youtube_service()
        if not youtube:
            log.error("Failed to get YouTube service")
            return None
        
        # Prepare video metadata
        body = {
            'snippet': {
                'title': title[:100],  # YouTube limit
                'description': description[:5000],  # YouTube limit
                'tags': tags[:50],  # Max 50 tags
                'categoryId': category_id,
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False,
            }
        }
        
        # Add #Shorts tag if it's a Short
        if is_shorts and '#Shorts' not in body['snippet']['description']:
            body['snippet']['description'] += '\n\n#Shorts'
        
        # Upload video
        log.info(f"📤 Uploading to YouTube: {title[:50]}...")
        
        media = MediaFileUpload(
            str(video_path),
            chunksize=-1,  # Upload in single request
            resumable=True,
            mimetype='video/mp4'
        )
        
        request = youtube.videos().insert(
            part='snippet,status',
            body=body,
            media_body=media
        )
        
        response = request.execute()
        
        video_id = response.get('id')
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        log.info(f"✅ Uploaded to YouTube: {video_url}")
        log.info(f"   Privacy: {privacy_status}")
        
        return {
            'video_id': video_id,
            'url': video_url,
            'privacy_status': privacy_status,
            'uploaded_at': datetime.utcnow().isoformat(),
        }
    
    except HttpError as e:
        log.error(f"YouTube API error: {e}")
        return None
    except Exception as e:
        log.error(f"Upload failed: {e}")
        return None


def update_video_privacy(video_id: str, privacy_status: str) -> bool:
    """
    Update video privacy status (e.g., from private to public).
    
    Args:
        video_id: YouTube video ID
        privacy_status: private, unlisted, or public
    
    Returns:
        True if successful
    """
    try:
        youtube = get_youtube_service()
        if not youtube:
            return False
        
        youtube.videos().update(
            part='status',
            body={
                'id': video_id,
                'status': {
                    'privacyStatus': privacy_status
                }
            }
        ).execute()
        
        log.info(f"✅ Updated video {video_id} privacy to {privacy_status}")
        return True
    
    except Exception as e:
        log.error(f"Failed to update privacy: {e}")
        return False


def delete_video(video_id: str) -> bool:
    """
    Delete video from YouTube.
    
    Args:
        video_id: YouTube video ID
    
    Returns:
        True if successful
    """
    try:
        youtube = get_youtube_service()
        if not youtube:
            return False
        
        youtube.videos().delete(id=video_id).execute()
        log.info(f"🗑 Deleted video {video_id}")
        return True
    
    except Exception as e:
        log.error(f"Failed to delete video: {e}")
        return False


def get_video_stats(video_id: str) -> Optional[Dict]:
    """
    Get video statistics (views, likes, comments).
    
    Args:
        video_id: YouTube video ID
    
    Returns:
        Dict with stats or None
    """
    try:
        youtube = get_youtube_service()
        if not youtube:
            return None
        
        response = youtube.videos().list(
            part='statistics,status',
            id=video_id
        ).execute()
        
        if not response.get('items'):
            return None
        
        item = response['items'][0]
        stats = item.get('statistics', {})
        status = item.get('status', {})
        
        return {
            'view_count': int(stats.get('viewCount', 0)),
            'like_count': int(stats.get('likeCount', 0)),
            'comment_count': int(stats.get('commentCount', 0)),
            'privacy_status': status.get('privacyStatus', 'unknown'),
        }
    
    except Exception as e:
        log.error(f"Failed to get video stats: {e}")
        return None
