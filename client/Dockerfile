# Stage 1: Build React App with pnpm
FROM node:24-alpine AS builder

WORKDIR /app

# Enable corepack for pnpm (already installed in Node 24 but needs enabling)
RUN corepack enable pnpm

COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml ./
RUN pnpm install

COPY . .
RUN pnpm run build

# Stage 2: Serve with Nginx
FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom config
COPY nginx.conf /etc/nginx/conf.d/

# Copy built assets from builder
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
