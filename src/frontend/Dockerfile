FROM node:18-alpine

WORKDIR /app

# Copy package files and install dependencies
# Note: Build context should be repository root, use: docker build -f src/frontend/Dockerfile .
COPY src/frontend/package.json src/frontend/package-lock.json ./
RUN npm install

# Copy frontend source code
COPY src/frontend/ .

# Set environment variable for API URL
# This will be overridden at runtime for container networking
ENV REACT_APP_API_URL=http://localhost:5001/api

# Expose port 3000
EXPOSE 3000

# Start the development server
CMD ["npm", "start"]
