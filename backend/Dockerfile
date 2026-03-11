FROM python:3.12-slim

# System dependencies: ffmpeg for video processing, libgl1 for MediaPipe/OpenCV, fonts
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    wget \
    unzip \
    fontconfig \
    fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

# Install Montserrat and Impact fonts
RUN mkdir -p /usr/share/fonts/truetype/custom && \
    # Download Montserrat from Google Fonts
    wget -O /tmp/montserrat.zip https://fonts.google.com/download?family=Montserrat && \
    unzip -o /tmp/montserrat.zip -d /usr/share/fonts/truetype/custom/montserrat && \
    rm /tmp/montserrat.zip && \
    # Impact is available in MS Core Fonts
    apt-get update && apt-get install -y --no-install-recommends \
    ttf-mscorefonts-installer \
    && rm -rf /var/lib/apt/lists/* && \
    # Refresh font cache
    fc-cache -f -v

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create required directories
RUN mkdir -p uploads outputs clips thumbnails assets/background_videos assets/sfx assets/models

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
