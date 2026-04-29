FROM node:20-alpine AS builder

ARG NEXT_PUBLIC_API_URL=https://api.clipsgold.ru
ARG NEXT_PUBLIC_WS_URL=wss://api.clipsgold.ru
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_WS_URL=$NEXT_PUBLIC_WS_URL

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY . .
RUN mkdir -p /app/public && npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/package.json ./package.json
COPY --from=builder /app/node_modules ./node_modules

EXPOSE 3000
CMD ["node_modules/.bin/next", "start", "-p", "3000"]
