# Stage 1: Build production frontend assets
FROM node:22-alpine AS builder

WORKDIR /app

# Install dependencies using clean install
COPY package.json package-lock.json ./
RUN npm ci

# Copy frontend source files and build
COPY . .
RUN npm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Remove default nginx configurations
RUN rm -rf /etc/nginx/conf.d/*

# Copy custom nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy production build artifacts from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
