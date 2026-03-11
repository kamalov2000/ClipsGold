# Autonomous Factory Setup Guide 🏭

## Quick Start

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

New dependencies added:
- `apscheduler>=3.10.4` - Job scheduling
- `pyyaml>=6.0.1` - Config file parsing
- `google-api-python-client>=2.100.0` - YouTube API
- `google-auth-oauthlib>=1.1.0` - OAuth2 authentication

### 2. Configure Environment Variables

Add to `.env`:

```bash
# Autonomous Factory
AUTONOMOUS_MODE=False  # Set to True for headless mode
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
YOUTUBE_AUTO_UPLOAD=False
YOUTUBE_DEFAULT_PRIVACY=private
```

### 3. Configure Niches

Edit `niche_config.yaml` to customize your content niches:

```yaml
niches:
  - name: "podcasts"
    enabled: true
    search_queries:
      - "podcast highlights"
      - "best podcast moments"
    min_duration: 600
    max_duration: 7200
    min_views: 10000
    viral_score_threshold: 8
```

### 4. Setup Telegram Bot (Optional)

1. Create bot with [@BotFather](https://t.me/botfather)
2. Get bot token
3. Get your chat ID from [@userinfobot](https://t.me/userinfobot)
4. Add to `.env`

### 5. Setup YouTube Auto-Upload (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create OAuth 2.0 Client ID
3. Download credentials as `youtube_credentials.json`
4. Place in `backend/` directory
5. First run will open browser for OAuth consent

### 6. Run Database Migrations

```bash
# Create new tables for autonomous factory
alembic revision --autogenerate -m "Add autonomous factory tables"
alembic upgrade head
```

Or for SQLite (dev):
```python
from db.session import create_tables
create_tables()  # Auto-creates all tables
```

---

## Usage Modes

### Mode 1: Manual Control (Default)

```bash
# Start backend normally
uvicorn main:app --reload

# Use API endpoints manually:
# POST /factory/run-scout - Discover videos
# GET /factory/discoveries - View queue
# GET /factory/stats - View statistics
```

### Mode 2: Scheduled Automation

```python
# In main.py startup event
from services.autonomous_scheduler import start_autonomous_scheduler

start_autonomous_scheduler(
    download_func=download_video,
    transcribe_func=transcribe_video,
    analyze_func=analyze_video,
    render_func=render_clip
)
```

Schedule:
- **6:00 AM** - Trend Scout discovers new videos
- **9:00 AM, 3:00 PM, 9:00 PM** - Factory processes queue
- **11:00 PM** - Daily report sent to Telegram

### Mode 3: Headless Mode

Set in `.env`:
```bash
AUTONOMOUS_MODE=True
```

In this mode:
- ✅ Scheduler runs automatically on startup
- ✅ Manual API endpoints disabled (factory only)
- ✅ All processing happens autonomously
- ✅ Telegram notifications for all events

---

## API Endpoints

### Factory Management

**GET `/factory/discoveries`**
- Get discovery queue items
- Query params: `limit`, `status`, `niche`

**GET `/factory/stats`**
- Overall factory statistics
- Returns: discovered, processed, clips, niches

**GET `/factory/scheduler-status`**
- Current scheduler status
- Returns: running status, job list with next run times

**POST `/factory/run-scout`**
- Manually trigger trend scout
- Returns: stats by niche

**GET `/factory/pending`**
- Get pending videos in queue
- Query param: `limit`

**GET `/factory/processed`**
- Get processed videos
- Query params: `limit`, `niche`

**GET `/factory/daily-report`**
- Get last 24h statistics

**POST `/factory/test-telegram`**
- Send test Telegram notification

---

## Architecture

### Database Models

**DiscoveryQueue**
- Stores discovered videos awaiting processing
- Fields: youtube_url, niche, status, view_count, etc.
- Status flow: pending → downloading → transcribing → analyzing → rendering → complete

**ProcessedVideo**
- Deduplication database
- Prevents reprocessing same video
- Tracks clips generated and uploaded

### Services

**auto_scout.py**
- `run_trend_scout()` - Main discovery function
- `search_youtube_videos()` - yt-dlp search
- `discover_videos_for_niche()` - Per-niche discovery
- `mark_video_processed()` - Deduplication

**autonomous_scheduler.py**
- `start_autonomous_scheduler()` - Initialize APScheduler
- `run_factory_cycle()` - Process pending queue
- `run_trend_scout_job()` - Scheduled discovery
- `run_daily_report_job()` - Daily stats

**youtube_uploader.py**
- `upload_video_to_youtube()` - Upload to YouTube Shorts
- `update_video_privacy()` - Change privacy status
- `get_video_stats()` - Fetch view/like counts

**telegram_notifier.py**
- `send_video_ready_notification()` - Clip ready alert
- `send_batch_complete_notification()` - Batch summary
- `send_daily_report()` - Daily stats
- `send_error_notification()` - Error alerts

### Frontend

**FactoryDashboard.tsx**
- Real-time factory status monitoring
- Discovery queue visualization
- Stats cards (discovered, processed, clips, pending)
- Scheduler status display
- Niche breakdown
- Auto-refresh every 10 seconds

---

## Smart Filtering

Only clips with `viral_score >= threshold` are rendered:

```yaml
# In niche_config.yaml
settings:
  auto_render_threshold: 8  # Only render 8+ scores
```

This ensures:
- ✅ High-quality output only
- ✅ Reduced rendering costs
- ✅ Better conversion rates
- ✅ Less manual review needed

---

## Deduplication

System maintains `processed_videos` table:

```python
# Before downloading
if is_video_processed(db, video_id):
    skip_video()

# After successful processing
mark_video_processed(db, video_id, file_id, niche, clips_count)
```

Prevents:
- ❌ Duplicate downloads
- ❌ Wasted API calls
- ❌ Storage bloat
- ❌ Redundant processing

---

## Automatic Thumbnail Selection

For autonomous mode, system selects best frame:

```python
from thumbnail_generator import select_best_thumbnail_frame

thumbnail_path, best_time, confidence = select_best_thumbnail_frame(
    video_path=video_path,
    start_time=clip_start,
    end_time=clip_end,
    sample_count=10
)
```

Algorithm:
1. Sample 10 frames evenly across clip
2. Run MediaPipe face detection on each
3. Select frame with highest confidence
4. Use for thumbnail + social media preview

---

## Monitoring & Alerts

### Telegram Notifications

**Video Ready:**
```
🎬 Video Ready for Upload!
📝 Title: Amazing Podcast Moment
⭐ Viral Score: 9.2/10
📊 Duration: 28.5s
💾 Size: 12.3 MB
🎯 Niche: podcasts
🏷 Hashtags: #podcast #viral #shorts
📥 Download: http://localhost:8000/download-clip/...
```

**Batch Complete:**
```
🏭 Factory Batch Complete!
📊 Stats:
• Videos Processed: 5
• Clips Generated: 12
• Uploaded to YouTube: 8
• Failed: 1
🎯 Niche: podcasts
✅ Success Rate: 92.3%
```

**Daily Report:**
```
📊 Daily Factory Report
🔍 Discovery: 15 videos found, 12 processed
🎬 Production: 28 clips generated, 22 uploaded
⭐ Quality: Top viral score 9.5/10
🎯 Niche Breakdown:
  • podcasts: 12 clips
  • tech_review: 8 clips
  • standup: 8 clips
```

### Dashboard Metrics

Access at `http://localhost:3000/factory`:

- **Total Discovered** - Videos found by trend scout
- **Total Processed** - Videos fully processed
- **Clips Generated** - Total clips created
- **In Queue** - Pending videos
- **Scheduler Status** - Running/Stopped + next run times
- **Niche Breakdown** - Clips per niche
- **Discovery Queue Table** - Real-time status

---

## Troubleshooting

### Scheduler not starting

Check logs:
```python
from services.autonomous_scheduler import get_scheduler_status
status = get_scheduler_status()
print(status)
```

### Telegram not working

Test notification:
```bash
curl -X POST http://localhost:8000/factory/test-telegram
```

Check `.env`:
- `TELEGRAM_BOT_TOKEN` set correctly
- `TELEGRAM_CHAT_ID` is your personal chat ID (not bot username)

### YouTube upload fails

1. Check `youtube_credentials.json` exists
2. Run OAuth flow: `python -c "from services.youtube_uploader import get_youtube_service; get_youtube_service()"`
3. Approve in browser
4. Token saved to `youtube_token.pickle`

### No videos discovered

Check `niche_config.yaml`:
- `enabled: true` for niches
- `min_views` not too high
- `search_queries` are valid

Test manually:
```bash
curl -X POST http://localhost:8000/factory/run-scout
```

### Videos stuck in queue

Check discovery status:
```bash
curl http://localhost:8000/factory/discoveries?limit=50
```

Look for `error_message` field.

Common issues:
- Download failed (bad URL, geo-restricted)
- Transcription timeout (video too long)
- No viral clips found (score < threshold)

---

## Performance

### Expected Throughput

- **Discovery:** 15-20 videos/day (configurable)
- **Processing:** 5-10 videos/cycle (3 cycles/day)
- **Rendering:** 2-3 clips/video (viral_score ≥ 8)
- **Total Output:** ~30-60 clips/day

### Resource Usage

- **CPU:** Moderate (Whisper + MediaPipe)
- **RAM:** ~4-8 GB (depends on video length)
- **Storage:** ~500 MB/video (temp files cleaned)
- **API Costs:**
  - Whisper: $0.006/min
  - GPT-4o: ~$0.02/video
  - YouTube API: Free (quota: 10,000 units/day)

### Optimization Tips

1. **Reduce viral threshold** - More clips, lower quality
2. **Increase min_views** - Higher quality sources
3. **Limit niches** - Focus on best performers
4. **Adjust schedule** - More/less frequent cycles
5. **Enable caching** - Reuse transcriptions

---

## Security

### API Keys

Store in `.env`, never commit:
- ✅ `OPENAI_API_KEY`
- ✅ `TELEGRAM_BOT_TOKEN`
- ✅ `youtube_credentials.json`

### Rate Limiting

Built-in protection:
- YouTube API: 10,000 units/day quota
- OpenAI: Tier-based limits
- yt-dlp: Respects robots.txt

### Data Privacy

- Videos stored temporarily (auto-cleanup after 24h)
- Transcripts cached in database
- No user data collected in autonomous mode

---

## Next Steps

1. **Test manually** - Run scout, check queue
2. **Enable scheduler** - Start autonomous mode
3. **Monitor dashboard** - Watch first batch
4. **Tune config** - Adjust niches/thresholds
5. **Enable uploads** - Connect YouTube
6. **Scale up** - Add more niches

Happy automating! 🚀
