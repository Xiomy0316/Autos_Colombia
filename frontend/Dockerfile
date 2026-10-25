# --- Autos Colombia · Interfaz (Angular) ---
# Etapa 1: compilar la aplicación
FROM node:24-alpine AS build

WORKDIR /srv/app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .
# Build de producción: angular.json reemplaza environment.ts por
# environment.prod.ts, de modo que la interfaz llama a /api.
RUN npm run build

# Etapa 2: servir el bundle con nginx
FROM nginx:1.31-alpine

# Angular entrega dist/frontend/browser (builder de aplicación)
COPY --from=build /srv/app/dist/frontend/browser /usr/share/nginx/html

# Plantilla con envsubst: ${PORT} y ${API_URL} se resuelven en el arranque.
# nginx escucha en ${PORT} (10000 en Render, 8080 en docker-compose).
COPY nginx/templates /etc/nginx/templates/
