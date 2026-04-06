"""Day 9 파이프라인 — 데이터 보강 + 파인튜닝 + PlantDoc 재검증.

실행 순서:
  1. Google 이미지 스크래핑 (~2,000장)
  2. 크기 필터링 (100px 이하 제거)
  3. CLIP 유사도 필터링 (노이즈 제거)
  4. 파인튜닝 (best_model.pth 기반)
  5. PlantDoc 재검증 (목표: 70%+)

사용법:
  python -m src.data.day9_pipeline
  python -m src.data.day9_pipeline --skip-scrape   # 스크래핑 건너뜀
  python -m src.data.day9_pipeline --skip-scrape --skip-clip  # 학습만
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

from loguru import logger

from src.config import DATA_RAW_DIR, DISEASE_MODEL_DIR, DOCS_DIR, set_seed, setup_logging
from src.data.clip_filter import filter_all as clip_filter_all
from src.data.scrape_images import filter_small_images, scrape_all


def _run_finetune() -> float:
    """파인튜닝 실행 후 best val_accuracy 반환."""
    from src.models.train import run_houseplant_finetune
    result = run_houseplant_finetune()
    return result.get("best_val_accuracy", 0.0)


def _run_plantdoc_eval() -> dict:
    """PlantDoc 재검증 실행 후 결과 반환."""
    from src.models.evaluate import evaluate_on_plantdoc
    return evaluate_on_plantdoc() or {}


def _count_scraped() -> int:
    """스크래핑된 이미지 총 수."""
    scrape_dir = DATA_RAW_DIR / "houseplant_disease_scraped"
    if not scrape_dir.exists():
        return 0
    return sum(
        1 for p in scrape_dir.rglob("*")
        if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
    )


def main(skip_scrape: bool = False, skip_clip: bool = False) -> None:
    setup_logging()
    set_seed()

    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info(f"Day 9 파이프라인 시작: {start_time.strftime('%Y-%m-%d %H:%M')}")
    logger.info("=" * 60)

    report: dict = {"started_at": start_time.isoformat(), "steps": {}}

    # ── Step 1: 스크래핑 ──────────────────────────────────────
    if not skip_scrape:
        logger.info("--- Step 1: Google 이미지 스크래핑 ---")
        stats = scrape_all(max_per_query=150)
        removed = filter_small_images()
        total = _count_scraped()
        logger.info(f"스크래핑 완료: {total}장 (소형 제거 {removed}장)")
        report["steps"]["scrape"] = {"total": total, "small_removed": removed, "by_class": stats}
    else:
        logger.info("--- Step 1: 스크래핑 건너뜀 ---")
        total = _count_scraped()
        logger.info(f"기존 스크래핑 데이터: {total}장")
        report["steps"]["scrape"] = {"skipped": True, "existing": total}

    # ── Step 2: CLIP 필터링 ───────────────────────────────────
    if not skip_clip:
        logger.info("--- Step 2: CLIP 유사도 필터링 ---")
        try:
            clip_results = clip_filter_all()
            after_clip = _count_scraped()
            logger.info(f"CLIP 필터링 후: {after_clip}장")
            report["steps"]["clip_filter"] = {"results": clip_results, "remaining": after_clip}
        except ImportError:
            logger.warning("CLIP 패키지 없음 → 필터링 건너뜀 (openai-clip 설치 필요)")
            report["steps"]["clip_filter"] = {"skipped": True, "reason": "openai-clip not installed"}
    else:
        logger.info("--- Step 2: CLIP 필터링 건너뜀 ---")
        report["steps"]["clip_filter"] = {"skipped": True}

    # ── Step 3: 파인튜닝 ──────────────────────────────────────
    logger.info("--- Step 3: 파인튜닝 ---")
    finetune_acc = _run_finetune()
    logger.info(f"파인튜닝 val_accuracy: {finetune_acc:.4f} ({finetune_acc*100:.2f}%)")
    report["steps"]["finetune"] = {"val_accuracy": finetune_acc}

    # ── Step 4: PlantDoc 재검증 ───────────────────────────────
    logger.info("--- Step 4: PlantDoc 재검증 ---")
    eval_result = _run_plantdoc_eval()
    plantdoc_acc = eval_result.get("plantdoc_accuracy", 0)
    logger.info(f"PlantDoc accuracy: {plantdoc_acc:.4f} ({plantdoc_acc*100:.2f}%)")
    report["steps"]["plantdoc_eval"] = eval_result

    # ── 최종 리포트 ───────────────────────────────────────────
    elapsed = (datetime.now() - start_time).seconds // 60
    report["completed_at"] = datetime.now().isoformat()
    report["elapsed_minutes"] = elapsed
    report["final_plantdoc_accuracy"] = plantdoc_acc
    report["target_reached"] = plantdoc_acc >= 0.70

    report_path = DOCS_DIR / "day9_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info("=" * 60)
    logger.info(f"Day 9 완료 ({elapsed}분 소요)")
    logger.info(f"PlantDoc 정확도: {plantdoc_acc*100:.2f}%  목표: 70.00%  {'✅ 달성' if plantdoc_acc >= 0.70 else '❌ 미달'}")
    logger.info(f"리포트 저장: {report_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Day 9 파이프라인")
    parser.add_argument("--skip-scrape", action="store_true", help="스크래핑 건너뜀")
    parser.add_argument("--skip-clip", action="store_true", help="CLIP 필터링 건너뜀")
    args = parser.parse_args()

    main(skip_scrape=args.skip_scrape, skip_clip=args.skip_clip)
