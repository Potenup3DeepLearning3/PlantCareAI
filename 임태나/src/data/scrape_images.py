"""Google Images 자동 스크래핑 (Day 4).

icrawler로 반려식물 병변 이미지를 자동 수집한다.
검색어별 클래스 폴더에 저장 후 노이즈 필터링.
"""

from pathlib import Path

from icrawler.builtin import BingImageCrawler
from loguru import logger
from PIL import Image

from src.config import DATA_RAW_DIR

SCRAPE_DIR = DATA_RAW_DIR / "houseplant_disease_scraped"

# 검색어 → 클래스 매핑
SEARCH_QUERIES: dict[str, list[str]] = {
    "overwatering": [
        "monstera overwatering yellowing leaves",
        "snake plant overwatering mushy",
        "스투키 과습 물렁",
        "몬스테라 과습 노란잎",
    ],
    "dehydration": [
        "pothos dehydration wilting curling",
        "화분 잎 처짐 시듦",
        "스킨답서스 잎 마름",
    ],
    "powdery_mildew": [
        "monstera powdery mildew white spots",
        "houseplant powdery mildew indoor",
        "몬스테라 흰가루병",
    ],
    "sunburn": [
        "houseplant sunburn brown patches leaf",
        "고무나무 잎 갈변",
    ],
    "rust": [
        "houseplant rust orange spots underside",
        "반려식물 잎 반점",
    ],
    "nutrient_deficiency": [
        "houseplant mineral deficiency yellow leaves",
        "indoor plant leaf curl disease",
    ],
    "root_rot": [
        "snake plant root rot brown tips",
        "산세베리아 무름병",
        "pothos brown spots disease",
    ],
    "stress": [
        "rubber plant leaf drop stress",
    ],
}

MAX_PER_QUERY = 100
MIN_IMAGE_SIZE = 100  # px


def scrape_all(max_per_query: int = MAX_PER_QUERY) -> dict[str, int]:
    """모든 검색어로 이미지 스크래핑.

    Returns:
        클래스별 수집 장수 딕셔너리.
    """
    SCRAPE_DIR.mkdir(parents=True, exist_ok=True)
    stats: dict[str, int] = {}

    for class_name, queries in SEARCH_QUERIES.items():
        class_dir = SCRAPE_DIR / class_name
        class_dir.mkdir(parents=True, exist_ok=True)

        total = 0
        for query in queries:
            logger.info(f"[{class_name}] 검색: '{query}'")
            try:
                crawler = BingImageCrawler(
                    storage={"root_dir": str(class_dir)},
                    log_level=40,
                )
                crawler.crawl(
                    keyword=query,
                    max_num=max_per_query,
                )
                count = _count_images(class_dir)
                added = count - total
                total = count
                logger.info(f"  → {added}장 수집 (누적 {total}장)")
            except Exception as e:
                logger.warning(f"  → 스크래핑 실패: {e}")

        stats[class_name] = total

    return stats


def filter_small_images(min_size: int = MIN_IMAGE_SIZE) -> int:
    """크기가 작은 이미지 제거.

    Returns:
        제거된 이미지 수.
    """
    removed = 0
    for img_path in SCRAPE_DIR.rglob("*"):
        if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        try:
            with Image.open(img_path) as img:
                w, h = img.size
                if w < min_size or h < min_size:
                    img_path.unlink()
                    removed += 1
        except Exception:
            img_path.unlink()
            removed += 1

    logger.info(f"노이즈 필터링: {removed}장 제거")
    return removed


def _count_images(directory: Path) -> int:
    """디렉토리 내 이미지 수."""
    extensions = {".jpg", ".jpeg", ".png", ".webp"}
    return sum(1 for f in directory.rglob("*") if f.suffix.lower() in extensions)


def main() -> None:
    """스크래핑 + 필터링 실행."""
    logger.info("=== Google Images 스크래핑 시작 ===")
    stats = scrape_all()

    logger.info("=== 노이즈 필터링 ===")
    filter_small_images()

    total = sum(stats.values())
    logger.info("=== 스크래핑 완료 ===")
    for cls, count in sorted(stats.items()):
        logger.info(f"  {cls}: {count}장")
    logger.info(f"  총: {total}장")


if __name__ == "__main__":
    main()
