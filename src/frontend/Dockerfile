# Frontend Dockerfile for React Invoice Application
FROM node:18-alpine

# Set working directory
WORKDIR /app

# Set environment variables
ENV NODE_ENV=development
# Backend API URL - will be overridden at runtime for container networking
ENV REACT_APP_API_URL=http://localhost:5001/api

# Copy package files and install dependencies
COPY package.json package-lock.json ./
RUN npm install

# Copy frontend source code
COPY . .

# Expose port 3000
EXPOSE 3000

# Start the React development server
CMD ["npm", "start"]
