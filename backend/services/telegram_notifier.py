"""
Telegram Notification Service - Send alerts when videos are ready.
Uses Telegram Bot API to send messages with download links and metadata.
"""

import os
import requests
from typing import Optional, Dict
from pathlib import Path
from services.observability import get_logger

log = get_logger(__name__)


def get_telegram_config() -> Dict[str, str]:
    """Get Telegram bot configuration from environment."""
    return {
        'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
        'chat_id': os.getenv('TELEGRAM_CHAT_ID', ''),
    }


def send_telegram_message(
    message: str,
    parse_mode: str = 'Markdown',
    disable_web_page_preview: bool = False
) -> bool:
    """
    Send message to Telegram chat.
    
    Args:
        message: Message text (supports Markdown or HTML)
        parse_mode: 'Markdown' or 'HTML'
        disable_web_page_preview: Disable link previews
    
    Returns:
        True if sent successfully
    """
    config = get_telegram_config()
    bot_token = config['bot_token']
    chat_id = config['chat_id']
    
    if not bot_token or not chat_id:
        log.warning("Telegram credentials not configured - skipping notification")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': parse_mode,
        'disable_web_page_preview': disable_web_page_preview,
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        log.info("✅ Telegram notification sent")
        return True
    except Exception as e:
        log.error(f"Failed to send Telegram message: {e}")
        return False


def send_video_ready_notification(
    title: str,
    download_url: str,
    viral_score: float,
    hashtags: list,
    duration: float,
    file_size_mb: float,
    niche: Optional[str] = None,
    clip_filename: Optional[str] = None
) -> bool:
    """
    Send notification when video is ready for upload.
    
    Args:
        title: Video title
        download_url: URL to download the clip
        viral_score: AI virality score (1-10)
        hashtags: List of hashtags
        duration: Video duration in seconds
        file_size_mb: File size in MB
        niche: Content niche
        clip_filename: Filename of rendered clip
    
    Returns:
        True if sent successfully
    """
    # Format hashtags (plain text, no markdown issues)
    hashtag_str = ' '.join([f'#{tag}' for tag in hashtags[:5]])
    
    # Build message (no markdown to avoid parsing errors)
    message = f"""VIDEO READY!

Title: {title}

Viral Score: {viral_score}/10
Duration: {duration:.1f}s
Size: {file_size_mb:.1f} MB
"""
    
    if niche:
        message += f"Niche: {niche}\n"
    
    message += f"\nHashtags:\n{hashtag_str}\n"
    message += f"\nDOWNLOAD VIDEO:\n{download_url}\n"
    
    if clip_filename:
        message += f"\nFilename: {clip_filename}\n"
    
    message += f"\nReady to upload to YouTube Shorts / TikTok / Instagram Reels"
    
    return send_telegram_message(message, parse_mode=None)


def send_batch_complete_notification(
    total_videos: int,
    total_clips: int,
    uploaded_clips: int,
    failed_clips: int,
    niche: Optional[str] = None
) -> bool:
    """
    Send notification when batch processing is complete.
    
    Args:
        total_videos: Number of videos processed
        total_clips: Total clips generated
        uploaded_clips: Clips uploaded to YouTube
        failed_clips: Failed clips
        niche: Content niche
    
    Returns:
        True if sent successfully
    """
    message = f"""
🏭 *Factory Batch Complete!*

📊 *Stats:*
• Videos Processed: {total_videos}
• Clips Generated: {total_clips}
• Uploaded to YouTube: {uploaded_clips}
• Failed: {failed_clips}
"""
    
    if niche:
        message += f"\n🎯 *Niche:* {niche}"
    
    success_rate = (uploaded_clips / total_clips * 100) if total_clips > 0 else 0
    message += f"\n\n✅ Success Rate: {success_rate:.1f}%"
    
    return send_telegram_message(message)


def send_error_notification(
    error_type: str,
    error_message: str,
    video_id: Optional[str] = None,
    file_id: Optional[str] = None
) -> bool:
    """
    Send error notification.
    
    Args:
        error_type: Type of error (download, transcribe, render, upload)
        error_message: Error details
        video_id: YouTube video ID
        file_id: Internal file ID
    
    Returns:
        True if sent successfully
    """
    message = f"""
❌ *Factory Error*

🔴 *Type:* {error_type}
📝 *Message:* {error_message}
"""
    
    if video_id:
        message += f"\n🎥 *Video ID:* {video_id}"
    if file_id:
        message += f"\n📁 *File ID:* {file_id}"
    
    return send_telegram_message(message)


def send_daily_report(
    videos_discovered: int,
    videos_processed: int,
    clips_generated: int,
    clips_uploaded: int,
    top_viral_score: float,
    niches: Dict[str, int]
) -> bool:
    """
    Send daily summary report.
    
    Args:
        videos_discovered: Videos found by trend scout
        videos_processed: Videos fully processed
        clips_generated: Total clips created
        clips_uploaded: Clips uploaded to platforms
        top_viral_score: Highest viral score achieved
        niches: Dict of {niche: clip_count}
    
    Returns:
        True if sent successfully
    """
    niche_breakdown = '\n'.join([f"  • {niche}: {count} clips" for niche, count in niches.items()])
    
    message = f"""
📊 *Daily Factory Report*

🔍 *Discovery:*
• Videos Found: {videos_discovered}
• Videos Processed: {videos_processed}

🎬 *Production:*
• Clips Generated: {clips_generated}
• Clips Uploaded: {clips_uploaded}

⭐ *Quality:*
• Top Viral Score: {top_viral_score}/10

🎯 *Niche Breakdown:*
{niche_breakdown}

🏭 Factory Status: ✅ Operational
"""
    
    return send_telegram_message(message)


def send_video_file(
    video_path: str,
    caption: str = "",
    thumbnail_path: Optional[str] = None
) -> bool:
    """
    Send video file directly to Telegram chat.
    Best for mobile access - user can watch/download immediately.
    
    Args:
        video_path: Path to video file
        caption: Video caption/description
        thumbnail_path: Optional thumbnail image path
    
    Returns:
        True if sent successfully
    """
    from pathlib import Path
    
    config = get_telegram_config()
    bot_token = config['bot_token']
    chat_id = config['chat_id']
    
    if not bot_token or not chat_id:
        log.warning("Telegram credentials not configured")
        return False
    
    video_file = Path(video_path)
    if not video_file.exists():
        log.error(f"Video file not found: {video_path}")
        return False
    
    # Check file size (Telegram limit: 50MB for bots)
    file_size_mb = video_file.stat().st_size / 1024 / 1024
    if file_size_mb > 50:
        log.warning(f"Video too large for Telegram ({file_size_mb:.1f}MB > 50MB limit)")
        return False
    
    url = f"https://api.telegram.org/bot{bot_token}/sendVideo"
    
    try:
        with open(video_file, 'rb') as video:
            files = {'video': video}
            data = {
                'chat_id': chat_id,
                'caption': caption[:1024] if caption else "",  # Telegram caption limit
                'supports_streaming': True
            }
            
            # Add thumbnail if provided
            if thumbnail_path and Path(thumbnail_path).exists():
                with open(thumbnail_path, 'rb') as thumb:
                    files['thumb'] = thumb
                    response = requests.post(url, data=data, files=files, timeout=60)
            else:
                response = requests.post(url, data=data, files=files, timeout=60)
        
        response.raise_for_status()
        
        if response.json().get('ok'):
            log.info(f"Video sent to Telegram: {video_file.name}")
            return True
        else:
            log.error(f"Telegram API error: {response.json()}")
            return False
            
    except Exception as e:
        log.error(f"Failed to send video to Telegram: {e}")
        return False


def send_test_notification() -> bool:
    """Send test notification to verify Telegram setup."""
    message = """
Test Notification

Telegram integration is working!

Your ClipsGold AI Factory is ready to send notifications.
"""
    return send_telegram_message(message, parse_mode=None)
