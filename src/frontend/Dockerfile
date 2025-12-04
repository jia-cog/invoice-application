# Frontend Dockerfile for Invoice Application
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files and install dependencies
COPY package.json package-lock.json ./
RUN npm install

# Copy frontend source code
COPY . .

# Set environment variable for API URL (will be overridden by docker-compose)
ENV REACT_APP_API_URL=http://localhost:5001/api

# Expose port 3000
EXPOSE 3000

# Start the development server
CMD ["npm", "start"]
