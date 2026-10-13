# 프론트엔드(Next.js) 컨테이너 — AWS 등 Firebase 외 환경 배포용
# NEXT_PUBLIC_* 값은 빌드 시점에 번들에 박히므로 --build-arg로 전달해야 한다.
#   docker build -t medihim-frontend --build-arg NEXT_PUBLIC_API_URL=http://<was>:8003 .
#   docker run -d -p 3003:3000 medihim-frontend
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_SITE_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build && npm prune --omit=dev

FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY --from=build /app/package.json ./
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/.next ./.next
COPY --from=build /app/public ./public
EXPOSE 3000
CMD ["npx", "next", "start", "-p", "3000"]
