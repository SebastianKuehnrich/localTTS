FROM python:3.11-slim

# System-Dependencies fuer Audio-Processing
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dependencies zuerst kopieren (Docker Layer Caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Dann den Rest des Codes
COPY . .

# Port definieren
EXPOSE 8000

# Health Check im Container
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=60s \
    CMD curl -f http://localhost:8000/health || exit 1

# Starten (PORT-Variable fuer Railway-Kompatibilitaet)
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000}"]
