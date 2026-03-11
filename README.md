# ClipsGold ✂️

An AI-powered viral clip detection system that uses OpenAI Whisper for transcription and GPT-4o/Gemini for intelligent content analysis. Automatically identifies the most viral-worthy 30-second segments from your videos.

## Features

### Core AI Features
- **🎤 AI Transcription**: Powered by OpenAI Whisper for accurate speech-to-text
- **🤖 Viral Clip Detection**: GPT-4o or Google Gemini analyzes content to find viral moments
- **✂️ Automatic Clip Extraction**: FFmpeg cuts video segments based on AI timestamps
- **📊 Virality Scoring**: Each clip rated 1-10 with detailed reasoning
- **⚡ Dual AI Support**: Choose between OpenAI GPT-4o or Google Gemini
- **📺 YouTube Support**: Download videos directly from YouTube (up to 1080p) with yt-dlp

### 🏆 Gold Features (Turn Clips into Gold!)
- **📱 Auto-Reframe (9:16)**: MediaPipe detects faces and automatically crops to vertical format
- **💬 Dynamic Subtitles**: High-contrast yellow/white subtitles burned into video with bold fonts
- **🔥 Attention Hooks**: AI-generated 3-5 word hooks displayed at the top of each clip
- **🎯 Social Media Ready**: Clips optimized for TikTok, Instagram Reels, YouTube Shorts

### UI & Experience
- **🎨 Modern UI**: Beautiful drag-and-drop interface with real-time processing status
- **📈 Enhancement Badges**: Visual indicators showing which features are applied
- **⚡ Fast Processing**: MediaPipe + FFmpeg for efficient video processing

## Prerequisites

- **Python 3.8+** for the backend
- **Node.js 18+** for the frontend
- **FFmpeg** installed and available in your system PATH
- **OpenAI API Key** or **Google Gemini API Key** for AI features (optional - mock mode available for testing)

### Installing FFmpeg

**Windows:**
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from https://ffmpeg.org/download.html
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
sudo apt update
sudo apt install ffmpeg
```

## Setup

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Create a virtual environment:
```bash
python -m venv venv
```

3. Activate the virtual environment:
```bash
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```
```bash
pip install -r requirements.txt
```

3. **(Optional)** Create a `.env` file with your API keys:
```bash
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
AI_PROVIDER=openai
```

**Note**: You can skip this step and use **Mock Mode** for testing without API keys. The app will generate random clips automatically.

4. Start the FastAPI server:
```bash
uvicorn main:app --reload
```

The backend will be available at `http://localhost:8000`

**Note**: On first run, Whisper will download the "base" model (~140MB). This happens automatically.

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Run the development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:3000`

## Usage

### AI-Powered Viral Clip Detection Workflow

1. **Start both servers** (backend and frontend)
2. **Open** `http://localhost:3000` in your browser
3. **Get your video**:
   - **Option A**: Paste a YouTube URL and click "Download" (auto-downloads best quality up to 1080p)
   - **Option B**: Upload your own MP4 file via drag-and-drop or file browser
4. **Select AI Provider**: 
   - **Mock** (default - no API keys needed, generates random clips for testing)
   - **OpenAI GPT-4o** (requires API key)
   - **Google Gemini** (requires API key)
5. **Transcribe**: Click "Transcribe" to extract audio and convert to text using Whisper
6. **Analyze**: Click "Analyze" to have AI identify the top 3 viral-worthy 30-second segments
   - In **Mock Mode**: Returns 3 hardcoded clips (0-30s, 30-60s, 60-90s) with random scores
   - In **AI Mode**: Uses GPT-4o/Gemini to analyze content and find viral moments
7. **Extract Gold Clips**: Click "Extract Clips" to create enhanced clips with:
   - **9:16 Auto-Reframe**: Face-centered vertical crop using MediaPipe
   - **Dynamic Subtitles**: Burned-in captions with high contrast
   - **Attention Hooks**: AI-generated hooks at the top of the video
8. **Download**: Download individual "Gold" clips ready for social media

### 🧪 Mock Mode (Testing Without API Keys)

Perfect for testing the video processing pipeline without AI API costs:

- **No API keys required** - works out of the box
- **Generates 3 random clips** based on video duration (0-30s, 30-60s, 60-90s)
- **Hardcoded titles and hooks** like "Epic Opening Hook", "Mind-Blowing Revelation"
- **Random virality scores** between 7-10
- **Full Gold features** - reframing, subtitles, and hooks all work normally
- **Great for development** - test the entire pipeline without API calls

To use Mock Mode, simply select "Mock" as the AI provider in the frontend (it's the default).

### What the AI Analyzes

The AI looks for:
- **Strong hooks** that grab attention immediately
- **Emotional peaks** (excitement, surprise, humor)
- **Surprising revelations** or plot twists
- **Actionable insights** or valuable information
- **Memorable moments** with high shareability

Each clip receives:
- A **virality score** (1-10)
- A **catchy title**
- A **3-5 word hook** (e.g., "WAIT FOR IT", "THIS CHANGED EVERYTHING")
- **Detailed reasoning** for why it's viral-worthy
- **Precise timestamps** for extraction

### Gold Enhancement Details

**Auto-Reframe (9:16)**:
- Uses MediaPipe to detect speaker's face in each frame
- Calculates optimal crop coordinates to keep face centered
- Converts landscape videos to vertical format perfect for mobile

**Dynamic Subtitles** (Word-Level Highlighting):
- **Word-by-word highlighting**: Each word changes color exactly when spoken
- **Color transition**: White → Yellow with 120% scale pop-up animation
- **Precise timing**: Uses Whisper's word-level timestamps for perfect sync
- **High-contrast styling**: Bold Arial Black font with black outline
- **Smart grouping**: Groups words into readable 8-word lines
- **ASS format**: Advanced SubStation Alpha for complex animations

**Attention Hooks**:
- AI generates short, punchy hooks (3-5 words max)
- Displayed at top of video throughout the clip
- Creates curiosity and urgency
- Examples: "WATCH THIS", "MIND = BLOWN", "THE SECRET REVEALED"

## API Endpoints

### Core Endpoints

**`GET /`**
- Health check endpoint that returns FFmpeg availability status

**`POST /upload`**
- Upload an MP4 file
- **Body**: `multipart/form-data` with `file` field
- **Returns**: `file_id`, `filename`, `size`, `message`

**`POST /download-youtube`**
- Download video from YouTube URL
- **Body**: `{"url": "https://youtube.com/watch?v=..."}`
- **Returns**: `file_id`, `filename`, `title`, `duration`, `size`, `message`
- **Format**: Best quality up to 1080p, automatically merged to MP4

### AI-Powered Endpoints

**`POST /transcribe/{file_id}`**
- Transcribe video audio using OpenAI Whisper
- **Returns**: Full transcription text, language, and timestamped segments

**`POST /analyze/{file_id}?provider=mock`**
- Analyze transcription to find viral clips using GPT-4o, Gemini, or Mock
- **Query Parameters**: `provider` (mock, openai, or gemini) - defaults to `mock`
- **Returns**: Array of 3 viral clips with scores, titles, timestamps, hooks, and reasoning
- **Mock Mode**: Returns hardcoded clips without API calls (perfect for testing)

**`POST /extract-clips/{file_id}`**
- Extract viral clips using FFmpeg based on AI analysis
- **Returns**: Array of extracted clip metadata with download info

**`GET /download-clip/{file_id}/{clip_id}`**
- Download a specific extracted clip
- **Returns**: MP4 file download

### Legacy Endpoints

**`POST /process/{file_id}?operation=info|thumbnail|compress`**
- Basic video processing operations
- **Returns**: Processing result or output file path

**`GET /download/{file_id}?file_type=thumbnail|compressed`**
- Download processed file
- **Returns**: File download

**`DELETE /cleanup/{file_id}`**
- Delete all files associated with a file_id
- **Returns**: List of deleted files

## Project Structure

```
ClipsGold/
├── backend/
│   ├── main.py                  # FastAPI application with all endpoints
│   ├── analyzer.py              # AI service for viral clip detection + hook generation
│   ├── reframer.py              # MediaPipe face detection & 9:16 cropping
│   ├── subtitle_generator.py   # ASS subtitle generation from Whisper transcripts
│   ├── requirements.txt         # Python dependencies
│   ├── .env.example            # Environment variables template
│   ├── uploads/                # Uploaded videos (created at runtime)
│   ├── outputs/                # Transcriptions, subtitles, analysis (created at runtime)
│   └── clips/                  # Extracted Gold clips (created at runtime)
├── frontend/
│   ├── app/
│   │   ├── globals.css         # Global styles
│   │   ├── layout.tsx          # Root layout
│   │   └── page.tsx            # Home page
│   ├── components/
│   │   ├── VideoUploader.tsx      # Upload component
│   │   ├── VideoProcessor.tsx     # Basic processing (legacy)
│   │   └── AIVideoProcessor.tsx   # AI-powered Gold clip creation
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── next.config.js
└── README.md
```

## Technologies Used

### Backend
- **FastAPI**: Modern Python web framework
- **OpenAI Whisper**: State-of-the-art speech recognition
- **OpenAI GPT-4o**: Advanced language model for content analysis + hook generation
- **Google Gemini**: Alternative AI provider for analysis
- **yt-dlp**: YouTube video downloader (best quality up to 1080p)
- **MediaPipe**: Google's ML solution for face detection
- **OpenCV**: Computer vision for video frame processing
- **FFmpeg**: Professional video processing with subtitle burning
- **PyTorch**: Deep learning framework for Whisper
- **Uvicorn**: ASGI server

### Frontend
- **Next.js 14**: React framework with App Router
- **TypeScript**: Type-safe JavaScript
- **TailwindCSS**: Utility-first CSS framework
- **Lucide React**: Beautiful icon library
- **Axios**: HTTP client

## How It Works

### Standard Workflow
1. **Video Acquisition**:
   - **YouTube**: yt-dlp downloads video (best quality ≤1080p, merged to MP4)
   - **Upload**: Direct MP4 file upload stored with unique ID
2. **Audio Extraction**: FFmpeg extracts audio as WAV (16kHz mono)
3. **Transcription**: Whisper converts audio to text with timestamps
4. **AI Analysis**: GPT-4o/Gemini analyzes the transcription to identify:
   - Emotional peaks and hooks
   - Surprising or valuable moments
   - Optimal 30-second segments
   - Generates attention-grabbing hooks for each clip

### Gold Enhancement Pipeline
5. **Face Detection**: MediaPipe scans video frames to locate speaker's face
6. **Crop Calculation**: Determines optimal 9:16 crop coordinates to center face
7. **Subtitle Generation**: Converts Whisper word-level timestamps to ASS format with:
   - Hook text at the top (permanent, white)
   - Word-level captions at the bottom with:
     - Each word highlighted yellow when spoken
     - 120% scale pop-up animation on current word
     - Smooth color transitions (white → yellow → white)
     - Precise millisecond-level timing
   - High-contrast styling with black outline for readability
8. **Enhanced Extraction**: FFmpeg applies:
   - Crop filter for 9:16 aspect ratio
   - Subtitle burning with custom styling
   - Re-encoding with H.264 (fast preset, CRF 23)
9. **Download**: Gold clips ready for TikTok, Reels, Shorts

## Performance Notes

- **YouTube download**: Speed depends on video size and internet connection (~30s for 5-min 1080p video)
- **Whisper "base" model**: ~140MB, good balance of speed and accuracy
- **Transcription speed**: ~2-5x real-time with word timestamps (5-min video = 1-2 min)
- **Word-level timestamps**: Adds ~10-20% to transcription time
- **AI analysis**: 5-15 seconds depending on transcript length
- **Hook generation**: ~1-2 seconds per clip
- **Face detection**: ~5-10 seconds per 30-second clip (samples every 30 frames)
- **Subtitle generation**: Near-instant (word-level ASS creation)
- **Gold clip creation**: ~10-20 seconds per clip (with reframe + word-level subs)
- **Basic clip extraction**: Near-instant with `-c copy` (no re-encoding)
- **First run**: Whisper model downloads automatically (~140MB)

## Cost Estimates (OpenAI)

- **Whisper API**: $0.006/minute of audio (if using API instead of local)
- **GPT-4o**: ~$0.01-0.05 per video analysis (depends on transcript length)
- **Local Whisper**: Free (uses your GPU/CPU)

## Notes

- The backend creates `uploads/`, `outputs/`, and `clips/` directories automatically
- Files are stored with UUID-based names to prevent conflicts
- **YouTube downloads**: yt-dlp automatically selects best quality up to 1080p
- **Supported platforms**: YouTube, YouTube Music, and 1000+ other sites via yt-dlp
- CORS is configured to allow requests from `http://localhost:3000`
- Whisper runs locally by default (no API calls needed for transcription)
- Choose between OpenAI and Gemini based on your API access and preferences
- Gold clips are named with `_gold.mp4` suffix to distinguish from basic clips
- MediaPipe samples every 30 frames for face detection (balance of accuracy and speed)
- **Word-level subtitles**: Each word gets precise timing from Whisper's word_timestamps
- **ASS animations**: Uses `\t()` tags for color transitions and `\fscx/\fscy` for scaling
- **Karaoke-style effect**: Words light up yellow with 20% size increase when spoken
- Reframing ensures faces stay centered even with camera movement
- Gold clips are re-encoded (H.264, CRF 23) due to filters; basic clips use `-c copy`
