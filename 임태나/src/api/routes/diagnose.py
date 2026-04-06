"""POST /diagnose 엔드포인트."""

import time

from fastapi import APIRouter, Form, HTTPException, UploadFile
from loguru import logger

from src.api.schemas import (
    BoonzResponse,
    CareGuideResponse,
    DiagnoseResponse,
    DiseaseResponse,
    LesionResponse,
    SpeciesResponse,
)
from src.data.remap_labels import DISEASE_TYPE_KOREAN
from src.inference.diagnose import DiagnosisPipeline
from src.inference.llm import generate_care_guide, get_boonz_mood
from src.inference.tts import get_audio_url, text_to_speech

router = APIRouter()
_pipeline: DiagnosisPipeline | None = None


def _get_pipeline() -> DiagnosisPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = DiagnosisPipeline()
    return _pipeline


@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(
    file: UploadFile,
    nickname: str = Form(""),
) -> DiagnoseResponse:
    """잎 사진으로 진단 실행."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다.")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="이미지 크기는 10MB 이하여야 합니다.")

    start = time.perf_counter()

    import cv2
    import numpy as np

    nparr = np.frombuffer(contents, np.uint8)
    image_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if image_bgr is None:
        raise HTTPException(status_code=400, detail="이미지를 읽을 수 없습니다.")
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    try:
        pipeline = _get_pipeline()
        result = pipeline.diagnose(image_rgb)
    except Exception as e:
        logger.error(f"진단 실패: {e}")
        raise HTTPException(status_code=500, detail=f"진단 중 오류가 발생했습니다: {e}")

    korean_disease = DISEASE_TYPE_KOREAN.get(result.disease.name, result.disease.name)

    guide_text = generate_care_guide(
        species_name=result.species.name,
        disease_korean_name=korean_disease,
        confidence=result.disease.confidence,
        lesion_ratio=result.lesion.ratio,
        severity=result.lesion.severity,
        plant_nickname=nickname,
    )

    audio_path = text_to_speech(guide_text)
    audio_url = get_audio_url(audio_path)

    elapsed_ms = (time.perf_counter() - start) * 1000

    disease_alternatives = [
        DiseaseResponse(
            name=alt.name, confidence=alt.confidence,
            korean=DISEASE_TYPE_KOREAN.get(alt.name, alt.name),
        )
        for alt in result.disease_alternatives
    ]

    mood, message = get_boonz_mood(result.lesion.ratio, nickname)

    return DiagnoseResponse(
        species=SpeciesResponse(
            name=result.species.name, confidence=result.species.confidence,
        ),
        disease=DiseaseResponse(
            name=result.disease.name, confidence=result.disease.confidence,
            korean=korean_disease,
        ),
        disease_alternatives=disease_alternatives,
        confidence_level=result.confidence_level,
        lesion=LesionResponse(
            ratio=result.lesion.ratio, severity=result.lesion.severity,
            overlay_base64=result.lesion.overlay_image_base64,
            segmentation_quality=result.lesion.segmentation_quality,
        ),
        care_guide=CareGuideResponse(text=guide_text, audio_url=audio_url),
        boonz=BoonzResponse(mood=mood, message=message),
        processing_time_ms=round(elapsed_ms, 1),
    )
