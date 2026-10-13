# 프론트엔드(Next.js) 컨테이너 — AWS 등 Firebase 외 환경 배포용
# NEXT_PUBLIC_* 값은 빌드 시점에 번들에 박히므로 --build-arg로 전달해야 한다.
#
# (권장) 프록시 모드 — 브라우저는 프론트만 호출, Next 서버가 /api/* 를 백엔드로 전달:
#   docker build -t medihim-frontend --build-arg NEXT_PUBLIC_API_URL=/api \
#     --build-arg BACKEND_INTERNAL_URL=http://<was>:8003 .
# (직접 호출 모드) NEXT_PUBLIC_API_URL=http://<backend>/api 만 지정 → 브라우저가 백엔드 직접 호출 (CORS 필요)
#
#   docker run -d -p 3003:3000 medihim-frontend
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_SITE_URL
ARG BACKEND_INTERNAL_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL \
    BACKEND_INTERNAL_URL=$BACKEND_INTERNAL_URL \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build && npm prune --omit=dev

FROM node:22-alpine
WORKDIR /app
ARG BACKEND_INTERNAL_URL
ARG NEXT_PUBLIC_SITE_URL
# next start가 next.config.mjs를 다시 읽으므로(프록시 타임아웃 등) 실행 단계에도 값과 파일이 필요
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    BACKEND_INTERNAL_URL=$BACKEND_INTERNAL_URL \
    NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
COPY --from=build /app/package.json /app/next.config.mjs ./
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/.next ./.next
COPY --from=build /app/public ./public
EXPOSE 3000
CMD ["npx", "next", "start", "-p", "3000"]
