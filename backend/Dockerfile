FROM python:3.12-slim

# Prevent Python from writing .pyc files and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# Install system dependencies:
# - poppler-utils: required for resume PDF extraction (pdftotext, pdfinfo)
# - curl: required for Docker healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# Copy application files
COPY alembic.ini /app/alembic.ini
COPY alembic/ /app/alembic/
COPY backend/ /app/backend/
COPY scripts/ /app/scripts/

# Ensure entrypoint script is executable
RUN chmod +x /app/backend/docker-entrypoint.sh

EXPOSE 8001

ENTRYPOINT ["/app/backend/docker-entrypoint.sh"]
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
