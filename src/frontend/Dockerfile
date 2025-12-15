# Frontend Dockerfile for Invoice Application
# React development server

FROM node:18-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package.json package-lock.json ./

# Install dependencies
RUN npm install

# Copy frontend source code
COPY . .

# Set environment variable for API URL
# This will be overridden by docker-compose or ansible
ENV REACT_APP_API_URL=http://localhost:5001/api

# Expose port 3000
EXPOSE 3000

# Start the React development server
CMD ["npm", "start"]
