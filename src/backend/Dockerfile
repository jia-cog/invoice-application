# Backend Dockerfile for Flask Invoice Application
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Default environment variables for production
ENV DATABASE_URL=sqlite:////data/invoice_app.db
ENV JWT_SECRET_KEY=change-this-secret-key-in-production
ENV SECRET_KEY=change-this-secret-key-in-production

# Copy requirements from repository root and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY src/backend/ .

# Expose port 5001
EXPOSE 5001

# Run the Flask application
CMD ["python3", "app.py"]
