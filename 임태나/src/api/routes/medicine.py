"""POST /check-medicine 엔드포인트."""

import time

from fastapi import APIRouter, Form, HTTPException, UploadFile
from loguru import logger

from src.api.schemas import (
    BoonzResponse,
    CompatibilityResponse,
    IngredientResponse,
    MedicineResponse,
    OcrResultResponse,
)
from src.inference.llm import judge_medicine_compatibility
from src.inference.ocr import ocr_medicine_label

router = APIRouter()

# 세션 캐시: 마지막 진단 결과
_last_diagnosis: str = ""


def set_last_diagnosis(disease_name: str) -> None:
    global _last_diagnosis
    _last_diagnosis = disease_name


@router.post("/medicine", response_model=MedicineResponse)
async def check_medicine(
    file: UploadFile,
    nickname: str = Form(""),
) -> MedicineResponse:
    """약제 라벨 이미지 OCR + 적합성 판단."""
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

    try:
        ocr_result = ocr_medicine_label(image_bgr)
    except Exception as e:
        logger.error(f"OCR 실패: {e}")
        raise HTTPException(status_code=500, detail=f"OCR 처리 중 오류: {e}")

    ingredients_text = ", ".join(
        f"{ing.name} {ing.concentration}" for ing in ocr_result.ingredients
    )
    if not ingredients_text:
        ingredients_text = ocr_result.raw_text

    name = nickname or "식물"
    compatibility = {
        "is_compatible": False,
        "reason": "진단 이력이 없습니다. 먼저 사진 진단을 해주세요.",
    }
    if _last_diagnosis:
        compatibility = judge_medicine_compatibility(
            _last_diagnosis, ingredients_text, plant_nickname=name,
        )

    elapsed_ms = (time.perf_counter() - start) * 1000

    is_ok = compatibility.get("is_compatible", False)
    mood = "happy" if is_ok else "worried"
    message = (
        f"{name}한테 보여줬는데, 이거 괜찮대"
        if is_ok
        else f"{name}가 이건 별로래. 다른 거 찾아보자"
    )

    return MedicineResponse(
        ocr_result=OcrResultResponse(
            raw_text=ocr_result.raw_text,
            ingredients=[
                IngredientResponse(name=ing.name, concentration=ing.concentration)
                for ing in ocr_result.ingredients
            ],
        ),
        compatibility=CompatibilityResponse(**compatibility),
        current_diagnosis=_last_diagnosis,
        boonz=BoonzResponse(mood=mood, message=message),
        processing_time_ms=round(elapsed_ms, 1),
    )
