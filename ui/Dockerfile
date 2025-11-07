# --- build stage ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* ./
RUN npm ci || npm install
COPY . .
RUN npm run build

# --- runtime stage ---
FROM nginx:1.27-alpine AS runtime
# Copy built UI
COPY --from=build /app/dist /usr/share/nginx/html
# Copy shared brand assets (logo, favicon) to a stable path
COPY ./images /usr/share/nginx/html/images
# Minimal nginx config with fallback to index.html for SPA routing
RUN rm -f /etc/nginx/conf.d/default.conf
COPY ./nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
