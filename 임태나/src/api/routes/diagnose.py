"""POST /diagnose 엔드포인트."""

import time

from fastapi import APIRouter, Form, HTTPException, UploadFile
from loguru import logger

from src.api.schemas import (
    BoonzResponse,
    CareGuideResponse,
    ClipResponse,
    DiagnoseResponse,
    DiseaseResponse,
    LesionResponse,
    SpeciesResponse,
)
from src.data.remap_labels import DISEASE_TYPE_KOREAN
from src.inference.diagnose import DiagnosisPipeline
from src.inference.llm import get_boonz_mood

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
    """잎 사진으로 진단 실행. LLM/TTS 호출 없이 진단만 빠르게 반환."""
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 업로드 가능합니다.")

    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="이미지 크기는 10MB 이하여야 합니다.")

    start = time.perf_counter()

    import numpy as np
    from PIL import Image
    import io

    # PIL → numpy (한글 경로 대응, cv2.imread 미사용)
    pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
    image_rgb = np.array(pil_image)

    try:
        pipeline = _get_pipeline()
        result = pipeline.diagnose(image_rgb)
    except Exception as e:
        logger.error(f"진단 실패: {e}")
        raise HTTPException(status_code=500, detail=f"진단 중 오류가 발생했습니다: {e}")

    korean_disease = DISEASE_TYPE_KOREAN.get(result.disease.name, result.disease.name)

    # CLIP 폴백 처리 (신뢰도 < 70%)
    clip_used = False
    clip_description = ""
    if result.disease.confidence < 0.70:
        try:
            from src.inference.clip_analyzer import describe_plant_state
            import tempfile
            import os
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                tmp_path = tmp.name
                pil_image.save(tmp_path)
            clip_description = describe_plant_state(tmp_path)
            os.unlink(tmp_path)
            clip_used = True
            logger.info(f"CLIP 보완: {clip_description}")
        except Exception as e:
            logger.warning(f"CLIP 분석 실패 (무시): {e}")

    elapsed_ms = (time.perf_counter() - start) * 1000

    disease_alternatives = [
        DiseaseResponse(
            name=alt.name, confidence=alt.confidence,
            korean=DISEASE_TYPE_KOREAN.get(alt.name, alt.name),
        )
        for alt in result.disease_alternatives
    ]

    mood, message = get_boonz_mood(result.lesion.ratio, nickname)

    # 저신뢰도면 분즈 메시지에 CLIP 설명 반영
    if clip_used and clip_description:
        mood = "default"
        name = nickname or "식물"
        message = f"{name} 상태가 좀 복잡한데... 좀 더 살펴봤어. {clip_description}"

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
        care_guide=CareGuideResponse(text=""),
        boonz=BoonzResponse(mood=mood, message=message),
        processing_time_ms=round(elapsed_ms, 1),
        clip=ClipResponse(used=clip_used, description=clip_description),
    )
