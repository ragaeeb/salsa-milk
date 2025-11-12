FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1 \
    TORCH_HOME=/cache \
    PORT=8000

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /cache && \
    TORCH_HOME=/cache python -c "from demucs.pretrained import get_model; get_model('htdemucs')"

COPY . .

RUN mkdir -p /media /output

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "webapp:app"]
