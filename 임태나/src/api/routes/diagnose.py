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

# 서버 시작 시 1회 생성 — 이후 모든 요청이 이 인스턴스를 공유
_pipeline = DiagnosisPipeline()


def warmup() -> None:
    """서버 startup 시 호출 — 모델 파일을 미리 메모리에 올린다."""
    logger.info("DiagnosisPipeline 사전 로드 시작")
    _pipeline._ensure_species()
    _pipeline._ensure_disease()
    _pipeline._ensure_sam()
    logger.info("DiagnosisPipeline 사전 로드 완료")


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
        result = _pipeline.diagnose(image_rgb)
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
            clip_result = describe_plant_state(tmp_path)
            if isinstance(clip_result, tuple):
                clip_description, _ = clip_result
            else:
                clip_description = str(clip_result)
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
