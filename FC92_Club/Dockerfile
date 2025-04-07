# Use Python 3.11 as the base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV DEBUG=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create static directories and collect static files
RUN mkdir -p staticfiles && \
    mkdir -p static && \
    mkdir -p media && \
    python manage.py collectstatic --noinput --clear

# Run migrations and start Gunicorn
CMD ["sh", "-c", "python manage.py migrate && gunicorn FC92_Club.wsgi:application --bind 0.0.0.0:8000"] 