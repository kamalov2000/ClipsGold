# Background Videos for "Satisfying" Split-Screen

This directory contains background videos used for the **satisfying split-screen format**.

## Format Requirements

- **Resolution:** 1080x1080 (1:1 aspect ratio) or will be cropped to 1080x960
- **Duration:** Any (will be looped/trimmed to match clip duration)
- **Content:** Satisfying visuals (Minecraft parkour, subway surfers, ASMR, etc.)
- **Audio:** Will be muted automatically

## How It Works

When rendering in split-screen mode:
- **Top 50%:** Speaker (face-detected crop)
- **Bottom 50%:** Random background video from this folder
- **Subtitles:** Centered at MarginV=480 (border between videos)

## Example Background Videos

Popular satisfying content:
1. Minecraft parkour gameplay
2. Subway Surfers gameplay
3. Satisfying slime/ASMR
4. Kinetic sand cutting
5. Oddly satisfying compilations

## Usage

1. Add `.mp4` files to this directory
2. System will randomly select one per clip
3. Background video will loop if shorter than clip
4. Background video will be trimmed if longer than clip

## Fallback

If this directory is empty, the system will fallback to standard single-view crop mode.
