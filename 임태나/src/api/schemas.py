"""Pydantic 응답 스키마."""

from pydantic import BaseModel


# ── 분즈 ─────────────────────────────────────────────────────────

class BoonzResponse(BaseModel):
    mood: str = "default"
    message: str = ""


# ── 진단 ─────────────────────────────────────────────────────────

class SpeciesResponse(BaseModel):
    name: str
    confidence: float
    korean: str = ""


class DiseaseResponse(BaseModel):
    name: str
    confidence: float
    korean: str = ""


class LesionResponse(BaseModel):
    ratio: float
    severity: str
    overlay_base64: str = ""
    segmentation_quality: str = "양호"


class CareGuideResponse(BaseModel):
    text: str
    audio_url: str = ""


class ClipResponse(BaseModel):
    used: bool = False
    description: str = ""


class DiagnoseResponse(BaseModel):
    species: SpeciesResponse
    disease: DiseaseResponse
    disease_alternatives: list[DiseaseResponse] = []
    confidence_level: str = "높음"
    lesion: LesionResponse
    care_guide: CareGuideResponse
    boonz: BoonzResponse = BoonzResponse()
    processing_time_ms: float = 0
    clip: ClipResponse = ClipResponse()


# ── 약제 ─────────────────────────────────────────────────────────

class IngredientResponse(BaseModel):
    name: str
    concentration: str = ""


class OcrResultResponse(BaseModel):
    raw_text: str
    ingredients: list[IngredientResponse]


class CompatibilityResponse(BaseModel):
    is_compatible: bool
    reason: str


class MedicineResponse(BaseModel):
    ocr_result: OcrResultResponse
    compatibility: CompatibilityResponse
    current_diagnosis: str
    boonz: BoonzResponse = BoonzResponse()
    processing_time_ms: float = 0


# ── 음성/텍스트 상담 ──────────────────────────────────────────────

class ConsultAnswerResponse(BaseModel):
    text: str
    audio_url: str = ""


class ConsultResponse(BaseModel):
    transcript: str = ""
    question: str = ""
    answer: ConsultAnswerResponse
    boonz: BoonzResponse = BoonzResponse()
    suggested_action: str = ""
    processing_time_ms: float = 0


# ── 식물 등록 ─────────────────────────────────────────────────────

class PlantRegisterRequest(BaseModel):
    nickname: str
    species_name: str = ""


class PlantItem(BaseModel):
    nickname: str
    species_name: str = ""
    registered_at: str = ""


# ── 케어 로그 ─────────────────────────────────────────────────────

class CareLogRequest(BaseModel):
    nickname: str
    action: str
    disease: str = ""
    lesion_ratio: float | None = None


class CareLogResponse(BaseModel):
    saved: bool = True
    boonz: BoonzResponse = BoonzResponse()


# ── 타임라인 ─────────────────────────────────────────────────────

class TimelineItem(BaseModel):
    timestamp: str
    type: str  # "diagnosis" | "care"
    nickname: str
    action: str = ""
    disease: str = ""
    lesion_ratio: float | None = None


class TimelineResponse(BaseModel):
    nickname: str
    items: list[TimelineItem]
    boonz: BoonzResponse = BoonzResponse()


# ── 패턴 분석 ─────────────────────────────────────────────────────

class PatternResponse(BaseModel):
    nickname: str
    analysis: str
    boonz: BoonzResponse = BoonzResponse()
