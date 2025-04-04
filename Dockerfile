FROM python:3.13-slim

# Install FFmpeg and other system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .

# Upgrade pip first
RUN pip install --no-cache-dir --upgrade pip

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download Demucs models
RUN mkdir -p /cache && \
    TORCH_HOME=/cache python -c "from demucs.pretrained import get_model; get_model('htdemucs')"

# Create directories
RUN mkdir -p /media /output

# Copy application code
COPY salsa-milk.py .

# Environment variable to force immediate output
ENV PYTHONUNBUFFERED=1
ENV TORCH_HOME=/cache

# Set volumes for persistence
VOLUME ["/media", "/output", "/cache"]

# Set entrypoint
ENTRYPOINT ["python", "salsa-milk.py"]