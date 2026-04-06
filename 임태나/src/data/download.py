"""데이터셋 다운로드 스크립트.

3개 데이터셋을 다운로드한다:
1. PlantVillage (HuggingFace) — 병변 패턴 사전학습 (38클래스, ~43K장)
2. House Plant Species (HuggingFace) — 47종 반려식물 종 식별
3. Healthy/Wilted Houseplant (Kaggle) — 건강/시듦 2클래스 분류 (904장)
"""

import os
import tarfile
from pathlib import Path

from loguru import logger

from src.config import DATA_RAW_DIR, KAGGLE_KEY, KAGGLE_USERNAME

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def count_images(directory: Path) -> int:
    """디렉토리 내 이미지 파일 수 반환."""
    if not directory.exists():
        return 0
    return sum(1 for f in directory.rglob("*") if f.suffix.lower() in IMAGE_EXTENSIONS)


def count_classes(directory: Path) -> int:
    """클래스(서브디렉토리) 수 반환."""
    if not directory.exists():
        return 0
    return sum(1 for d in directory.iterdir() if d.is_dir())


def validate_dataset(
    path: Path, expected_min_images: int, expected_classes: int, name: str
) -> bool:
    """데이터셋 검증."""
    num_images = count_images(path)
    num_classes = count_classes(path)
    if num_images >= expected_min_images and num_classes >= expected_classes:
        logger.info(f"[{name}] 검증 통과: {num_images}장, {num_classes}클래스")
        return True
    logger.warning(
        f"[{name}] 검증 실패: {num_images}장(기대 {expected_min_images}+), "
        f"{num_classes}클래스(기대 {expected_classes})"
    )
    return False


# ── 1. PlantVillage ──────────────────────────────────────────


def download_plantvillage(target_dir: Path | None = None) -> Path:
    """HuggingFace에서 PlantVillage 다운로드 (~43K장, 38클래스)."""
    target_dir = target_dir or DATA_RAW_DIR / "plantvillage"

    if validate_dataset(target_dir, 40000, 30, "PlantVillage"):
        logger.info("PlantVillage 이미 다운로드됨. 스킵합니다.")
        return target_dir

    logger.info("PlantVillage 다운로드 시작 (HuggingFace)...")
    from datasets import load_dataset

    ds = load_dataset(
        "BrandonFors/Plant-Diseases-PlantVillage-Dataset", split="train"
    )
    target_dir.mkdir(parents=True, exist_ok=True)

    for idx, sample in enumerate(ds):
        label = sample["label"]
        label_name = ds.features["label"].int2str(label)
        class_dir = target_dir / label_name
        class_dir.mkdir(parents=True, exist_ok=True)
        image_path = class_dir / f"{idx:06d}.jpg"
        if not image_path.exists():
            sample["image"].save(image_path)

        if (idx + 1) % 10000 == 0:
            logger.info(f"PlantVillage: {idx + 1}장 저장 완료")

    logger.info(f"PlantVillage 다운로드 완료: {count_images(target_dir)}장")
    return target_dir


# ── 2. House Plant Species ───────────────────────────────────


def download_house_plant_species(target_dir: Path | None = None) -> Path:
    """HuggingFace에서 House Plant Species 다운로드 (47종)."""
    target_dir = target_dir or DATA_RAW_DIR / "house_plant_species"

    if validate_dataset(target_dir, 100, 40, "House Plant Species"):
        logger.info("House Plant Species 이미 다운로드됨. 스킵합니다.")
        return target_dir

    logger.info("House Plant Species 다운로드 시작 (HuggingFace)...")
    from huggingface_hub import hf_hub_download

    tar_path = hf_hub_download(
        repo_id="kakasher/house-plant-species",
        filename="house_plant_species.tar",
        repo_type="dataset",
    )
    target_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"TAR 압축 해제 중: {tar_path}")
    with tarfile.open(tar_path, "r") as tar:
        tar.extractall(path=target_dir, filter="data")

    _flatten_extracted_dirs(target_dir)
    logger.info(f"House Plant Species 다운로드 완료: {count_images(target_dir)}장")
    return target_dir


# ── 3. Healthy/Wilted Houseplant (Kaggle) ────────────────────


def download_healthy_wilted(target_dir: Path | None = None) -> Path:
    """Kaggle에서 Healthy/Wilted Houseplant 다운로드 (904장, 2클래스)."""
    target_dir = target_dir or DATA_RAW_DIR / "healthy_wilted"

    if validate_dataset(target_dir, 800, 2, "Healthy/Wilted"):
        logger.info("Healthy/Wilted 이미 다운로드됨. 스킵합니다.")
        return target_dir

    if not KAGGLE_USERNAME or not KAGGLE_KEY:
        raise ValueError(
            "KAGGLE_USERNAME과 KAGGLE_KEY가 필요합니다. .env를 확인해주세요."
        )

    logger.info("Healthy/Wilted Houseplant 다운로드 시작 (Kaggle)...")
    os.environ["KAGGLE_USERNAME"] = KAGGLE_USERNAME
    os.environ["KAGGLE_KEY"] = KAGGLE_KEY

    from kaggle.api.kaggle_api_extended import KaggleApi

    api = KaggleApi()
    api.authenticate()
    api.dataset_download_files(
        "russellchan/healthy-and-wilted-houseplant-images",
        path=str(target_dir),
        unzip=True,
    )

    _flatten_extracted_dirs(target_dir)
    logger.info(f"Healthy/Wilted 다운로드 완료: {count_images(target_dir)}장")
    return target_dir


# ── 유틸 ──────────────────────────────────────────────────────


def _flatten_extracted_dirs(target_dir: Path) -> None:
    """압축 해제 후 중첩 디렉토리 평탄화."""
    import shutil

    subdirs = [d for d in target_dir.iterdir() if d.is_dir()]
    if len(subdirs) == 1:
        nested = subdirs[0]
        inner_items = list(nested.iterdir())
        if all(d.is_dir() for d in inner_items):
            for d in inner_items:
                dest = target_dir / d.name
                if not dest.exists():
                    shutil.move(str(d), str(dest))
            if not any(nested.iterdir()):
                nested.rmdir()
            logger.info(f"디렉토리 평탄화 완료: {target_dir}")


# ── 메인 ──────────────────────────────────────────────────────


def main() -> None:
    """모든 데이터셋 다운로드 실행."""
    logger.info("=== 데이터셋 다운로드 시작 ===")

    pv_dir = download_plantvillage()
    validate_dataset(pv_dir, 40000, 30, "PlantVillage")

    species_dir = download_house_plant_species()
    validate_dataset(species_dir, 100, 40, "House Plant Species")

    hw_dir = download_healthy_wilted()
    validate_dataset(hw_dir, 800, 2, "Healthy/Wilted")

    logger.info("=== 모든 데이터셋 다운로드 완료 ===")
    logger.info(f"  PlantVillage: {count_images(pv_dir)}장")
    logger.info(f"  House Plant Species: {count_images(species_dir)}장")
    logger.info(f"  Healthy/Wilted: {count_images(hw_dir)}장")


if __name__ == "__main__":
    main()
