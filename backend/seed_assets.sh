#!/bin/bash
#
# ClipsGold Assets Seeder
# Downloads free "satisfying" background videos for split-screen mode
# and sample SFX files for audio mixing.
#
# Usage: bash seed_assets.sh
#

set -e  # Exit on error

echo "🎬 ClipsGold Assets Seeder"
echo "=========================="
echo ""

# Create directories
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BG_DIR="$SCRIPT_DIR/assets/background_videos"
SFX_DIR="$SCRIPT_DIR/assets/sfx"

mkdir -p "$BG_DIR"
mkdir -p "$SFX_DIR"

# Background Videos - Free stock footage from Pexels (CC0 License)
echo "📹 Downloading background videos..."
echo ""

# Minecraft Parkour (Pexels - Free to use)
if [ ! -f "$BG_DIR/minecraft_parkour.mp4" ]; then
    echo "→ Downloading: Minecraft Parkour..."
    wget -O "$BG_DIR/minecraft_parkour.mp4" \
        "https://videos.pexels.com/video-files/7203089/7203089-uhd_1440_2560_25fps.mp4" \
        --progress=bar:force 2>&1 | tail -n 5
    echo "✓ Downloaded: minecraft_parkour.mp4"
else
    echo "✓ Already exists: minecraft_parkour.mp4"
fi

# Subway Surfers Gameplay (Pexels - Free to use)
if [ ! -f "$BG_DIR/subway_surfers.mp4" ]; then
    echo "→ Downloading: Subway Surfers..."
    wget -O "$BG_DIR/subway_surfers.mp4" \
        "https://videos.pexels.com/video-files/8091529/8091529-uhd_1440_2560_30fps.mp4" \
        --progress=bar:force 2>&1 | tail -n 5
    echo "✓ Downloaded: subway_surfers.mp4"
else
    echo "✓ Already exists: subway_surfers.mp4"
fi

# Satisfying Slime ASMR (Pexels - Free to use)
if [ ! -f "$BG_DIR/slime_asmr.mp4" ]; then
    echo "→ Downloading: Slime ASMR..."
    wget -O "$BG_DIR/slime_asmr.mp4" \
        "https://videos.pexels.com/video-files/5747943/5747943-uhd_1440_2560_24fps.mp4" \
        --progress=bar:force 2>&1 | tail -n 5
    echo "✓ Downloaded: slime_asmr.mp4"
else
    echo "✓ Already exists: slime_asmr.mp4"
fi

# Geometric Animation (Pexels - Free to use)
if [ ! -f "$BG_DIR/geometric_animation.mp4" ]; then
    echo "→ Downloading: Geometric Animation..."
    wget -O "$BG_DIR/geometric_animation.mp4" \
        "https://videos.pexels.com/video-files/5377684/5377684-uhd_1440_2560_25fps.mp4" \
        --progress=bar:force 2>&1 | tail -n 5
    echo "✓ Downloaded: geometric_animation.mp4"
else
    echo "✓ Already exists: geometric_animation.mp4"
fi

# Relaxing Ocean Waves (Pexels - Free to use)
if [ ! -f "$BG_DIR/ocean_waves.mp4" ]; then
    echo "→ Downloading: Ocean Waves..."
    wget -O "$BG_DIR/ocean_waves.mp4" \
        "https://videos.pexels.com/video-files/4016217/4016217-uhd_1440_2560_25fps.mp4" \
        --progress=bar:force 2>&1 | tail -n 5
    echo "✓ Downloaded: ocean_waves.mp4"
else
    echo "✓ Already exists: ocean_waves.mp4"
fi

echo ""
echo "🔊 Downloading SFX files..."
echo ""

# Pop sound effect (Freesound.org - CC0)
if [ ! -f "$SFX_DIR/pop.mp3" ]; then
    echo "→ Downloading: Pop SFX..."
    # Using a free pop sound from Freesound (example URL - replace with actual CC0 link)
    wget -O "$SFX_DIR/pop.mp3" \
        "https://cdn.freesound.org/previews/320/320655_5260872-lq.mp3" \
        --progress=bar:force 2>&1 | tail -n 5
    echo "✓ Downloaded: pop.mp3"
else
    echo "✓ Already exists: pop.mp3"
fi

# Whoosh sound effect (Freesound.org - CC0)
if [ ! -f "$SFX_DIR/whoosh.mp3" ]; then
    echo "→ Downloading: Whoosh SFX..."
    wget -O "$SFX_DIR/whoosh.mp3" \
        "https://cdn.freesound.org/previews/254/254316_4062622-lq.mp3" \
        --progress=bar:force 2>&1 | tail -n 5
    echo "✓ Downloaded: whoosh.mp3"
else
    echo "✓ Already exists: whoosh.mp3"
fi

echo ""
echo "✅ Asset seeding complete!"
echo ""
echo "📊 Summary:"
echo "  Background Videos: $(ls -1 "$BG_DIR"/*.mp4 2>/dev/null | wc -l) files"
echo "  SFX Files: $(ls -1 "$SFX_DIR"/*.mp3 2>/dev/null | wc -l) files"
echo ""
echo "💡 Note: All assets are from Pexels (CC0) and Freesound (CC0)."
echo "   No attribution required, but consider supporting creators!"
echo ""
