# syntax=docker/dockerfile:1
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# ffmpeg merges the audio and video streams when countdown videos are downloaded
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 app
WORKDIR /app

# Dependencies first, so code changes don't reinstall them
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src ./src

# Writable folders for logs and data (data is mounted from the host at runtime)
RUN mkdir -p logs data/results data/videos \
    && chown -R app:app /app
USER app

# Every setting comes from environment variables (CLIENT_ID, CLIENT_SECRET, SECRET_KEY, REDIRECT_URI, ...),
# so nothing secret is baked into the image.
ENV PORT=8888
EXPOSE 8888

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/' % os.environ.get('PORT', '8000'), timeout=3)"]

# One worker, many threads: search and download jobs are held in memory, so they must share a process
CMD ["sh", "-c", "exec gunicorn -k gthread -w 1 --threads 8 -t 120 -b 0.0.0.0:${PORT} src.web.app:app"]
