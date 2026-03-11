# ClipsGold AI Factory Guide 🏭 - AUTONOMOUS MODE

## ✨ NEW: Fully Autonomous AI Factory

ClipsGold теперь может работать **полностью автономно** - от поиска трендовых видео до загрузки готовых клипов на YouTube!

### 🚀 Что нового (10 автономных компонентов)

1. **Trend Scout Service** - Автоматический поиск популярных видео по нишам
2. **Autonomous Scheduler** - Запуск pipeline по расписанию (9:00, 15:00, 21:00)
3. **Smart Filtering** - Автоматический рендер только клипов с viral_score ≥ 8
4. **Niche Configuration** - YAML конфиг для управления тематиками
5. **YouTube Auto-Uploader** - Загрузка готовых клипов на YouTube Shorts
6. **Telegram Notifications** - Уведомления о готовых видео
7. **Deduplication Logic** - Защита от повторной обработки
8. **Auto Thumbnail Selection** - Выбор лучшего кадра по face confidence
9. **Factory Dashboard** - Мониторинг статуса в реальном времени
10. **Headless Mode** - Полностью автономная работа без UI

---

## 🚀 Overview

ClipsGold has been transformed from a manual video cutter into an **autonomous AI factory** that:
- **Discovers viral moments** automatically using GPT-4o
- **Creates semantic subtitles** with intelligent phrase grouping
- **Maintains existing features** (face detection, 2-pass rendering, WebSocket progress)

---

## 📋 Table of Contents

1. [Architecture](#architecture)
2. [Phase 1: Viral Moment Discovery](#phase-1-viral-moment-discovery)
3. [Phase 2: Semantic Subtitle Chunking](#phase-2-semantic-subtitle-chunking)
4. [Phase 3: Frontend Integration](#phase-3-frontend-integration)
5. [API Reference](#api-reference)
6. [Usage Guide](#usage-guide)
7. [Configuration](#configuration)

---

## 🏗️ Architecture

### New Components

```
backend/
├── services/
│   └── viral_scout.py          # GPT-4o viral moment detection
├── main.py                      # New /analyze-video endpoint
└── subtitle_generator_v2.py     # Semantic chunking support

frontend/
└── components/
    └── ViralSuggestions.tsx     # Viral moment UI component
```

### Data Flow

```
1. Upload Video → Transcribe (Whisper)
2. Click "Discover Viral Moments" → GPT-4o analyzes transcript
3. AI returns 3-5 high-impact segments with viral scores
4. Generate thumbnails + face detection for each moment
5. User reviews viral moments (or renders directly)
6. Render with semantic subtitles (GPT-4o phrase grouping)
7. Download finished clips
```

---

## 🎯 Phase 1: Viral Moment Discovery

### Backend Service: `viral_scout.py`

**Function:** `discover_viral_moments(transcription_data, min_segments=3, max_segments=5)`

**What it does:**
- Sends full transcript with timestamps to GPT-4o
- AI identifies 3-5 segments with viral potential (15-60 seconds each)
- Returns segments with:
  - `start_time` / `end_time`
  - `title` (catchy 3-5 word title)
  - `viral_score` (1-10 rating)
  - `hook` (explanation of viral potential)

**GPT-4o Prompt Strategy:**
```
CRITERIA FOR VIRAL MOMENTS:
1. Emotional Hooks: Controversy, shock, humor, inspiration
2. Standalone Value: Makes sense without prior context
3. Optimal Length: 15-60 seconds
4. Peak Moments: Climax, punchline, revelation, strong opinion
5. Cultural Relevance: Trending topics, memes, universal experiences

AVOIDS:
- Setup without payoff
- Transitions or filler
- Segments requiring extensive context
```

**Example Response:**
```json
[
  {
    "start_time": 45.2,
    "end_time": 62.8,
    "title": "Woke Culture Rant",
    "viral_score": 9,
    "hook": "Controversial opinion on modern politics with strong emotional delivery",
    "duration": 17.6
  }
]
```

### API Endpoint: `POST /analyze-video`

**Request:**
```bash
POST http://localhost:8000/analyze-video?file_id=<uuid>
```

**Response:**
```json
{
  "viral_moments": [
    {
      "start_time": 45.2,
      "end_time": 62.8,
      "title": "Woke Culture Rant",
      "viral_score": 9,
      "hook": "Controversial opinion...",
      "duration": 17.6,
      "clip_index": 0,
      "thumbnail_url": "/thumbnails/...",
      "crop_preview": { "crop_x": 640, "mode": "single_face" }
    }
  ],
  "count": 5,
  "message": "AI discovered 5 viral moments"
}
```

**Error Handling:**
- Returns 404 if video or transcription not found
- Returns 500 if OPENAI_API_KEY not set
- Falls back gracefully if AI fails

---

## 📝 Phase 2: Semantic Subtitle Chunking

### Backend Service: `viral_scout.py`

**Function:** `get_semantic_subtitle_chunks(segment_text, segment_words, preserve_timing=True)`

**What it does:**
- Replaces fixed 3-word chunking with AI-powered semantic grouping
- GPT-4o groups words into 1-5 word phrases based on:
  - Complete thoughts
  - Natural pauses
  - Speech rhythm
  - Preserves brands/names in English (South Park, Woke, POV)

**Traditional Chunking (OLD):**
```
"I think South Park is the best show"
→ ["I think South", "Park is the", "best show"]
❌ Breaks "South Park" brand name
```

**Semantic Chunking (NEW):**
```
"I think South Park is the best show"
→ ["I think", "South Park", "is the best show"]
✅ Preserves brand, natural pauses
```

### Subtitle Generator Integration

**File:** `subtitle_generator_v2.py`

**New Parameter:** `use_semantic_chunking=True`

```python
# Create generator with semantic chunking (default)
generator = create_subtitle_generator(use_semantic_chunking=True)

# Disable for traditional 3-word chunks
generator = create_subtitle_generator(use_semantic_chunking=False)
```

**Fallback Logic:**
- If GPT-4o fails → falls back to traditional 3-word chunking
- If OPENAI_API_KEY not set → uses traditional chunking
- Logs warning but never crashes

**Performance:**
- Adds ~1-2 seconds per segment for AI processing
- Caches results within same render job
- Async execution prevents blocking

---

## 🎨 Phase 3: Frontend Integration

### Component: `ViralSuggestions.tsx`

**Location:** `frontend/components/ViralSuggestions.tsx`

**Features:**
- **Discover Button:** Triggers autonomous AI analysis
- **Viral Moment Cards:** Shows title, score, hook, thumbnail
- **Score Visualization:** Color-coded badges (red=9-10, orange=7-8, yellow=5-6)
- **Time Display:** Shows start/end times and duration
- **Auto-Integration:** Discovered moments populate candidate list

**UI Elements:**
```tsx
<ViralSuggestions 
  fileId={fileId} 
  onMomentsDiscovered={handleViralMomentsDiscovered}
/>
```

**Visual Design:**
- Gradient purple/blue background
- Sparkles icon for AI branding
- Fire emoji (🔥) for score 9-10
- Lightning emoji (⚡) for score 7-8
- Hover effects on cards

### Integration with AIVideoProcessor

**File:** `frontend/components/AIVideoProcessor.tsx`

**Changes:**
1. Import ViralSuggestions component
2. Add `handleViralMomentsDiscovered` callback
3. Place component after transcription section
4. Viral moments populate existing candidate system
5. Seamless integration with render pipeline

**Workflow:**
```
1. User uploads video
2. Clicks "Transcribe"
3. Clicks "Discover Viral Moments" (new button)
4. AI analyzes → shows 3-5 viral moment cards
5. Moments appear in "Clip Candidates" section
6. User clicks "Render Clip" on any moment
7. Semantic subtitles applied automatically
8. Download finished clip
```

---

## 📚 API Reference

### Endpoints

#### `POST /analyze-video`
Autonomous viral moment discovery using GPT-4o.

**Query Parameters:**
- `file_id` (required): UUID of uploaded video

**Response:**
```json
{
  "viral_moments": [ViralMoment],
  "count": number,
  "message": string
}
```

#### `POST /transcribe/{file_id}` (existing)
Transcribe video using Whisper.

#### `POST /render-clip` (existing)
Render clip with semantic subtitles (automatic if enabled).

---

## 🎮 Usage Guide

### Quick Start

1. **Upload Video:**
   ```bash
   POST /upload
   # Upload your MP4 file
   ```

2. **Transcribe:**
   ```bash
   POST /transcribe/{file_id}
   # Whisper generates transcript with word-level timing
   ```

3. **Discover Viral Moments (NEW):**
   ```bash
   POST /analyze-video?file_id={file_id}
   # GPT-4o analyzes and returns 3-5 viral segments
   ```

4. **Review & Render:**
   - Frontend shows viral moment cards
   - Click "Render Clip" on any moment
   - Semantic subtitles applied automatically

5. **Download:**
   ```bash
   GET /download-clip/{file_id}/{clip_id}
   ```

### Manual Analysis (Legacy)

Still available for custom workflows:

```bash
POST /analyze/{file_id}?provider=openai
# Uses existing analyzer.py logic
```

---

## ⚙️ Configuration

### Environment Variables

**Required:**
```bash
OPENAI_API_KEY=sk-...
```

**Optional:**
```bash
# Disable semantic chunking (use traditional 3-word chunks)
USE_SEMANTIC_CHUNKING=false
```

### Semantic Chunking Toggle

**In Code:**
```python
# Enable semantic chunking (default)
generator = create_subtitle_generator(use_semantic_chunking=True)

# Disable for faster rendering (no AI calls)
generator = create_subtitle_generator(use_semantic_chunking=False)
```

### GPT-4o Model Settings

**File:** `services/viral_scout.py`

```python
# Viral moment discovery
model="gpt-4o"
temperature=0.7  # Higher for creative discovery
max_tokens=2048

# Semantic chunking
model="gpt-4o"
temperature=0.3  # Lower for consistent grouping
max_tokens=1024
```

---

## 🔧 Technical Details

### Viral Moment Validation

**Duration Check:**
- Minimum: 15 seconds
- Maximum: 60 seconds
- Rejects segments outside this range

**Score Normalization:**
- Clamps scores to 1-10 range
- Sorts by viral_score (highest first)

**JSON Parsing:**
- Strips markdown code blocks
- Validates required fields
- Graceful error handling

### Semantic Chunking Algorithm

**Input:**
```python
segment_text = "I think South Park is the best show"
segment_words = [
  {"word": "I", "start": 0.0, "end": 0.2},
  {"word": "think", "start": 0.2, "end": 0.5},
  # ... word-level timing from Whisper
]
```

**GPT-4o Prompt:**
```
Group these words into semantic chunks for subtitles.
Each chunk should be 1-5 words and represent a complete thought.

RULES:
- Keep brands/names in English (South Park, Woke, POV)
- Natural speech rhythm (pause at commas, periods)
- 1-5 words per chunk maximum
- Return JSON array: [{"words": [0, 1, 2]}, {"words": [3, 4]}, ...]

Words (index:text):
0:I, 1:think, 2:South, 3:Park, 4:is, 5:the, 6:best, 7:show
```

**Output:**
```json
[
  {"words": [0, 1]},      // "I think"
  {"words": [2, 3]},      // "South Park"
  {"words": [4, 5, 6, 7]} // "is the best show"
]
```

**Timing Mapping:**
- Maps word indices back to Whisper timestamps
- Preserves exact start/end times
- Generates ASS subtitle file with semantic chunks

---

## 🎯 Key Features

### ✅ Autonomous Discovery
- No manual timestamp selection
- AI identifies peak moments automatically
- Emotional hook detection

### ✅ Semantic Subtitles
- Natural phrase grouping
- Preserves brand names (South Park, Woke)
- Respects speech rhythm

### ✅ Viral Score System
- 1-10 rating for each moment
- Color-coded UI (red/orange/yellow)
- Sorted by viral potential

### ✅ Graceful Fallbacks
- Traditional chunking if AI fails
- Center crop if face detection fails
- Never crashes on AI errors

### ✅ Existing Features Preserved
- 2-pass FFmpeg rendering
- Face detection + smart crop
- Split-screen mode
- WebSocket progress tracking
- Manual crop override

---

## 🚨 Troubleshooting

### "No viral moments discovered"
- Check `OPENAI_API_KEY` is set
- Verify transcript has content
- Check API quota/rate limits

### "Semantic chunking failed"
- Falls back to traditional 3-word chunks
- Check logs for specific error
- Verify OpenAI API is accessible

### Slow rendering
- Semantic chunking adds 1-2s per segment
- Disable with `use_semantic_chunking=False`
- Check network latency to OpenAI

---

## 📊 Performance Metrics

**Viral Moment Discovery:**
- Analysis time: 5-15 seconds (depends on transcript length)
- API calls: 1 per video
- Cost: ~$0.01-0.05 per video (GPT-4o pricing)

**Semantic Chunking:**
- Processing time: 1-2 seconds per segment
- API calls: 1 per segment (typically 5-10 segments per clip)
- Cost: ~$0.001-0.005 per segment

**Total Workflow:**
- Upload: instant
- Transcribe: 30-60 seconds (Whisper)
- Discover: 5-15 seconds (GPT-4o)
- Render: 20-40 seconds per clip (FFmpeg + semantic chunking)

---

## 🎓 Best Practices

1. **Always transcribe first** - Viral discovery requires transcript
2. **Review viral scores** - Higher scores = better viral potential
3. **Use semantic chunking** - Better subtitle readability
4. **Check thumbnails** - Verify face detection worked
5. **Test different platforms** - TikTok/YouTube/Instagram have different safe zones

---

## 🔮 Future Enhancements

- [ ] Batch rendering of all viral moments
- [ ] Custom viral criteria (humor only, controversy only, etc.)
- [ ] A/B testing different subtitle styles
- [ ] Auto-upload to social platforms
- [ ] Viral score prediction model training
- [ ] Multi-language support for semantic chunking

---

## 📝 License & Credits

**ClipsGold AI Factory**
- Built with GPT-4o (OpenAI)
- Whisper for transcription
- MediaPipe for face detection
- FFmpeg for video processing

**Author:** ClipsGold Team
**Version:** 2.0 (AI Factory Edition)
**Last Updated:** February 2026
