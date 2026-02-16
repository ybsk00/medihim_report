import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
REPLY_TO_EMAIL = os.getenv("REPLY_TO_EMAIL", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", "report@ippo.co.kr")
JWT_SECRET = os.getenv("JWT_SECRET", "medihim-ippo-jwt-secret-key-2026")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

# PubMed / NCBI
NCBI_API_KEY = os.getenv("NCBI_API_KEY", "")
NCBI_EMAIL = os.getenv("NCBI_EMAIL", "bsyoo1974@gamil.com")
NCBI_TOOL = os.getenv("NCBI_TOOL", "ADC-GenAI-Platform")

# 벡터DB 구축 대상 YouTube 채널 (피부과 5 + 성형외과 6)
TARGET_CHANNELS = [
    # 피부과
    {
        "channel_id": "UC8av1CNslnPQS3N08rkzzhQ",
        "name": "오프라이드 oh-pride",
        "category": "dermatology",
    },
    {
        "channel_id": "UC5lOe8buRS42zIjN0H4o_WA",
        "name": "닥터주디 피부과전문의",
        "category": "dermatology",
    },
    {
        "channel_id": "",
        "handle": "@doctorfiller",
        "name": "닥터필러 에버피부과 김지은",
        "category": "dermatology",
    },
    {
        "channel_id": "UCFpFZkm7mclD-z_-j7FTUag",
        "name": "톡스앤필 ToxNFill",
        "category": "dermatology",
    },
    {
        "channel_id": "UCglQ_gvV5TSsyVBBg8B4Jzw",
        "name": "바노바기 피부과",
        "category": "dermatology",
    },
    # 성형외과
    {
        "channel_id": "UCQdXdttJJTiHwCczJGkgRIg",
        "name": "나나TV - 나나성형외과",
        "category": "plastic_surgery",
    },
    {
        "channel_id": "",
        "handle": "@idhospital",
        "name": "아이디병원 ID Hospital",
        "category": "plastic_surgery",
    },
    {
        "channel_id": "",
        "handle": "@DAprs",
        "name": "디에이성형외과 DA",
        "category": "plastic_surgery",
    },
    {
        "channel_id": "",
        "handle": "@banobagi",
        "name": "바노바기 성형외과",
        "category": "plastic_surgery",
    },
    {
        "channel_id": "",
        "handle": "@viewplasticsurgery",
        "name": "뷰 성형외과 (VIEW)",
        "category": "plastic_surgery",
    },
    {
        "channel_id": "",
        "handle": "@wonjinbeauty",
        "name": "원진 성형외과 (Wonjin)",
        "category": "plastic_surgery",
    },
    # 성형외과 추가 (STT 필요)
    {
        "channel_id": "UCF_-dQyYKvXudcoxzPVJCSQ",
        "name": "우리성형외과",
        "category": "plastic_surgery",
    },
    {
        "channel_id": "UCqWXdw_2MCDdjrgkZHVVn8Q",
        "name": "제이티성형외과 JT",
        "category": "plastic_surgery",
    },
    {
        "channel_id": "UCJT2E9l8zniBfgGqhXCSajQ",
        "name": "마인성형외과",
        "category": "plastic_surgery",
    },
    # 피부과 추가 (STT 필요)
    {
        "channel_id": "UC908f2Qj4Jz2bs9XzDdPMLg",
        "name": "피알남 피부과전문의 김홍석",
        "category": "dermatology",
    },
    {
        "channel_id": "UCHQ1sKCV0R3Xwk4-Ck2dV-A",
        "name": "닥터피부광",
        "category": "dermatology",
    },
]
