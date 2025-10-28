# Use Python 3.11 slim image for a good balance of features and size
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# Clone the latest code from GitHub
RUN apt-get update && apt-get install -y git && \
    git clone --depth 1 -b dev https://github.com/harshitadutt267/scanner_engine.git /app/scanner_engine && \
    cd /app/scanner_engine && \
    git fetch --depth 1 origin dev && \
    git reset --hard origin/dev && \
    rm -rf /var/lib/apt/lists/*

# Set working directory to the cloned repo
WORKDIR /app/scanner_engine

# Create a non-root user for security
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port 8000
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the FastAPI application
CMD ["uvicorn", "scanner_api:app", "--host", "0.0.0.0", "--port", "8000"]