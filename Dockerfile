FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    build-essential \
    libjpeg-dev \
    zlib1g-dev \
    libfreetype6-dev \
    libwebp-dev \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers (no --with-deps, we already installed deps)
RUN playwright install chromium

COPY . .

ENV PYTHONUNBUFFERED=1
ENV VIDEO_OUTPUT_DIR=/app/output/videos
ENV MUSIC_DIR=/app/assets/music
ENV LOGO_PATH=/app/assets/logo.png

RUN mkdir -p output/videos assets/music

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Use shell form; fallback to 8000 if $PORT not set
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}