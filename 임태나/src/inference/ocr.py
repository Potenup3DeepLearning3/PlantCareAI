"""약제 라벨 OCR 모듈.

EasyOCR로 약제 라벨 이미지에서 한국어 텍스트를 추출한다.
"""

import re
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from loguru import logger


@dataclass
class Ingredient:
    name: str
    concentration: str = ""


@dataclass
class OcrResult:
    raw_text: str
    ingredients: list[Ingredient]


_reader = None


def _get_reader():
    """EasyOCR Reader 싱글턴."""
    global _reader
    if _reader is None:
        import easyocr
        _reader = easyocr.Reader(["ko", "en"], gpu=True)
        logger.info("EasyOCR 로드 완료 (ko+en, GPU)")
    return _reader


def extract_text(image: np.ndarray | str | Path) -> str:
    """이미지에서 텍스트 추출.

    Args:
        image: BGR numpy 배열 또는 이미지 경로.

    Returns:
        추출된 전체 텍스트.
    """
    reader = _get_reader()

    if isinstance(image, (str, Path)):
        from PIL import Image as PILImage
        pil_img = PILImage.open(str(image)).convert("RGB")
        image_rgb = np.array(pil_img)
    else:
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    results = reader.readtext(image_rgb)
    texts = [text for _, text, conf in results if conf > 0.3]
    return " ".join(texts)


def extract_ingredients(raw_text: str) -> list[Ingredient]:
    """텍스트에서 약제 성분 + 농도 추출.

    Args:
        raw_text: OCR 추출 텍스트.

    Returns:
        Ingredient 리스트.
    """
    ingredients = []
    concentration_pattern = re.compile(r"(\d+\.?\d*)\s*(%|ppm|mg|ml|g)")

    lines = raw_text.replace(",", "\n").split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = concentration_pattern.search(line)
        if match:
            conc = match.group(0)
            name = line[:match.start()].strip().rstrip(":")
            if name:
                ingredients.append(Ingredient(name=name, concentration=conc))

    return ingredients


def ocr_medicine_label(image: np.ndarray | str | Path) -> OcrResult:
    """약제 라벨 OCR 전체 파이프라인.

    Args:
        image: 약제 라벨 이미지.

    Returns:
        OcrResult (raw_text + ingredients).
    """
    try:
        raw_text = extract_text(image)
        ingredients = extract_ingredients(raw_text)
        logger.info(f"OCR 완료: {len(ingredients)}개 성분 추출")
        return OcrResult(raw_text=raw_text, ingredients=ingredients)
    except Exception as e:
        logger.error(f"OCR 실패: {e}")
        return OcrResult(
            raw_text="라벨을 인식할 수 없습니다. 더 선명한 사진을 올려주세요.",
            ingredients=[],
        )


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        logger.error("사용법: python -m src.inference.ocr <이미지_경로>")
        sys.exit(1)
    result = ocr_medicine_label(sys.argv[1])
    logger.info(f"텍스트: {result.raw_text}")
    for ing in result.ingredients:
        logger.info(f"  성분: {ing.name} ({ing.concentration})")
