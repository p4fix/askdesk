# ==========================================
# Stage 1: Build Production Static Bundle
# ==========================================
FROM node:20-alpine AS builder

WORKDIR /app

# Copy dependency manifests first for optimal Docker layer caching
COPY package*.json ./
RUN npm ci || npm install

# Copy source code and build production assets
COPY . .
RUN npm run build

# ==========================================
# Stage 2: Production Nginx Runtime
# ==========================================
FROM nginx:1.27-alpine AS runner

# Remove default welcome webpage
RUN rm -rf /etc/nginx/conf.d/default.conf

# Copy custom reverse-proxy and SSE configuration
COPY nginx.conf /etc/nginx/conf.d/askdesk.conf

# Copy compiled static assets from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -qO- http://localhost/healthz || exit 1

CMD ["nginx", "-g", "daemon off;"]
