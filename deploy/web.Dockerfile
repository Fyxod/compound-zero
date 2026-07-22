# syntax=docker/dockerfile:1.7

FROM node:24.18.0-bookworm-slim AS build

ENV PNPM_HOME=/pnpm \
    PATH=/pnpm:$PATH

WORKDIR /workspace
RUN corepack enable && corepack prepare pnpm@11.9.0 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
RUN pnpm install --frozen-lockfile --filter @compound-zero/web...

COPY apps/web ./apps/web

ARG VITE_API_BASE_URL=/api
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN pnpm --filter @compound-zero/web build


FROM nginxinc/nginx-unprivileged:1.31.3-alpine3.24 AS runtime

COPY deploy/nginx.conf /etc/nginx/nginx.conf
COPY --from=build --chown=101:101 /workspace/apps/web/dist /usr/share/nginx/html

USER 101
EXPOSE 8080

HEALTHCHECK CMD wget --quiet --tries=1 --spider http://127.0.0.1:8080/healthz || exit 1

# Bypass mutation-oriented image entrypoint scripts so the runtime remains
# compatible with the read-only filesystem enforced by Compose.
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
