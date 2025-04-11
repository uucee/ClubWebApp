# Use Python 3.11 as the base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

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

# Create staticfiles directory
RUN mkdir -p staticfiles

# Collect static files
RUN python manage.py collectstatic --noinput

# Expose the port Gunicorn will run on
EXPOSE 8000

# Run migrations (consider running migrations as a separate step/job)
# and start Gunicorn
CMD ["sh", "-c", "python manage.py migrate && gunicorn FC92_Club.wsgi:application --bind 0.0.0.0:8000"]

# Run migrations and start the application (initial code commented out)
#CMD ["sh", "-c", "python manage.py migrate && python manage.py runserver 0.0.0.0:8000"] 