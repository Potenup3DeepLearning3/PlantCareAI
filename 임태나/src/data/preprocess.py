"""이미지 전처리 모듈.

CLAHE 조명 정규화, 리사이즈, train/val/test 스플릿을 수행한다.
"""

import json
import shutil
from pathlib import Path

import cv2
import numpy as np
from loguru import logger
from sklearn.model_selection import train_test_split
from tqdm import tqdm

from src.config import (
    CLAHE_CLIP_LIMIT,
    CLAHE_TILE_GRID_SIZE,
    DATA_PROCESSED_DIR,
    DATA_RAW_DIR,
    DATA_SPLITS_DIR,
    IMAGE_SIZE,
    SEED,
)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def apply_clahe(
    image: np.ndarray,
    clip_limit: float = CLAHE_CLIP_LIMIT,
    tile_grid_size: tuple[int, int] = CLAHE_TILE_GRID_SIZE,
) -> np.ndarray:
    """CLAHE 조명 정규화 적용.

    Args:
        image: BGR 이미지 (numpy array).
        clip_limit: CLAHE clipLimit.
        tile_grid_size: CLAHE tileGridSize.

    Returns:
        CLAHE 적용된 BGR 이미지.
    """
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l_channel, a_channel, b_channel = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    l_channel = clahe.apply(l_channel)
    lab = cv2.merge([l_channel, a_channel, b_channel])
    return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)


def preprocess_image(image_path: Path, output_path: Path, image_size: int = IMAGE_SIZE) -> bool:
    """단일 이미지에 CLAHE + 리사이즈 적용 후 저장.

    Args:
        image_path: 원본 이미지 경로.
        output_path: 저장 경로.
        image_size: 출력 이미지 크기 (정사각형).

    Returns:
        성공 여부.
    """
    try:
        image = cv2.imread(str(image_path))
        if image is None:
            logger.warning(f"이미지 로드 실패: {image_path}")
            return False
        image = apply_clahe(image)
        image = cv2.resize(image, (image_size, image_size))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(output_path), image)
        return True
    except Exception as e:
        logger.warning(f"이미지 전처리 실패 {image_path}: {e}")
        return False


def preprocess_dataset(
    source_dir: Path, target_dir: Path, image_size: int = IMAGE_SIZE
) -> Path:
    """데이터셋 전체에 CLAHE + 리사이즈 적용.

    클래스 폴더 구조를 유지하며 전처리된 이미지를 저장한다.

    Args:
        source_dir: 원본 데이터셋 경로 (클래스별 서브폴더).
        target_dir: 전처리 결과 저장 경로.
        image_size: 출력 이미지 크기.

    Returns:
        전처리 완료된 디렉토리 경로.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    image_paths = [
        p for p in source_dir.rglob("*") if p.suffix.lower() in IMAGE_EXTENSIONS
    ]
    logger.info(f"전처리 시작: {source_dir.name} ({len(image_paths)}장)")

    success_count = 0
    for img_path in tqdm(image_paths, desc=f"전처리 {source_dir.name}"):
        rel_path = img_path.relative_to(source_dir)
        output_path = target_dir / rel_path
        if preprocess_image(img_path, output_path, image_size):
            success_count += 1

    logger.info(f"전처리 완료: {success_count}/{len(image_paths)}장 성공")
    return target_dir


def create_splits(
    processed_dir: Path,
    splits_dir: Path,
    ratios: tuple[float, float, float] = (0.8, 0.1, 0.1),
    seed: int = SEED,
) -> dict[str, Path]:
    """Stratified train/val/test 스플릿 생성.

    Args:
        processed_dir: 전처리된 데이터셋 경로.
        splits_dir: 스플릿 저장 경로.
        ratios: (train, val, test) 비율.
        seed: 랜덤 시드.

    Returns:
        {"train": Path, "val": Path, "test": Path} 딕셔너리.
    """
    image_paths: list[Path] = []
    labels: list[str] = []
    for img_path in processed_dir.rglob("*"):
        if img_path.suffix.lower() in IMAGE_EXTENSIONS:
            class_name = img_path.parent.name
            image_paths.append(img_path)
            labels.append(class_name)

    if not image_paths:
        logger.error(f"이미지를 찾을 수 없습니다: {processed_dir}")
        return {}

    logger.info(f"스플릿 생성: {len(image_paths)}장, {len(set(labels))}클래스")

    train_ratio, val_ratio, _ = ratios
    val_test_ratio = 1.0 - train_ratio

    paths_train, paths_valtest, labels_train, labels_valtest = train_test_split(
        image_paths, labels, test_size=val_test_ratio, stratify=labels, random_state=seed
    )
    relative_val = val_ratio / val_test_ratio
    paths_val, paths_test, _, _ = train_test_split(
        paths_valtest, labels_valtest, test_size=(1.0 - relative_val),
        stratify=labels_valtest, random_state=seed
    )

    split_paths = {}
    for split_name, split_files in [
        ("train", paths_train), ("val", paths_val), ("test", paths_test)
    ]:
        split_dir = splits_dir / split_name
        split_dir.mkdir(parents=True, exist_ok=True)
        _copy_files_to_split(split_files, processed_dir, split_dir)
        split_paths[split_name] = split_dir
        logger.info(f"  {split_name}: {len(split_files)}장")

    class_to_idx = {name: idx for idx, name in enumerate(sorted(set(labels)))}
    _save_class_mapping(splits_dir, class_to_idx)

    return split_paths


def _copy_files_to_split(files: list[Path], source_root: Path, split_dir: Path) -> None:
    """파일들을 스플릿 디렉토리로 복사 (클래스 구조 유지)."""
    for file_path in files:
        rel_path = file_path.relative_to(source_root)
        dest = split_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            shutil.copy2(file_path, dest)


def _save_class_mapping(splits_dir: Path, class_to_idx: dict[str, int]) -> None:
    """class_to_idx.json 저장."""
    mapping_path = splits_dir / "class_to_idx.json"
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(class_to_idx, f, ensure_ascii=False, indent=2)
    logger.info(f"클래스 매핑 저장: {mapping_path} ({len(class_to_idx)}클래스)")


def preprocess_all() -> None:
    """모든 데이터셋 전처리 + 스플릿 생성."""
    datasets = [
        ("plantvillage", "plantvillage"),
        ("house_plant_species", "house_plant_species"),
        ("healthy_wilted", "healthy_wilted"),
        ("houseplant_disease_scraped", "houseplant_disease_scraped"),
    ]

    for raw_name, processed_name in datasets:
        raw_dir = DATA_RAW_DIR / raw_name
        if not raw_dir.exists():
            logger.warning(f"원본 데이터 없음, 스킵: {raw_dir}")
            continue

        processed_dir = DATA_PROCESSED_DIR / processed_name
        splits_dir = DATA_SPLITS_DIR / processed_name

        if processed_dir.exists() and any(processed_dir.rglob("*.jpg")):
            logger.info(f"{processed_name} 이미 전처리됨. 스킵합니다.")
        else:
            preprocess_dataset(raw_dir, processed_dir)

        if splits_dir.exists() and (splits_dir / "class_to_idx.json").exists():
            logger.info(f"{processed_name} 스플릿 이미 존재. 스킵합니다.")
        else:
            create_splits(processed_dir, splits_dir)


def main() -> None:
    """전처리 파이프라인 실행."""
    logger.info("=== 전처리 시작 ===")
    preprocess_all()
    logger.info("=== 전처리 완료 ===")


if __name__ == "__main__":
    main()
