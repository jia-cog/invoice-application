# Backend Dockerfile for Invoice Application
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from repository root and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY src/backend/ .

# Create directory for SQLite database
RUN mkdir -p /app/instance

# Set default environment variables for production
ENV DATABASE_URL=sqlite:////app/instance/invoice_app.db
ENV JWT_SECRET_KEY=change-this-in-production
ENV SECRET_KEY=change-this-in-production

# Expose port 5001
EXPOSE 5001

# Set entry point to run the Flask application
CMD ["python3", "app.py"]
