# ========= API (Flask) =========
FROM python:3.11-slim AS api
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# dipendenze di sistema minime
RUN apt-get update && apt-get install -y --no-install-recommends build-essential && \
    rm -rf /var/lib/apt/lists/*

# installa requirements
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt && \
    pip install --no-cache-dir gunicorn

# copia il backend (app.py + functions.py)
COPY content/backend/ /app/

# crea dir per il volume
RUN mkdir -p /app/uploads
ENV UPLOADS_DIR=/app/uploads

EXPOSE 5000
# avvia gunicorn e tieni il processo in foreground
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]

# ========= UI (Next.js) =========
FROM node:20-alpine AS ui
WORKDIR /ui

# args/vars per build Next
ARG NEXT_PUBLIC_API_URL=http://localhost:5003
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
# usato solo lato server nel container (fetch interno)
ENV INTERNAL_API_URL=http://whatif_api:5000
ENV PORT=3000
ENV NEXT_TELEMETRY_DISABLED=1

# install deps
COPY content/package*.json ./
RUN npm ci

# copia sorgenti e build
COPY content/ ./
# se usi ts: assicurati esista next-env.d.ts nella root di "content/"
RUN npm run build

EXPOSE 3000
CMD ["npm", "start"]
