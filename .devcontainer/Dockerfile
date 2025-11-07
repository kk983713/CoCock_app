# Dev container for CoCock_app (Python 3.11)
FROM mcr.microsoft.com/devcontainers/python:1-3.11-bookworm

# Install system packages for OCR/PDF/image handling
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        poppler-utils \
        libgl1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /tmp/pip-tmp/
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r /tmp/pip-tmp/requirements.txt \
    && rm -rf /tmp/pip-tmp
