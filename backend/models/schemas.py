from pydantic import BaseModel
from typing import Optional, List
from enum import Enum


# ============================================
# Enums
# ============================================
class Classification(str, Enum):
    DERMATOLOGY = "dermatology"
    PLASTIC_SURGERY = "plastic_surgery"
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


class GenerateReportsRequest(BaseModel):
    consultation_ids: List[str]


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
