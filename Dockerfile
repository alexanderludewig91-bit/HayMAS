# ============================================================================
# HayMAS - Multi-Stage Docker Build
# ============================================================================
# Stage 1: Frontend Build
# Stage 2: Python Backend + Built Frontend
# ============================================================================

# === Stage 1: Build Frontend ===
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Dependencies zuerst (für besseres Caching)
COPY frontend/package*.json ./
RUN npm ci

# Frontend bauen
COPY frontend/ ./
RUN npm run build


# === Stage 2: Python Backend + Frontend ===
FROM python:3.11-slim

WORKDIR /app

# System-Dependencies für WeasyPrint (PDF-Generierung)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Python Dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Backend Code
COPY agents/ ./agents/
COPY evidence_gated/ ./evidence_gated/
COPY mcp_server/ ./mcp_server/
COPY templates/ ./templates/
COPY logo/ ./logo/
COPY api.py config.py session_logger.py ./

# Built Frontend aus Stage 1
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Verzeichnisse für persistente Daten
RUN mkdir -p /app/data /app/output /app/logs

# Volumes für persistente Speicherung
VOLUME ["/app/data", "/app/output", "/app/logs"]

# Port
EXPOSE 8000

# Umgebungsvariablen
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/status')"

# Start: Backend serviert auch das Frontend
CMD ["python", "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8000"]
