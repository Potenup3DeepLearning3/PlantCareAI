"""학습 재개: ConvNeXt-Tiny + 비교 + Species.

EfficientNet-B3은 이미 완료 (Epoch 6, val_acc 99.86%).
"""

import json
import shutil
from pathlib import Path

import torch
from loguru import logger
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR

from src.config import (
    BATCH_SIZE,
    COMPARISON_DIR,
    DATA_SPLITS_DIR,
    DISEASE_MODEL_DIR,
    DOCS_DIR,
    FINETUNE_EPOCHS,
    LR_BACKBONE,
    LR_FC,
    PRETRAIN_EPOCHS,
    SPECIES_MODEL_DIR,
    SPECIES_NUM_CLASSES,
    get_device,
    set_seed,
    setup_logging,
)
from src.data.dataset import create_dataloaders
from src.models.disease_classifier import create_convnext_tiny, create_efficientnet_b3
from src.models.species_classifier import create_species_model, get_species_parameter_groups
from src.models.train import (
    _copy_best_model,
    _load_class_mapping,
    _save_comparison_results,
    _select_winner,
    generate_comparison_report,
    get_model_size_mb,
    measure_inference_speed,
    train_model,
)


def main() -> None:
    setup_logging()
    set_seed()
    device = get_device()

    # ── 1. EfficientNet-B3 결과 로드 ─────────────────────────
    logger.info("=== EfficientNet-B3 기존 결과 로드 ===")
    eff_ckpt_path = DISEASE_MODEL_DIR / "efficientnet_b3_disease_type_best.pth"
    eff_ckpt = torch.load(eff_ckpt_path, map_location="cpu", weights_only=True)
    dt_class_to_idx = eff_ckpt["class_to_idx"]
    num_classes = len(dt_class_to_idx)

    eff_model = create_efficientnet_b3(num_classes, pretrained=False)
    eff_model.load_state_dict(eff_ckpt["model_state_dict"])

    eff_result = {
        "model_name": "efficientnet_b3_disease_type",
        "architecture": "efficientnet_b3",
        "best_val_accuracy": eff_ckpt["val_accuracy"],
        "val_f1": 0.0,
        "training_time_sec": 0,
        "total_epochs": eff_ckpt["epoch"],
        "best_checkpoint": str(eff_ckpt_path),
        "model_size_mb": round(get_model_size_mb(eff_model), 2),
        "inference_speed_ms": round(measure_inference_speed(eff_model, device), 2),
    }
    logger.info(f"EfficientNet-B3: val_acc={eff_result['best_val_accuracy']:.4f}")

    # ── 2. ConvNeXt-Tiny 학습 ────────────────────────────────
    logger.info("=== ConvNeXt-Tiny 학습 시작 ===")
    dt_splits = DATA_SPLITS_DIR / "disease_type"
    dt_loaders = create_dataloaders(dt_splits, batch_size=BATCH_SIZE)

    conv_model = create_convnext_tiny(num_classes, pretrained=True)
    optimizer = AdamW(conv_model.parameters(), lr=LR_FC)
    scheduler = CosineAnnealingLR(optimizer, T_max=PRETRAIN_EPOCHS)

    conv_result = train_model(
        conv_model, dt_loaders, optimizer, scheduler,
        PRETRAIN_EPOCHS, DISEASE_MODEL_DIR, "convnext_tiny_disease_type",
        "convnext_tiny", dt_class_to_idx,
    )

    conv_ckpt = torch.load(conv_result["best_checkpoint"], map_location="cpu", weights_only=True)
    eval_model = create_convnext_tiny(num_classes, pretrained=False)
    eval_model.load_state_dict(conv_ckpt["model_state_dict"])
    conv_result["model_size_mb"] = round(get_model_size_mb(eval_model), 2)
    conv_result["inference_speed_ms"] = round(measure_inference_speed(eval_model, device), 2)

    # ── 3. 비교 + 최종 선택 ──────────────────────────────────
    results = {"efficientnet_b3": eff_result, "convnext_tiny": conv_result}
    winner = _select_winner(results)
    _save_comparison_results(results, winner)
    _copy_best_model(results[winner])
    logger.info(f"=== 비교 완료. 최종 선택: {winner} ===")

    comparison = {"models": results, "winner": winner}
    generate_comparison_report(comparison)

    # ── 4. Species 모델 학습 ─────────────────────────────────
    logger.info("=== 종 식별 모델 학습 시작 ===")
    sp_splits = DATA_SPLITS_DIR / "house_plant_species"
    sp_loaders = create_dataloaders(sp_splits, batch_size=BATCH_SIZE)
    sp_class_to_idx = _load_class_mapping(sp_splits)

    sp_model = create_species_model(len(sp_class_to_idx), pretrained=True)
    sp_groups = get_species_parameter_groups(sp_model, lr_fc=LR_FC, lr_backbone=LR_BACKBONE)
    sp_optimizer = AdamW(sp_groups)
    sp_scheduler = CosineAnnealingLR(sp_optimizer, T_max=FINETUNE_EPOCHS)

    sp_result = train_model(
        sp_model, sp_loaders, sp_optimizer, sp_scheduler,
        FINETUNE_EPOCHS, SPECIES_MODEL_DIR, "species_model",
        "efficientnet_b3", sp_class_to_idx,
    )

    best_src = Path(sp_result["best_checkpoint"])
    best_dst = SPECIES_MODEL_DIR / "species_model.pth"
    if best_src != best_dst:
        shutil.copy2(best_src, best_dst)

    logger.info("========================================")
    logger.info("  학습 파이프라인 완료")
    logger.info(f"  병변 분류 최종 모델: {winner}")
    logger.info(f"  종 식별 Val Acc: {sp_result['best_val_accuracy']:.4f}")
    logger.info("========================================")


if __name__ == "__main__":
    main()
