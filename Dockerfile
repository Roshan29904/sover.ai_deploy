FROM python:3.12-slim

# Prevent Python from creating .pyc files
ENV PYTHONDONTWRITEBYTECODE=1

# Show Python output immediately
ENV PYTHONUNBUFFERED=1

# Application directory
WORKDIR /app

# Copy requirements first
# This allows Docker to cache dependency installation
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# FastAPI port
EXPOSE 8000

CMD ["sh", "-c", "uvicorn fast_api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]