FROM node:24-slim AS build
WORKDIR /app
# Copy manifests first so the npm ci layer stays cached until dependencies change.
COPY package.json package-lock.json ./ 
RUN npm ci
COPY . .
RUN npm run build

FROM caddy:2.11.7
COPY Caddyfile /etc/caddy/Caddyfile
COPY --from=build /app/dist /srv