from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


# ============================================
# Enums
# ============================================
class Classification(str, Enum):
    DERMATOLOGY = "dermatology"
    PLASTIC_SURGERY = "plastic_surgery"
    DENTISTRY = "dentistry"
    UNCLASSIFIED = "unclassified"


class CTALevel(str, Enum):
    HOT = "hot"
    WARM = "warm"
    COOL = "cool"


class ConsultationStatus(str, Enum):
    REGISTERED = "registered"
    PROCESSING = "processing"
    CLASSIFICATION_PENDING = "classification_pending"
    REPORT_GENERATING = "report_generating"
    REPORT_READY = "report_ready"
    REPORT_APPROVED = "report_approved"
    REPORT_SENT = "report_sent"
    REPORT_FAILED = "report_failed"


class ReportStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"


# ============================================
# Request Models
# ============================================
class ConsultationCreate(BaseModel):
    customer_id: Optional[str] = ""
    customer_name: Optional[str] = ""
    customer_email: Optional[str] = ""
    customer_line_id: Optional[str] = ""
    original_text: str


class ConsultationBulkCreate(BaseModel):
    consultations: List[ConsultationCreate]


class AdminUserCreate(BaseModel):
    username: str
    password: str


class ClassifyRequest(BaseModel):
    classification: Classification


class CTAUpdateRequest(BaseModel):
    cta_level: CTALevel


class ReportEditRequest(BaseModel):
    report_data: dict


class ReportRegenerateRequest(BaseModel):
    direction: str


# [R1-R3 비활성화] 28일 R4 테스트 후 활성화 예정
# class SendEmailRequest(BaseModel):
#     to_email: Optional[str] = None  # R1~R3용 수동 이메일 입력


class ConsultationUpdateRequest(BaseModel):
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_line_id: Optional[str] = None
    customer_id: Optional[str] = None


class GenerateReportsRequest(BaseModel):
    consultation_ids: List[str]


class BulkApproveRequest(BaseModel):
    report_ids: List[str]


class BirthDateVerify(BaseModel):
    birth_date: str


class YouTubeAddRequest(BaseModel):
    video_url: str
    category: Classification


# ============================================
# Response Models
# ============================================
class ConsultationResponse(BaseModel):
    id: str
    status: str


class DashboardStats(BaseModel):
    total_consultations: int
    unclassified_count: int
    report_pending_count: int
    sent_count: int
    view_rate: float
    cta_hot: int
    cta_warm: int
    cta_cool: int



# ============================================
# 이뻐 앱 연동 Models
# ============================================
class IppeoConsultationRequest(BaseModel):
    """이뻐 → 우리: 상담 STT 데이터 전송"""
    customer_name: str
    customer_email: Optional[str] = ""
    stt_text: Optional[str] = ""  # STT 원문 텍스트 (직접 전달)
    stt_file_url: Optional[str] = ""  # S3 Presigned URL (10분 유효)
    consultation_round: int = 1  # 1차, 2차, 3차...
    hospital_name: Optional[str] = ""
    doctor_name: Optional[str] = ""
    concern_area: Optional[str] = ""
    # 이뻐 측 ID (콜백 시 그대로 돌려줌)
    ippeo_user_id: Optional[str] = ""
    ippeo_consultation_id: Optional[str] = ""
