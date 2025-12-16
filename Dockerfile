# ============================================================================
# PHASE 1: Base Image Selection
# We use 'slim' to keep the image small (security & performance)
# ============================================================================
FROM python:3.11-slim

# ============================================================================
# PHASE 2: Environment Configuration
# PYTHONDONTWRITEBYTECODE: Prevents Python from writing .pyc files (useless in containers)
# PYTHONUNBUFFERED: Forces logs to stdout immediately (critical for Docker logging)
# ============================================================================
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# ============================================================================
# PHASE 3: System Dependencies
# We combine apt-get update and install in one RUN command.
# Why? Docker layers. If we separate them, Docker might cache an old 'update'
# layer and fail to find new packages in the 'install' layer.
# We also clean up apt lists immediately to reduce image size.
# ============================================================================
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    tesseract-ocr \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# ============================================================================
# PHASE 4: Python Dependencies
# We copy requirements.txt ALONE first.
# Why? Docker caches layers. If you change your code but not your requirements,
# Docker will skip this step and reuse the installed packages, making builds instant.
# ============================================================================
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# ============================================================================
# PHASE 5: Application Code
# Now we copy the actual code. This layer changes frequently.
# ============================================================================
COPY . .

# ============================================================================
# PHASE 6: Security (Non-Root User)
# Running as root is a security risk. If a hacker breaks out of the app,
# they would have root access to the container. We create a limited user 'appuser'.
# ============================================================================
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port 8000 for the internal network
EXPOSE 8000

# Start the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]