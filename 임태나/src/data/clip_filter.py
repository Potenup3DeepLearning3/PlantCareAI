"""CLIP 유사도 필터링 — 스크래핑 데이터 노이즈 제거.

OpenAI CLIP으로 수집된 이미지와 텍스트 프롬프트 간 유사도를 계산하여
식물 병변과 무관한 이미지를 제거한다.
"""

from pathlib import Path

import torch
from loguru import logger
from PIL import Image, UnidentifiedImageError

from src.config import DATA_RAW_DIR

SCRAPE_DIR = DATA_RAW_DIR / "houseplant_disease_scraped"

# 클래스별 CLIP 텍스트 프롬프트
CLASS_PROMPTS: dict[str, list[str]] = {
    "overwatering":        ["overwatered plant yellow leaves", "houseplant overwatering damage"],
    "dehydration":         ["dehydrated wilting plant", "dried out houseplant curling leaves"],
    "powdery_mildew":      ["powdery mildew white fungus plant leaf", "흰가루병 잎"],
    "sunburn":             ["sunburned plant leaf brown patches", "houseplant sun damage"],
    "rust":                ["rust disease orange spots plant leaf", "녹병 반점"],
    "nutrient_deficiency": ["plant nutrient deficiency yellowing", "indoor plant mineral deficiency"],
    "root_rot":            ["root rot plant brown mushy", "과습 무름병"],
    "stress":              ["stressed houseplant leaf drop", "식물 스트레스 잎"],
}

# 최소 CLIP 유사도 임계값 (0~1)
SIMILARITY_THRESHOLD = 0.22
# 배치 크기
BATCH_SIZE = 32


def _load_clip_model(device: torch.device):
    """CLIP 모델 + 전처리 함수 로드."""
    try:
        import clip
        model, preprocess = clip.load("ViT-B/32", device=device)
        return model, preprocess, clip
    except ImportError:
        logger.error("clip 패키지가 없습니다. 'uv add openai-clip' 실행 후 재시도하세요.")
        raise


def filter_class(
    class_name: str,
    threshold: float = SIMILARITY_THRESHOLD,
    device: torch.device | None = None,
) -> tuple[int, int]:
    """한 클래스 폴더의 이미지를 CLIP으로 필터링.

    Args:
        class_name: 클래스 폴더명.
        threshold: CLIP 유사도 임계값.
        device: 추론 디바이스.

    Returns:
        (유지된 수, 제거된 수) 튜플.
    """
    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    model, preprocess, clip = _load_clip_model(device)

    class_dir = SCRAPE_DIR / class_name
    if not class_dir.exists():
        logger.warning(f"{class_name} 폴더 없음: {class_dir}")
        return 0, 0

    prompts = CLASS_PROMPTS.get(class_name, [f"plant disease {class_name}"])
    text_tokens = clip.tokenize(prompts).to(device)
    with torch.no_grad():
        text_features = model.encode_text(text_tokens)
        text_features = text_features / text_features.norm(dim=-1, keepdim=True)
    # 클래스 텍스트 벡터 평균
    text_vec = text_features.mean(dim=0, keepdim=True)

    img_paths = [
        p for p in class_dir.rglob("*")
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    ]

    kept = 0
    removed = 0

    for i in range(0, len(img_paths), BATCH_SIZE):
        batch_paths = img_paths[i:i + BATCH_SIZE]
        batch_tensors = []
        valid_paths = []

        for p in batch_paths:
            try:
                img = preprocess(Image.open(p).convert("RGB")).unsqueeze(0)
                batch_tensors.append(img)
                valid_paths.append(p)
            except (UnidentifiedImageError, Exception):
                p.unlink(missing_ok=True)
                removed += 1
                continue

        if not batch_tensors:
            continue

        batch = torch.cat(batch_tensors).to(device)
        with torch.no_grad():
            img_features = model.encode_image(batch)
            img_features = img_features / img_features.norm(dim=-1, keepdim=True)

        similarities = (img_features @ text_vec.T).squeeze(1)

        for path, sim in zip(valid_paths, similarities.tolist()):
            if sim < threshold:
                path.unlink(missing_ok=True)
                removed += 1
            else:
                kept += 1

    logger.info(f"[{class_name}] 유지 {kept}장 / 제거 {removed}장")
    return kept, removed


def filter_all(threshold: float = SIMILARITY_THRESHOLD) -> dict[str, dict[str, int]]:
    """전체 스크래핑 데이터 CLIP 필터링.

    Returns:
        클래스별 {"kept": int, "removed": int} 딕셔너리.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logger.info(f"CLIP 필터링 시작 (device={device}, threshold={threshold})")

    results: dict[str, dict[str, int]] = {}
    for class_name in CLASS_PROMPTS:
        kept, removed = filter_class(class_name, threshold, device)
        results[class_name] = {"kept": kept, "removed": removed}

    total_kept = sum(v["kept"] for v in results.values())
    total_removed = sum(v["removed"] for v in results.values())
    logger.info(f"=== CLIP 필터링 완료: 유지 {total_kept}장 / 제거 {total_removed}장 ===")
    return results


if __name__ == "__main__":
    results = filter_all()
    for cls, stat in results.items():
        logger.info(f"  {cls}: 유지 {stat['kept']}장, 제거 {stat['removed']}장")
