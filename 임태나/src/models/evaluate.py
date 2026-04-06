"""모델 평가 스크립트.

PlantDoc 데이터셋 및 테스트 스플릿으로 모델 정확도를 평가하고
정확도 리포트를 생성한다.
"""

import json
from pathlib import Path

import torch
import torch.nn as nn
from loguru import logger
from sklearn.metrics import classification_report, f1_score
from torch.utils.data import DataLoader
from tqdm import tqdm

from src.config import (
    BATCH_SIZE,
    DATA_SPLITS_DIR,
    DISEASE_MODEL_DIR,
    DOCS_DIR,
    IMAGE_SIZE,
    get_device,
    set_seed,
    setup_logging,
)
from src.data.dataset import PlantDataset, get_eval_transforms, load_class_to_idx
from src.models.disease_classifier import create_efficientnet_b3, create_convnext_tiny
from src.models.train import generate_confusion_matrix


def load_model_from_checkpoint(
    checkpoint_path: Path, device: torch.device,
) -> tuple[nn.Module, dict[str, int], dict[int, str]]:
    """체크포인트에서 모델 로드.

    Returns:
        (모델, class_to_idx, idx_to_class).
    """
    ckpt = torch.load(checkpoint_path, map_location=device, weights_only=True)
    arch = ckpt["architecture"]
    class_to_idx = ckpt["class_to_idx"]
    num_classes = len(class_to_idx)
    idx_to_class = {v: k for k, v in class_to_idx.items()}

    if arch == "efficientnet_b3":
        model = create_efficientnet_b3(num_classes, pretrained=False)
    else:
        model = create_convnext_tiny(num_classes, pretrained=False)
    model.load_state_dict(ckpt["model_state_dict"])
    model.to(device).eval()
    return model, class_to_idx, idx_to_class


def evaluate_on_dataloader(
    model: nn.Module, dataloader: DataLoader, device: torch.device,
) -> tuple[float, float, list[int], list[int]]:
    """DataLoader로 모델 평가.

    Returns:
        (정확도, f1, 예측 리스트, 라벨 리스트).
    """
    model.eval()
    correct = 0
    total = 0
    all_preds: list[int] = []
    all_labels: list[int] = []

    with torch.no_grad():
        for images, labels in tqdm(dataloader, desc="평가"):
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()
            all_preds.extend(predicted.cpu().tolist())
            all_labels.extend(labels.cpu().tolist())

    accuracy = correct / total if total > 0 else 0.0
    f1 = f1_score(all_labels, all_preds, average="weighted", zero_division=0)
    return accuracy, f1, all_preds, all_labels


def evaluate_disease_model() -> dict:
    """병변 분류 모델 (best_model.pth) 테스트 스플릿 평가."""
    device = get_device()
    model_path = DISEASE_MODEL_DIR / "best_model.pth"
    model, class_to_idx, idx_to_class = load_model_from_checkpoint(model_path, device)

    splits_dir = DATA_SPLITS_DIR / "disease_type"
    test_dir = splits_dir / "test"
    if not test_dir.exists():
        logger.warning("disease_type 테스트 스플릿이 없습니다.")
        return {}

    dataset = PlantDataset(test_dir, transform=get_eval_transforms(), class_to_idx=class_to_idx)
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    logger.info(f"병변 분류 모델 평가 (테스트 {len(dataset)}장)")
    acc, f1, preds, labels = evaluate_on_dataloader(model, dataloader, device)

    class_names = [idx_to_class[i] for i in range(len(class_to_idx))]
    generate_confusion_matrix(
        labels, preds, class_names,
        DISEASE_MODEL_DIR / "best_model_test_confusion_matrix.png",
    )

    report = classification_report(
        labels, preds, target_names=class_names, output_dict=True, zero_division=0,
    )

    return {
        "model": "best_model.pth (PlantVillage 사전학습)",
        "dataset": "disease_type test split",
        "num_samples": len(dataset),
        "accuracy": round(acc, 4),
        "f1_weighted": round(f1, 4),
        "per_class": {
            name: {
                "precision": round(report[name]["precision"], 4),
                "recall": round(report[name]["recall"], 4),
                "f1": round(report[name]["f1-score"], 4),
                "support": report[name]["support"],
            }
            for name in class_names if name in report
        },
    }


def evaluate_finetuned_model() -> dict:
    """파인튜닝 모델 (best_model_finetuned.pth) 테스트 스플릿 평가."""
    device = get_device()
    model_path = DISEASE_MODEL_DIR / "best_model_finetuned.pth"
    if not model_path.exists():
        logger.warning("파인튜닝 모델이 없습니다.")
        return {}

    model, class_to_idx, idx_to_class = load_model_from_checkpoint(model_path, device)

    splits_dir = DATA_SPLITS_DIR / "houseplant_disease_scraped"
    test_dir = splits_dir / "test"
    if not test_dir.exists():
        logger.warning("houseplant_disease_scraped 테스트 스플릿이 없습니다.")
        return {}

    dataset = PlantDataset(test_dir, transform=get_eval_transforms(), class_to_idx=class_to_idx)
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    logger.info(f"파인튜닝 모델 평가 (테스트 {len(dataset)}장)")
    acc, f1, preds, labels = evaluate_on_dataloader(model, dataloader, device)

    class_names = [idx_to_class[i] for i in range(len(class_to_idx))]
    generate_confusion_matrix(
        labels, preds, class_names,
        DISEASE_MODEL_DIR / "finetuned_test_confusion_matrix.png",
    )

    report = classification_report(
        labels, preds, target_names=class_names, output_dict=True, zero_division=0,
    )

    return {
        "model": "best_model_finetuned.pth (스크래핑 파인튜닝)",
        "dataset": "houseplant_disease_scraped test split",
        "num_samples": len(dataset),
        "accuracy": round(acc, 4),
        "f1_weighted": round(f1, 4),
        "per_class": {
            name: {
                "precision": round(report[name]["precision"], 4),
                "recall": round(report[name]["recall"], 4),
                "f1": round(report[name]["f1-score"], 4),
                "support": report[name]["support"],
            }
            for name in class_names if name in report
        },
    }


def evaluate_species_model() -> dict:
    """종 식별 모델 평가."""
    from src.config import SPECIES_MODEL_DIR

    device = get_device()
    model_path = SPECIES_MODEL_DIR / "species_model.pth"
    if not model_path.exists():
        logger.warning("종 식별 모델이 없습니다.")
        return {}

    model, class_to_idx, idx_to_class = load_model_from_checkpoint(model_path, device)

    splits_dir = DATA_SPLITS_DIR / "house_plant_species"
    test_dir = splits_dir / "test"
    if not test_dir.exists():
        logger.warning("house_plant_species 테스트 스플릿이 없습니다.")
        return {}

    dataset = PlantDataset(test_dir, transform=get_eval_transforms(), class_to_idx=class_to_idx)
    dataloader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    logger.info(f"종 식별 모델 평가 (테스트 {len(dataset)}장)")
    acc, f1, preds, labels = evaluate_on_dataloader(model, dataloader, device)

    class_names = [idx_to_class[i] for i in range(len(class_to_idx))]
    generate_confusion_matrix(
        labels, preds, class_names,
        SPECIES_MODEL_DIR / "species_test_confusion_matrix.png",
    )

    return {
        "model": "species_model.pth",
        "dataset": "house_plant_species test split",
        "num_samples": len(dataset),
        "accuracy": round(acc, 4),
        "f1_weighted": round(f1, 4),
    }


# ── PlantDoc 크로스 데이터셋 평가 ────────────────────────────


# PlantDoc 클래스 → 모델 9클래스 매핑
# 모델 class_to_idx: Blight_Spot(0), Greening(1), Healthy(2), Leaf_Curl(3),
#   Leaf_Mold(4), Mosaic_Virus(5), Powdery_Mildew(6), Rust(7), Scab_Rot(8)
# Blight_Spot = Bacterial_Spot + Early_Blight + Late_Blight + Leaf_Spot 합침
PLANTDOC_TO_DISEASE_TYPE: dict[str, str] = {
    "Apple Scab Leaf": "Scab_Rot",
    "Apple leaf": "Healthy",
    "Apple rust leaf": "Rust",
    "Bell_pepper leaf spot": "Blight_Spot",
    "Bell_pepper leaf": "Healthy",
    "Blueberry leaf": "Healthy",
    "Cherry leaf": "Healthy",
    "Corn Gray leaf spot": "Blight_Spot",
    "Corn leaf blight": "Blight_Spot",
    "Corn rust leaf": "Rust",
    "Peach leaf": "Healthy",
    "Potato leaf early blight": "Blight_Spot",
    "Potato leaf late blight": "Blight_Spot",
    "Potato leaf": "Healthy",
    "Raspberry leaf": "Healthy",
    "Soyabean leaf": "Healthy",
    "Soybean leaf": "Healthy",
    "Squash Powdery mildew leaf": "Powdery_Mildew",
    "Strawberry leaf": "Healthy",
    "Tomato Early blight leaf": "Blight_Spot",
    "Tomato Septoria leaf spot": "Blight_Spot",
    "Tomato leaf bacterial spot": "Blight_Spot",
    "Tomato leaf late blight": "Blight_Spot",
    "Tomato leaf mosaic virus": "Mosaic_Virus",
    "Tomato leaf yellow virus": "Leaf_Curl",
    "Tomato leaf": "Healthy",
    "Tomato mold leaf": "Leaf_Mold",
    "grape leaf black rot": "Scab_Rot",
    "grape leaf": "Healthy",
}


def _tta_predict(
    model: nn.Module, tensor: torch.Tensor, device: torch.device,
) -> torch.Tensor:
    """TTA 추론: 원본 + 좌우반전 + 90도 회전의 소프트맥스 평균."""
    augmented = [
        tensor,
        torch.flip(tensor, dims=[-1]),
        torch.rot90(tensor, k=1, dims=[-2, -1]),
    ]
    probs = []
    with torch.no_grad():
        for t in augmented:
            out = model(t.to(device))
            probs.append(torch.softmax(out, dim=1))
    return torch.stack(probs).mean(dim=0)


def evaluate_on_plantdoc(checkpoint_path: Path | None = None) -> dict:
    """PlantDoc 데이터셋으로 크로스 데이터셋 평가 (실제 환경 검증).

    TTA(3종 증강 평균)를 적용하여 도메인 갭을 줄인다.

    Args:
        checkpoint_path: 평가할 모델 체크포인트. None이면 best_model.pth 사용.
    """
    device = get_device()
    model_path = checkpoint_path or (DISEASE_MODEL_DIR / "best_model.pth")
    if not model_path.exists():
        logger.warning(f"체크포인트를 찾을 수 없습니다: {model_path}")
        return {}
    model, class_to_idx, idx_to_class = load_model_from_checkpoint(model_path, device)

    # PlantDoc 경로 탐색
    from src.config import DATA_RAW_DIR
    plantdoc_root = DATA_RAW_DIR / "plantdoc_data"

    # ZIP 추출 후 중첩 폴더 탐색
    test_dir = None
    for candidate in [
        plantdoc_root / "PlantDoc-Dataset-master" / "test",
        plantdoc_root / "PlantDoc-Dataset-master" / "Test",
        plantdoc_root / "test",
        plantdoc_root / "Test",
    ]:
        if candidate.exists():
            test_dir = candidate
            break

    if test_dir is None:
        # train 폴더라도 사용
        for candidate in [
            plantdoc_root / "PlantDoc-Dataset-master" / "train",
            plantdoc_root / "PlantDoc-Dataset-master" / "Train",
            plantdoc_root / "train",
        ]:
            if candidate.exists():
                test_dir = candidate
                break

    if test_dir is None:
        logger.warning(f"PlantDoc 데이터를 찾을 수 없습니다: {plantdoc_root}")
        return {}

    logger.info(f"PlantDoc 평가 디렉토리: {test_dir}")

    # 매핑 가능한 클래스만 수집
    from src.data.preprocess import IMAGE_EXTENSIONS
    samples: list[tuple[Path, int, str, str]] = []  # (path, mapped_idx, original_class, mapped_class)
    unmapped_classes: set[str] = set()

    for class_dir in sorted(test_dir.iterdir()):
        if not class_dir.is_dir():
            continue
        original_class = class_dir.name
        mapped_class = PLANTDOC_TO_DISEASE_TYPE.get(original_class)
        if mapped_class is None:
            unmapped_classes.add(original_class)
            continue
        if mapped_class not in class_to_idx:
            continue
        mapped_idx = class_to_idx[mapped_class]
        for img_path in class_dir.rglob("*"):
            if img_path.suffix.lower() in IMAGE_EXTENSIONS:
                samples.append((img_path, mapped_idx, original_class, mapped_class))

    if not samples:
        logger.warning("PlantDoc에서 매핑 가능한 이미지가 없습니다.")
        return {}

    if unmapped_classes:
        logger.warning(f"매핑 안 된 PlantDoc 클래스: {unmapped_classes}")

    logger.info(f"PlantDoc 평가 샘플: {len(samples)}장 (매핑 {len(PLANTDOC_TO_DISEASE_TYPE)}클래스)")

    # TTA 추론 (CLAHE 미적용 — 실제 환경 이미지에는 오히려 성능 저하)
    from src.data.dataset import get_eval_transforms
    transform = get_eval_transforms()
    from PIL import Image as PILImage

    correct = 0
    total = 0
    all_preds: list[int] = []
    all_labels: list[int] = []
    failure_cases: list[dict] = []

    model.eval()
    with torch.no_grad():
        for img_path, true_idx, orig_class, mapped_class in tqdm(samples, desc="PlantDoc 평가"):
            try:
                img = PILImage.open(img_path).convert("RGB")
                tensor = transform(img).unsqueeze(0).to(device)
                avg_prob = _tta_predict(model, tensor, device)
                conf, pred_idx = avg_prob.max(1)
                pred_idx = pred_idx.item()
                conf_val = conf.item()
            except Exception as e:
                logger.warning(f"이미지 처리 실패: {img_path}: {e}")
                continue

            all_preds.append(pred_idx)
            all_labels.append(true_idx)
            total += 1

            if pred_idx == true_idx:
                correct += 1
            else:
                failure_cases.append({
                    "image": str(img_path.name),
                    "original_class": orig_class,
                    "true_label": mapped_class,
                    "predicted": idx_to_class.get(pred_idx, f"idx_{pred_idx}"),
                    "confidence": round(conf_val, 4),
                })

    accuracy = correct / total if total > 0 else 0.0
    f1 = f1_score(all_labels, all_preds, average="weighted", zero_division=0)

    class_names = [idx_to_class[i] for i in range(len(class_to_idx))]
    generate_confusion_matrix(
        all_labels, all_preds, class_names,
        DISEASE_MODEL_DIR / f"plantdoc_{model_path.stem}_confusion_matrix.png",
    )

    from sklearn.metrics import classification_report
    report = classification_report(
        all_labels, all_preds, target_names=class_names,
        output_dict=True, zero_division=0,
    )

    return {
        "model": f"{model_path.stem} (PlantDoc 크로스 평가, TTA)",
        "dataset": f"PlantDoc ({test_dir.name})",
        "num_samples": total,
        "accuracy": round(accuracy, 4),
        "f1_weighted": round(f1, 4),
        "failure_cases": failure_cases,
        "per_class": {
            name: {
                "precision": round(report[name]["precision"], 4),
                "recall": round(report[name]["recall"], 4),
                "f1": round(report[name]["f1-score"], 4),
                "support": report[name]["support"],
            }
            for name in class_names if name in report
        },
    }


def generate_failure_log(
    failure_cases: list[dict], output_path: Path | None = None,
) -> None:
    """실패 케이스 마크다운 로그 생성."""
    output_path = output_path or DOCS_DIR / "failure_cases.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    lines = [
        "# 실패 케이스 로그",
        "",
        f"**생성 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**총 오분류 건수**: {len(failure_cases)}",
        "",
    ]

    if not failure_cases:
        lines.append("오분류 케이스가 없습니다.")
    else:
        # 오분류 패턴 분석
        from collections import Counter
        pattern_counter: Counter = Counter()
        for fc in failure_cases:
            pattern_counter[(fc["true_label"], fc["predicted"])] += 1

        lines.extend([
            "## 주요 오분류 패턴",
            "",
            "| 실제 | 예측 | 건수 |",
            "|------|------|------|",
        ])
        for (true, pred), count in pattern_counter.most_common(20):
            lines.append(f"| {true} | {pred} | {count} |")

        lines.extend([
            "",
            "## 상세 실패 케이스 (상위 50건)",
            "",
            "| 이미지 | 원본 클래스 | 실제 | 예측 | 신뢰도 |",
            "|--------|-----------|------|------|--------|",
        ])
        for fc in failure_cases[:50]:
            lines.append(
                f"| {fc['image']} | {fc['original_class']} | "
                f"{fc['true_label']} | {fc['predicted']} | {fc['confidence']:.4f} |"
            )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info(f"실패 케이스 로그 저장: {output_path}")


def generate_accuracy_report(results: list[dict], output_path: Path | None = None) -> None:
    """정확도 리포트 마크다운 생성."""
    output_path = output_path or DOCS_DIR / "accuracy_report.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    from datetime import datetime
    lines = [
        "# 모델 정확도 리포트",
        "",
        f"**평가 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
    ]

    for result in results:
        if not result:
            continue
        lines.extend([
            f"## {result['model']}",
            "",
            f"- **데이터셋**: {result['dataset']}",
            f"- **테스트 샘플 수**: {result['num_samples']}",
            f"- **Accuracy**: {result['accuracy']:.4f}",
            f"- **F1 (weighted)**: {result['f1_weighted']:.4f}",
            "",
        ])

        if "per_class" in result and result["per_class"]:
            lines.extend([
                "### 클래스별 성능",
                "",
                "| 클래스 | Precision | Recall | F1 | Support |",
                "|--------|-----------|--------|-----|---------|",
            ])
            for cls_name, metrics in result["per_class"].items():
                lines.append(
                    f"| {cls_name} | {metrics['precision']:.4f} | "
                    f"{metrics['recall']:.4f} | {metrics['f1']:.4f} | "
                    f"{metrics['support']} |"
                )
            lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    json_path = output_path.with_suffix(".json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    logger.info(f"정확도 리포트 저장: {output_path}")
    logger.info(f"JSON 결과 저장: {json_path}")


def main() -> None:
    """전체 모델 평가 실행."""
    setup_logging()
    set_seed()
    logger.info("=== 모델 평가 시작 ===")

    results = []
    results.append(evaluate_disease_model())
    results.append(evaluate_finetuned_model())
    results.append(evaluate_species_model())

    plantdoc_result = evaluate_on_plantdoc()
    if plantdoc_result:
        results.append(plantdoc_result)
        failure_cases = plantdoc_result.pop("failure_cases", [])
        generate_failure_log(failure_cases)

    generate_accuracy_report(results)
    logger.info("=== 모델 평가 완료 ===")


if __name__ == "__main__":
    main()
