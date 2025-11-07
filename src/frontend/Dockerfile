FROM node:18-alpine

WORKDIR /app

COPY src/frontend/package*.json ./

RUN npm install

COPY src/frontend/ ./

ENV REACT_APP_API_URL=http://backend:5001/api

EXPOSE 3000

CMD ["npm", "start"]
