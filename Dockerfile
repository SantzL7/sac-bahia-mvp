FROM node:22-alpine
WORKDIR /app
COPY package*.json ./
RUN set -eu; \
    if [ -f package-lock.json ]; then \
      npm ci --omit=dev --no-audit --no-fund; \
    else \
      npm install --omit=dev --no-audit --no-fund; \
    fi
COPY api ./api
COPY worker ./worker
COPY shared ./shared
USER node
CMD ["node", "api/src/server.js"]
