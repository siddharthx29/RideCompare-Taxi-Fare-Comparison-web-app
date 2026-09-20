# Build Stage
FROM node:18-alpine AS builder

WORKDIR /app

COPY package*.json tsconfig.json ./

RUN npm ci

COPY src ./src

RUN npm run build

# Production Stage
FROM node:18-alpine AS runner

WORKDIR /app

ENV NODE_ENV=production

COPY package*.json ./

RUN npm ci --only=production

COPY --from=builder /app/dist ./dist
COPY --from=builder /app/src/db/migrations ./dist/db/migrations
COPY src/db/schema.sql ./src/db/schema.sql

EXPOSE 5000

CMD ["node", "dist/index.js"]
