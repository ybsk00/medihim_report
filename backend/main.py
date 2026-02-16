from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.consultation import router as consultation_router
from api.report import router as report_router
from api.classify import router as classify_router
from api.youtube import router as youtube_router
from api.dashboard import router as dashboard_router
from api.public_report import router as public_report_router
from api.admin import router as admin_router

app = FastAPI(
    title="MediHim Ippo API",
    description="AI 상담 리포트 시스템 백엔드",
    version="1.0.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://*.vercel.app",
        "https://ipp0-medhim.web.app",
        "https://ipp0-medhim.firebaseapp.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(consultation_router)
app.include_router(report_router)
app.include_router(classify_router)
app.include_router(youtube_router)
app.include_router(dashboard_router)
app.include_router(public_report_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    return {"service": "MediHim Ippo API", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "ok"}
