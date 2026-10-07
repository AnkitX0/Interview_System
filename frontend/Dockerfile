# Stage 1: Build the React/Vite application
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies using package-lock
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy frontend source
COPY frontend/ ./

# Build arguments for browser API endpoint
ARG VITE_API_URL=http://localhost:8001
ENV VITE_API_URL=$VITE_API_URL

# Build production distribution
RUN npm run build

# Stage 2: Lightweight Nginx server
FROM nginx:alpine

# Copy built distribution files to Nginx webroot
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy Nginx SPA configuration
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
