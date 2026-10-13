// (.mjs인 이유: Docker 실행 단계에는 TypeScript가 없어 next.config.ts를 읽지 못함)
// 프록시 모드 (AWS 등 Docker 배포용): BACKEND_INTERNAL_URL을 빌드 시 지정하면
// Next 서버가 /api/* 요청을 백엔드로 넘긴다 → 브라우저는 프론트 주소만 호출 (백엔드 포트 외부 노출 불필요).
// 이 경우 NEXT_PUBLIC_API_URL="/api" (상대경로)로 빌드할 것.
// 미지정 시(운영 Firebase) 기존과 동일 — 브라우저가 NEXT_PUBLIC_API_URL(Cloud Run)을 직접 호출.
const BACKEND_INTERNAL_URL = process.env.BACKEND_INTERNAL_URL?.replace(/\/$/, "");

/** @type {import("next").NextConfig} */
const nextConfig = {
  images: { unoptimized: true },
  ...(BACKEND_INTERNAL_URL && {
    async rewrites() {
      return [{ source: "/api/:path*", destination: `${BACKEND_INTERNAL_URL}/api/:path*` }];
    },
    experimental: {
      proxyTimeout: 900_000, // 15분 — 재생성·번역·음성 STT 등 장시간 요청 (기본 30초)
      proxyClientMaxBodySize: "100mb", // 음성 파일 업로드 (기본 10MB)
    },
  }),
};

export default nextConfig;
