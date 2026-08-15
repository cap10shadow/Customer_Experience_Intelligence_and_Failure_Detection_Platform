# Phase 13 Batch 9 (AD-2, §20): multi-stage, additive only. The `dev`
# stage below is byte-for-byte the same single-stage image this
# Dockerfile always built -- docker-compose.yml now pins `target: dev`
# explicitly so the development workflow is completely unchanged. The
# `build`/`production` stages are new, used only by
# docker-compose.prod.yml, and implement §20's "production frontend
# build" requirement (`npm run build`, already scripted but never
# invoked before this batch) + a minimal static-serve stage -- no new
# frontend framework, no routing change.

FROM node:20-alpine AS base
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

FROM base AS dev
COPY . .
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM base AS build
COPY . .
RUN npm run build

FROM nginx:1.27-alpine AS production
# Same-origin API proxy + SPA fallback (see nginx.conf) -- the
# production equivalent of vite.config.ts's dev-only `/api` ->
# gateway_service:8000 proxy (AD-6, §9). No Vite dev server here.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
