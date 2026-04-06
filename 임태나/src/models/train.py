"""모델 학습 파이프라인.

학습 루프, 모델 비교 실험, confusion matrix, 문서 자동 생성을 담당한다.
"""

import csv
import json
import shutil
import time
from datetime import datetime
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import torch
import torch.nn as nn
from loguru import logger
from sklearn.metrics import confusion_matrix, f1_score
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import ConcatDataset, DataLoader, Subset
from tqdm import tqdm

from src.config import (
    BATCH_SIZE,
    COMPARISON_DIR,
    DATA_SPLITS_DIR,
    DATALOADER_NUM_WORKERS,
    DISEASE_MODEL_DIR,
    DOCS_DIR,
    EARLY_STOPPING_PATIENCE,
    FINETUNE_EPOCHS,
    FINETUNE_SOURCE_MIX_RATIO,
    HEALTHY_WILTED_NUM_CLASSES,
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
from src.models.disease_classifier import (
    create_convnext_tiny,
    create_efficientnet_b3,
    get_parameter_groups,
    replace_classifier_for_finetune,
)
from src.data.remap_labels import DISEASE_TYPE_NUM_CLASSES
from src.models.species_classifier import create_species_model, get_species_parameter_groups

matplotlib.use("Agg")


# ── 학습 핵심 함수들 ─────────────────────────────────────────


def train_one_epoch(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    optimizer: torch.optim.Optimizer,
    device: torch.device,
) -> tuple[float, float]:
    """한 에폭 학습 수행.

    Returns:
        (평균 손실, 정확도).
    """
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for images, labels in tqdm(dataloader, desc="학습", leave=False):
        images, labels = images.to(device), labels.to(device)
        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * images.size(0)
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()

    avg_loss = running_loss / total
    accuracy = correct / total
    return avg_loss, accuracy


def validate(
    model: nn.Module,
    dataloader: DataLoader,
    criterion: nn.Module,
    device: torch.device,
) -> tuple[float, float, list[int], list[int]]:
    """검증 수행.

    Returns:
        (평균 손실, 정확도, 예측 리스트, 라벨 리스트).
    """
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    all_preds: list[int] = []
    all_labels: list[int] = []

    with torch.no_grad():
        for images, labels in tqdm(dataloader, desc="검증", leave=False):
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)

            running_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()
            all_preds.extend(predicted.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())

    avg_loss = running_loss / total
    accuracy = correct / total
    return avg_loss, accuracy, all_preds, all_labels


# ── 체크포인트 / 로깅 ────────────────────────────────────────


def save_checkpoint(
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    epoch: int,
    val_accuracy: float,
    class_to_idx: dict[str, int],
    architecture: str,
    save_path: Path,
) -> None:
    """모델 체크포인트 저장."""
    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "epoch": epoch,
            "val_accuracy": val_accuracy,
            "class_to_idx": class_to_idx,
            "architecture": architecture,
        },
        save_path,
    )


def init_csv_log(log_path: Path) -> None:
    """CSV 로그 파일 초기화."""
    with open(log_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["epoch", "train_loss", "val_loss", "train_acc", "val_acc", "lr"]
        )
        writer.writeheader()


def append_csv_log(log_path: Path, row: dict) -> None:
    """CSV 로그에 한 행 추가."""
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f, fieldnames=["epoch", "train_loss", "val_loss", "train_acc", "val_acc", "lr"]
        )
        writer.writerow(row)


# ── 학습 메인 루프 ────────────────────────────────────────────


def train_model(
    model: nn.Module,
    dataloaders: dict[str, DataLoader],
    optimizer: torch.optim.Optimizer,
    scheduler: CosineAnnealingLR,
    num_epochs: int,
    save_dir: Path,
    model_name: str,
    architecture: str,
    class_to_idx: dict[str, int],
    patience: int = EARLY_STOPPING_PATIENCE,
) -> dict:
    """모델 학습 전체 루프.

    Returns:
        학습 결과 메트릭 딕셔너리.
    """
    device = get_device()
    model = model.to(device)
    criterion = nn.CrossEntropyLoss()
    save_dir.mkdir(parents=True, exist_ok=True)

    log_path = save_dir / f"{model_name}_training_log.csv"
    init_csv_log(log_path)
    best_path = save_dir / f"{model_name}_best.pth"

    best_val_acc = 0.0
    epochs_no_improve = 0
    start_time = time.perf_counter()

    for epoch in range(1, num_epochs + 1):
        current_lr = optimizer.param_groups[0]["lr"]
        train_loss, train_acc = train_one_epoch(
            model, dataloaders["train"], criterion, optimizer, device
        )
        val_loss, val_acc, val_preds, val_labels = validate(
            model, dataloaders["val"], criterion, device
        )
        scheduler.step()

        log_row = _build_log_row(epoch, train_loss, val_loss, train_acc, val_acc, current_lr)
        append_csv_log(log_path, log_row)
        logger.info(
            f"[{model_name}] Epoch {epoch}/{num_epochs} | "
            f"train_loss={train_loss:.4f} train_acc={train_acc:.4f} | "
            f"val_loss={val_loss:.4f} val_acc={val_acc:.4f} | lr={current_lr:.2e}"
        )

        if val_acc > best_val_acc:
            best_val_acc = val_acc
            epochs_no_improve = 0
            save_checkpoint(
                model, optimizer, epoch, val_acc, class_to_idx, architecture, best_path
            )
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:
                logger.info(f"[{model_name}] Early stopping (patience={patience})")
                break

    elapsed = time.perf_counter() - start_time
    val_f1 = f1_score(val_labels, val_preds, average="weighted")

    generate_confusion_matrix(
        val_labels, val_preds,
        list(class_to_idx.keys()), save_dir / f"{model_name}_confusion_matrix.png"
    )

    return {
        "model_name": model_name,
        "architecture": architecture,
        "best_val_accuracy": best_val_acc,
        "val_f1": val_f1,
        "training_time_sec": round(elapsed, 1),
        "total_epochs": epoch,
        "best_checkpoint": str(best_path),
    }


def _build_log_row(
    epoch: int, train_loss: float, val_loss: float,
    train_acc: float, val_acc: float, lr: float,
) -> dict:
    """CSV 로그 행 생성."""
    return {
        "epoch": epoch,
        "train_loss": f"{train_loss:.6f}",
        "val_loss": f"{val_loss:.6f}",
        "train_acc": f"{train_acc:.6f}",
        "val_acc": f"{val_acc:.6f}",
        "lr": f"{lr:.2e}",
    }


# ── Confusion Matrix / 모델 측정 ─────────────────────────────


def generate_confusion_matrix(
    labels: list[int],
    preds: list[int],
    class_names: list[str],
    save_path: Path,
) -> None:
    """Confusion matrix 생성 및 저장."""
    cm = confusion_matrix(labels, preds)
    fig_size = max(8, len(class_names) * 0.5)
    fig, ax = plt.subplots(figsize=(fig_size, fig_size))
    im = ax.imshow(cm, interpolation="nearest", cmap=plt.cm.Blues)
    ax.set_title("Confusion Matrix")
    fig.colorbar(im, ax=ax)

    if len(class_names) <= 20:
        ax.set_xticks(range(len(class_names)))
        ax.set_yticks(range(len(class_names)))
        ax.set_xticklabels(class_names, rotation=45, ha="right", fontsize=7)
        ax.set_yticklabels(class_names, fontsize=7)

    ax.set_xlabel("Predicted")
    ax.set_ylabel("True")
    plt.tight_layout()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(save_path, dpi=150)
    plt.close()
    logger.info(f"Confusion matrix 저장: {save_path}")


def measure_inference_speed(
    model: nn.Module, device: torch.device, num_runs: int = 100
) -> float:
    """추론 속도 측정 (ms/image).

    Returns:
        평균 추론 시간 (밀리초).
    """
    model.eval()
    model = model.to(device)
    dummy_input = torch.randn(1, 3, 224, 224, device=device)

    for _ in range(10):
        model(dummy_input)

    if device.type == "cuda":
        torch.cuda.synchronize()

    start = time.perf_counter()
    for _ in range(num_runs):
        model(dummy_input)
    if device.type == "cuda":
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - start

    return (elapsed / num_runs) * 1000


def get_model_size_mb(model: nn.Module) -> float:
    """모델 파라미터 크기 (MB) 반환."""
    param_size = sum(p.numel() * p.element_size() for p in model.parameters())
    return param_size / (1024 * 1024)


# ── 오케스트레이션 ────────────────────────────────────────────


def _train_pretrain(
    create_fn, architecture: str, num_classes: int, dataloaders: dict,
    class_to_idx: dict, save_dir: Path,
) -> dict:
    """사전학습 실행 헬퍼."""
    model = create_fn(num_classes, pretrained=True)
    optimizer = AdamW(model.parameters(), lr=LR_FC)
    scheduler = CosineAnnealingLR(optimizer, T_max=PRETRAIN_EPOCHS)
    return train_model(
        model, dataloaders, optimizer, scheduler,
        PRETRAIN_EPOCHS, save_dir, f"{architecture}_pretrain",
        architecture, class_to_idx,
    )


def _train_finetune(
    checkpoint_path: str, architecture: str, new_num_classes: int,
    dataloaders: dict, class_to_idx: dict, save_dir: Path,
) -> dict:
    """파인튜닝 실행 헬퍼."""
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    if architecture == "efficientnet_b3":
        model = create_efficientnet_b3(checkpoint["class_to_idx"].__len__(), pretrained=False)
    else:
        model = create_convnext_tiny(checkpoint["class_to_idx"].__len__(), pretrained=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    model = replace_classifier_for_finetune(model, new_num_classes, architecture)

    param_groups = get_parameter_groups(model, architecture, lr_fc=LR_FC, lr_backbone=LR_BACKBONE)
    optimizer = AdamW(param_groups)
    scheduler = CosineAnnealingLR(optimizer, T_max=FINETUNE_EPOCHS)
    return train_model(
        model, dataloaders, optimizer, scheduler,
        FINETUNE_EPOCHS, save_dir, f"{architecture}_finetune",
        architecture, class_to_idx,
    )


def run_disease_comparison() -> dict:
    """병변 분류 모델 비교 실험 실행.

    PlantVillage 재분류 데이터(7~9 병변 유형)로 EfficientNet-B3 vs ConvNeXt-Tiny 비교.

    Returns:
        비교 결과 딕셔너리.
    """
    logger.info("=== 병변 분류 모델 비교 실험 시작 ===")

    dt_splits = DATA_SPLITS_DIR / "disease_type"
    dt_loaders = create_dataloaders(dt_splits, batch_size=BATCH_SIZE)
    dt_class_to_idx = _load_class_mapping(dt_splits)
    num_classes = len(dt_class_to_idx)
    logger.info(f"병변 유형 클래스 수: {num_classes}")

    results = {}
    device = get_device()

    for arch, create_fn in [
        ("efficientnet_b3", create_efficientnet_b3),
        ("convnext_tiny", create_convnext_tiny),
    ]:
        logger.info(f"--- {arch} 학습 (병변 유형 {num_classes}클래스) ---")
        model = create_fn(num_classes, pretrained=True)
        optimizer = AdamW(model.parameters(), lr=LR_FC)
        scheduler = CosineAnnealingLR(optimizer, T_max=PRETRAIN_EPOCHS)
        result = train_model(
            model, dt_loaders, optimizer, scheduler,
            PRETRAIN_EPOCHS, DISEASE_MODEL_DIR, f"{arch}_disease_type",
            arch, dt_class_to_idx,
        )

        checkpoint = torch.load(result["best_checkpoint"], map_location="cpu", weights_only=True)
        eval_model = create_fn(num_classes, pretrained=False)
        eval_model.load_state_dict(checkpoint["model_state_dict"])

        result["model_size_mb"] = round(get_model_size_mb(eval_model), 2)
        result["inference_speed_ms"] = round(
            measure_inference_speed(eval_model, device), 2
        )

        # PlantDoc 크로스 데이터셋 평가
        from src.models.evaluate import evaluate_on_plantdoc
        plantdoc_result = evaluate_on_plantdoc(
            checkpoint_path=Path(result["best_checkpoint"])
        )
        if plantdoc_result:
            result["plantdoc_accuracy"] = plantdoc_result["accuracy"]
            result["plantdoc_f1"] = plantdoc_result["f1_weighted"]
        else:
            result["plantdoc_accuracy"] = None
            result["plantdoc_f1"] = None

        results[arch] = result

    # Domain Gap 계산
    for arch, res in results.items():
        pv_acc = res["best_val_accuracy"]
        pd_acc = res.get("plantdoc_accuracy")
        res["domain_gap"] = round(pv_acc - pd_acc, 4) if pd_acc is not None else None

    winner = _select_winner(results)
    _save_comparison_results(results, winner)
    _copy_best_model(results[winner])

    # 앙상블용 2등 모델도 저장
    loser = [k for k in results if k != winner]
    if loser:
        _copy_second_model(results[loser[0]])

    logger.info(f"=== 비교 실험 완료. 최종 선택: {winner} ===")
    return {"models": results, "winner": winner}


def _load_class_mapping(splits_dir: Path) -> dict[str, int]:
    """class_to_idx.json 로드."""
    mapping_path = splits_dir / "class_to_idx.json"
    with open(mapping_path, encoding="utf-8") as f:
        return json.load(f)


def _select_winner(results: dict) -> str:
    """복합 점수로 우승 모델 선택 (val 70% + PlantDoc 30%)."""
    def score(k: str) -> float:
        r = results[k]
        val_acc = r["best_val_accuracy"]
        pd_acc = r.get("plantdoc_accuracy")
        if pd_acc is not None:
            return 0.7 * val_acc + 0.3 * pd_acc
        return val_acc
    return max(results, key=score)


def _save_comparison_results(results: dict, winner: str) -> None:
    """비교 결과를 JSON으로 저장."""
    output = {
        "timestamp": datetime.now().isoformat(),
        "winner": winner,
        "models": results,
    }
    output_path = COMPARISON_DIR / "comparison_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    logger.info(f"비교 결과 저장: {output_path}")


def _copy_best_model(winner_result: dict) -> None:
    """우승 모델을 best_model.pth로 복사."""
    src = Path(winner_result["best_checkpoint"])
    dst = DISEASE_MODEL_DIR / "best_model.pth"
    shutil.copy2(src, dst)
    logger.info(f"최종 모델 저장: {dst}")


def _copy_second_model(second_result: dict) -> None:
    """2등 모델을 second_model.pth로 복사 (앙상블용)."""
    src = Path(second_result["best_checkpoint"])
    dst = DISEASE_MODEL_DIR / "second_model.pth"
    shutil.copy2(src, dst)
    logger.info(f"앙상블용 2등 모델 저장: {dst}")


def run_species_training() -> dict:
    """종 식별 모델 학습.

    Returns:
        학습 결과 메트릭.
    """
    logger.info("=== 종 식별 모델 학습 시작 ===")

    splits_dir = DATA_SPLITS_DIR / "house_plant_species"
    loaders = create_dataloaders(splits_dir, batch_size=BATCH_SIZE)
    class_to_idx = _load_class_mapping(splits_dir)

    model = create_species_model(SPECIES_NUM_CLASSES, pretrained=True)
    param_groups = get_species_parameter_groups(model, lr_fc=LR_FC, lr_backbone=LR_BACKBONE)
    optimizer = AdamW(param_groups)
    scheduler = CosineAnnealingLR(optimizer, T_max=FINETUNE_EPOCHS)

    result = train_model(
        model, loaders, optimizer, scheduler,
        FINETUNE_EPOCHS, SPECIES_MODEL_DIR, "species_model",
        "efficientnet_b3", class_to_idx,
    )

    best_src = Path(result["best_checkpoint"])
    best_dst = SPECIES_MODEL_DIR / "species_model.pth"
    if best_src != best_dst:
        shutil.copy2(best_src, best_dst)
    logger.info(f"종 식별 모델 저장: {best_dst}")
    return result


# ── 문서 생성 ─────────────────────────────────────────────────


def generate_comparison_report(comparison: dict, output_path: Path | None = None) -> None:
    """모델 비교 결과 마크다운 문서 생성."""
    output_path = output_path or DOCS_DIR / "model_comparison.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    models = comparison["models"]
    winner = comparison["winner"]

    lines = [
        "# 모델 비교 실험 결과",
        "",
        f"**실험 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**최종 선택**: {winner}",
        "",
        "## 비교 테이블",
        "",
        "| 항목 | EfficientNet-B3 | ConvNeXt-Tiny |",
        "|------|----------------|---------------|",
    ]

    metrics = [
        ("Val Accuracy", "best_val_accuracy", ".4f"),
        ("Val F1 (weighted)", "val_f1", ".4f"),
        ("PlantDoc Accuracy", "plantdoc_accuracy", ".4f"),
        ("PlantDoc F1", "plantdoc_f1", ".4f"),
        ("Domain Gap (PV-PD)", "domain_gap", ".4f"),
        ("학습 시간 (초)", "training_time_sec", ".1f"),
        ("모델 크기 (MB)", "model_size_mb", ".2f"),
        ("추론 속도 (ms)", "inference_speed_ms", ".2f"),
        ("총 에폭", "total_epochs", "d"),
    ]

    for label, key, fmt in metrics:
        eff = models.get("efficientnet_b3", {}).get(key, "N/A")
        conv = models.get("convnext_tiny", {}).get(key, "N/A")
        eff_str = f"{eff:{fmt}}" if isinstance(eff, (int, float)) else str(eff)
        conv_str = f"{conv:{fmt}}" if isinstance(conv, (int, float)) else str(conv)
        lines.append(f"| {label} | {eff_str} | {conv_str} |")

    lines.extend([
        "",
        "## 선택 근거",
        "",
        f"Val accuracy(70%)와 PlantDoc 크로스 정확도(30%)를 종합하여 "
        f"**{winner}**를 최종 모델로 선택하였다.",
        "",
        "## Domain Gap 분석",
        "",
        "Domain Gap = PlantVillage val accuracy - PlantDoc accuracy. "
        "낮을수록 실환경 일반화 성능이 좋음.",
        "",
    ])
    for arch_name in ["efficientnet_b3", "convnext_tiny"]:
        m = models.get(arch_name, {})
        gap = m.get("domain_gap")
        if gap is not None:
            lines.append(f"- **{arch_name}**: domain gap = {gap:.4f}")
    lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info(f"비교 보고서 저장: {output_path}")


# ── 메인 ──────────────────────────────────────────────────────


def run_houseplant_finetune() -> dict:
    """스크래핑 데이터로 병변 분류 모델 파인튜닝.

    best_model.pth(PlantVillage 사전학습) → 분류층 교체(8클래스) → 차등 학습률 재학습.
    Catastrophic forgetting 방지를 위해 PlantVillage 데이터를 일정 비율 혼합.

    Returns:
        학습 결과 메트릭.
    """
    logger.info("=== 반려식물 병변 파인튜닝 시작 ===")

    splits_dir = DATA_SPLITS_DIR / "houseplant_disease_scraped"
    loaders = create_dataloaders(splits_dir, batch_size=BATCH_SIZE)

    # PlantVillage 데이터 혼합 (catastrophic forgetting 방지)
    source_splits_dir = DATA_SPLITS_DIR / "disease_type"
    if source_splits_dir.exists() and FINETUNE_SOURCE_MIX_RATIO > 0:
        source_loaders = create_dataloaders(source_splits_dir, batch_size=BATCH_SIZE)
        if "train" in loaders and "train" in source_loaders:
            target_dataset = loaders["train"].dataset
            source_dataset = source_loaders["train"].dataset
            # PlantVillage에서 비율만큼 샘플링
            mix_size = int(len(target_dataset) * FINETUNE_SOURCE_MIX_RATIO / (1 - FINETUNE_SOURCE_MIX_RATIO))
            mix_size = min(mix_size, len(source_dataset))
            indices = torch.randperm(len(source_dataset))[:mix_size].tolist()
            source_subset = Subset(source_dataset, indices)
            mixed_dataset = ConcatDataset([target_dataset, source_subset])
            loaders["train"] = DataLoader(
                mixed_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=DATALOADER_NUM_WORKERS, pin_memory=True,
            )
            logger.info(
                f"혼합 배치: 반려식물 {len(target_dataset)}장 + PlantVillage {mix_size}장 "
                f"(비율: {FINETUNE_SOURCE_MIX_RATIO:.0%})",
            )

    class_to_idx = _load_class_mapping(splits_dir)
    new_num_classes = len(class_to_idx)
    logger.info(f"파인튜닝 클래스 수: {new_num_classes}")

    best_path = DISEASE_MODEL_DIR / "best_model.pth"
    checkpoint = torch.load(best_path, map_location="cpu", weights_only=True)
    architecture = checkpoint["architecture"]
    old_num_classes = len(checkpoint["class_to_idx"])

    if architecture == "efficientnet_b3":
        model = create_efficientnet_b3(old_num_classes, pretrained=False)
    else:
        model = create_convnext_tiny(old_num_classes, pretrained=False)
    model.load_state_dict(checkpoint["model_state_dict"])
    model = replace_classifier_for_finetune(model, new_num_classes, architecture)

    param_groups = get_parameter_groups(model, architecture, lr_fc=LR_FC, lr_backbone=LR_BACKBONE)
    optimizer = AdamW(param_groups)
    scheduler = CosineAnnealingLR(optimizer, T_max=FINETUNE_EPOCHS)

    result = train_model(
        model, loaders, optimizer, scheduler,
        FINETUNE_EPOCHS, DISEASE_MODEL_DIR, f"{architecture}_houseplant_finetune",
        architecture, class_to_idx,
    )

    best_src = Path(result["best_checkpoint"])
    best_dst = DISEASE_MODEL_DIR / "best_model_finetuned.pth"
    shutil.copy2(best_src, best_dst)
    logger.info(f"파인튜닝 모델 저장: {best_dst}")
    return result


def main() -> None:
    """전체 학습 파이프라인 실행."""
    setup_logging()
    set_seed()
    logger.info("========================================")
    logger.info("  PlantCare AI 학습 파이프라인 시작")
    logger.info("========================================")

    comparison = run_disease_comparison()
    species_result = run_species_training()
    generate_comparison_report(comparison)

    finetune_result = run_houseplant_finetune()

    logger.info("========================================")
    logger.info("  학습 파이프라인 완료")
    logger.info(f"  병변 분류 최종 모델: {comparison['winner']}")
    logger.info(f"  종 식별 Val Acc: {species_result['best_val_accuracy']:.4f}")
    logger.info(f"  파인튜닝 Val Acc: {finetune_result['best_val_accuracy']:.4f}")
    logger.info("========================================")


if __name__ == "__main__":
    main()
