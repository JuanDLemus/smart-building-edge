FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DB_PATH="/app/data/building.db" \
    OCCUPANCY_MODEL_PATH="/app/occupancy_model.pkl"

WORKDIR /app

# Install system dependencies if required
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

# Create data directory for persistent SQLite database
RUN mkdir -p /app/data

# INIT DB SCHEMA ONLY — model already trained and copied via COPY . .
RUN python init_db.py /app/data/building.db

EXPOSE 5000

CMD ["python", "app.py"]
