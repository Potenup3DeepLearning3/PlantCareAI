"""PlantVillage 38클래스 → 7~8개 병변 유형으로 재분류.

작물별 질병 분류를 병변 패턴 기반 분류로 변환한다.
재분류된 데이터는 data/processed/disease_type/에 저장된다.
"""

import shutil
from pathlib import Path

from loguru import logger

from src.config import DATA_PROCESSED_DIR, DATA_RAW_DIR, DATA_SPLITS_DIR, SEED
from src.data.preprocess import (
    IMAGE_EXTENSIONS,
    create_splits,
    preprocess_dataset,
)

# ── 38클래스 → 병변 유형 매핑 ─────────────────────────────────

DISEASE_TYPE_MAPPING: dict[str, str] = {
    # Healthy
    "Apple___healthy": "Healthy",
    "Blueberry___healthy": "Healthy",
    "Cherry_(including_sour)___healthy": "Healthy",
    "Corn_(maize)___healthy": "Healthy",
    "Grape___healthy": "Healthy",
    "Peach___healthy": "Healthy",
    "Pepper,_bell___healthy": "Healthy",
    "Potato___healthy": "Healthy",
    "Raspberry___healthy": "Healthy",
    "Soybean___healthy": "Healthy",
    "Strawberry___healthy": "Healthy",
    "Tomato___healthy": "Healthy",
    # Powdery Mildew (흰가루병)
    "Squash___Powdery_mildew": "Powdery_Mildew",
    "Cherry_(including_sour)___Powdery_mildew": "Powdery_Mildew",
    # Rust (녹병)
    "Apple___Cedar_apple_rust": "Rust",
    "Corn_(maize)___Common_rust_": "Rust",
    # Leaf Curl (잎말림)
    "Tomato___Tomato_Yellow_Leaf_Curl_Virus": "Leaf_Curl",
    # Early Blight (초기 역병)
    "Tomato___Early_blight": "Early_Blight",
    "Potato___Early_blight": "Early_Blight",
    # Late Blight (후기 역병)
    "Tomato___Late_blight": "Late_Blight",
    "Potato___Late_blight": "Late_Blight",
    "Corn_(maize)___Northern_Leaf_Blight": "Late_Blight",
    "Grape___Leaf_blight_(Isariopsis_Leaf_Spot)": "Late_Blight",
    # Bacterial Spot (세균성 반점)
    "Tomato___Bacterial_spot": "Bacterial_Spot",
    "Pepper,_bell___Bacterial_spot": "Bacterial_Spot",
    "Peach___Bacterial_spot": "Bacterial_Spot",
    # Septoria Leaf Spot (셉토리아 잎 반점)
    "Tomato___Septoria_leaf_spot": "Septoria_Leaf_Spot",
    # Target Spot (표적 반점)
    "Tomato___Target_Spot": "Target_Spot",
    # Other Leaf Spot (기타 잎 반점)
    "Tomato___Spider_mites Two-spotted_spider_mite": "Other_Leaf_Spot",
    "Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot": "Other_Leaf_Spot",
    "Strawberry___Leaf_scorch": "Other_Leaf_Spot",
    # Leaf Mold (잎곰팡이)
    "Tomato___Leaf_Mold": "Leaf_Mold",
    # Mosaic Virus (모자이크 바이러스)
    "Tomato___Tomato_mosaic_virus": "Mosaic_Virus",
    # Scab & Rot (흑성병/부패)
    "Apple___Apple_scab": "Scab_Rot",
    "Apple___Black_rot": "Scab_Rot",
    "Grape___Black_rot": "Scab_Rot",
    "Grape___Esca_(Black_Measles)": "Scab_Rot",
    # Greening (황룡병)
    "Orange___Haunglongbing_(Citrus_greening)": "Greening",
}

DISEASE_TYPE_NUM_CLASSES = len(set(DISEASE_TYPE_MAPPING.values()))

# 한국어 매핑
DISEASE_TYPE_KOREAN: dict[str, str] = {
    "Healthy": "건강",
    "Powdery_Mildew": "흰가루병",
    "Rust": "녹병",
    "Leaf_Curl": "잎말림",
    "Early_Blight": "초기 역병",
    "Late_Blight": "후기 역병",
    "Bacterial_Spot": "세균성 반점",
    "Septoria_Leaf_Spot": "셉토리아 잎 반점",
    "Target_Spot": "표적 반점",
    "Other_Leaf_Spot": "기타 잎 반점",
    "Leaf_Mold": "잎곰팡이",
    "Mosaic_Virus": "모자이크 바이러스",
    "Scab_Rot": "흑성병/부패",
    "Greening": "황룡병",
}


def remap_plantvillage(
    source_dir: Path | None = None,
    target_dir: Path | None = None,
) -> Path:
    """PlantVillage 원본 데이터를 병변 유형 기준으로 재분류.

    Args:
        source_dir: PlantVillage 원본 경로 (38클래스 서브폴더).
        target_dir: 재분류 결과 저장 경로.

    Returns:
        재분류된 데이터셋 경로.
    """
    source_dir = source_dir or DATA_RAW_DIR / "plantvillage"
    target_dir = target_dir or DATA_PROCESSED_DIR / "disease_type"

    if not source_dir.exists():
        raise FileNotFoundError(f"PlantVillage 데이터 없음: {source_dir}")

    target_dir.mkdir(parents=True, exist_ok=True)
    stats: dict[str, int] = {}
    unmapped: list[str] = []

    for class_dir in sorted(source_dir.iterdir()):
        if not class_dir.is_dir():
            continue

        original_class = class_dir.name
        disease_type = DISEASE_TYPE_MAPPING.get(original_class)

        if disease_type is None:
            unmapped.append(original_class)
            logger.warning(f"매핑 없는 클래스, 스킵: {original_class}")
            continue

        dest_dir = target_dir / disease_type
        dest_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        for img_path in class_dir.rglob("*"):
            if img_path.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            dest_path = dest_dir / f"{original_class}_{img_path.name}"
            if not dest_path.exists():
                shutil.copy2(img_path, dest_path)
            count += 1

        stats[disease_type] = stats.get(disease_type, 0) + count

    _log_remap_results(stats, unmapped)
    return target_dir


def _log_remap_results(stats: dict[str, int], unmapped: list[str]) -> None:
    """재분류 결과 로깅."""
    logger.info("=== PlantVillage 병변 유형 재분류 결과 ===")
    total = 0
    for disease_type, count in sorted(stats.items()):
        korean = DISEASE_TYPE_KOREAN.get(disease_type, "")
        logger.info(f"  {disease_type} ({korean}): {count}장")
        total += count
    logger.info(f"  총: {total}장, {len(stats)}클래스")
    if unmapped:
        logger.warning(f"  매핑 없는 클래스: {unmapped}")


def remap_and_split() -> None:
    """재분류 + CLAHE 전처리 + 스플릿 생성."""
    raw_disease_type = remap_plantvillage()

    processed_dir = DATA_PROCESSED_DIR / "disease_type_processed"
    if processed_dir.exists() and any(processed_dir.rglob("*.jpg")):
        logger.info("disease_type 이미 전처리됨. 스킵합니다.")
    else:
        preprocess_dataset(raw_disease_type, processed_dir)

    splits_dir = DATA_SPLITS_DIR / "disease_type"
    if splits_dir.exists() and (splits_dir / "class_to_idx.json").exists():
        logger.info("disease_type 스플릿 이미 존재. 스킵합니다.")
    else:
        create_splits(processed_dir, splits_dir, seed=SEED)


def main() -> None:
    """재분류 파이프라인 실행."""
    logger.info("=== PlantVillage 병변 유형 재분류 시작 ===")
    remap_and_split()
    logger.info("=== 재분류 완료 ===")


if __name__ == "__main__":
    main()
