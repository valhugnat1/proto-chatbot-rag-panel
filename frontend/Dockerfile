# --- Stage 1: build the Vue app ---------------------------------------------
FROM node:22-alpine AS build

WORKDIR /app

# VITE_API_URL is baked in at build time. Override with --build-arg for prod.
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

COPY package.json ./
RUN npm install

COPY index.html vite.config.js ./
COPY public ./public
COPY src ./src

RUN npm run build

# --- Stage 2: serve with nginx ----------------------------------------------
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost/ >/dev/null || exit 1
