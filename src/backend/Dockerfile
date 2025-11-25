FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from repository root and install Python dependencies
# Note: Build context should be repository root, use: docker build -f src/backend/Dockerfile .
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY src/backend/ .

# Set environment variables with defaults
ENV DATABASE_URL=sqlite:////app/data/invoice_app.db
ENV JWT_SECRET_KEY=change-this-in-production
ENV SECRET_KEY=change-this-in-production
ENV FLASK_ENV=production

# Create data directory for SQLite database
RUN mkdir -p /app/data

# Expose port 5001
EXPOSE 5001

# Run the application
CMD ["python3", "app.py"]
