# --- Build UI (React + Vite) ---
FROM node:20-alpine AS build-ui
WORKDIR /app
# Copy workspace root package files
COPY package*.json ./
COPY tsconfig.json ./
# Copy UI package files
COPY ui/package*.json ./ui/
# Install all workspace dependencies
RUN npm install --no-fund --no-audit
# Copy UI source
COPY ui/ ./ui/
# Build UI
RUN npm run build:ui

# --- Build BFF (Express + TypeScript) ---
FROM node:20-alpine AS build-bff
WORKDIR /app
# Copy workspace root package files
COPY package*.json ./
# Copy BFF package files
COPY bff/package*.json ./bff/
# Install all workspace dependencies
RUN npm install --no-fund --no-audit
# Copy BFF source
COPY bff/ ./bff/
# Build BFF
RUN npm run build:bff

# --- Runtime (Nginx + Node.js) ---
FROM node:20-alpine AS runtime
# Install nginx
RUN apk add --no-cache nginx

# Copy built UI from build-ui stage
COPY --from=build-ui /app/ui/dist /usr/share/nginx/html

# Copy built BFF from build-bff stage
WORKDIR /app/bff
COPY --from=build-bff /app/bff/dist ./dist
COPY --from=build-bff /app/bff/package*.json ./
COPY --from=build-bff /app/node_modules ../node_modules

# Copy shared brand assets (logo, favicon) to stable path
COPY ./images /usr/share/nginx/html/images

# Copy nginx config
RUN rm -f /etc/nginx/conf.d/default.conf /etc/nginx/http.d/default.conf
COPY ./nginx.conf /etc/nginx/http.d/default.conf

# Create startup script to run both nginx and BFF
RUN printf '#!/bin/sh\n\
nginx\n\
cd /app/bff && NODE_ENV=production node dist/index.js\n' > /start.sh && \
chmod +x /start.sh

EXPOSE 80
CMD ["/start.sh"]
