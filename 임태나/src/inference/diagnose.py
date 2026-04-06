"""진단 파이프라인 — 종 식별 + 병변 분류 + SAM 세그멘테이션.

잎 사진 → 종 식별 + 질병 분류 + 병변 면적 비율 + 오버레이 이미지.
"""

import base64
import io
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
import requests
import torch
from loguru import logger
from PIL import Image

from src.config import (
    CLAHE_CLIP_LIMIT,
    CLAHE_TILE_GRID_SIZE,
    CONFIDENCE_HIGH,
    CONFIDENCE_MEDIUM,
    DISEASE_MODEL_DIR,
    DISEASE_SEVERITY_THRESHOLDS,
    IMAGE_SIZE,
    IMAGENET_MEAN,
    IMAGENET_STD,
    MODELS_DIR,
    OVERLAY_ALPHA,
    OVERLAY_COLOR,
    SAM_CHECKPOINT_PATH,
    SAM_CHECKPOINT_URL,
    SAM_MASK_RATIO_MAX,
    SAM_MASK_RATIO_MIN,
    SAM_MIN_COMPONENT_RATIO,
    SAM_MODEL_TYPE,
    SAM_MORPH_CLOSE_ITER,
    SAM_MORPH_KERNEL_SIZE,
    SAM_MORPH_OPEN_ITER,
    SAM_NEGATIVE_MARGIN,
    SEVERITY_THRESHOLDS,
    SPECIES_DISEASE_BLACKLIST,
    SPECIES_MODEL_DIR,
    get_device,
)
from src.data.preprocess import apply_clahe
from src.models.disease_classifier import create_convnext_tiny, create_efficientnet_b3


# ── 결과 데이터 클래스 ────────────────────────────────────────


@dataclass
class SpeciesResult:
    name: str
    confidence: float


@dataclass
class DiseaseResult:
    name: str
    confidence: float
    korean_name: str = ""


@dataclass
class LesionResult:
    ratio: float
    severity: str
    mask: np.ndarray | None = field(default=None, repr=False)
    overlay_image_base64: str = ""
    segmentation_quality: str = "양호"


@dataclass
class DiagnosisResult:
    species: SpeciesResult
    disease: DiseaseResult
    disease_alternatives: list[DiseaseResult] = field(default_factory=list)
    confidence_level: str = "높음"
    lesion: LesionResult = field(default_factory=lambda: LesionResult(0.0, "초기"))
    preprocessing: dict = field(default_factory=dict)


# ── SAM ───────────────────────────────────────────────────────


def download_sam_checkpoint(checkpoint_path: Path = SAM_CHECKPOINT_PATH) -> Path:
    """SAM 체크포인트가 없으면 다운로드."""
    if checkpoint_path.exists():
        return checkpoint_path

    logger.info(f"SAM 체크포인트 다운로드 중: {SAM_CHECKPOINT_URL}")
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(SAM_CHECKPOINT_URL, stream=True, timeout=300)
    resp.raise_for_status()

    with open(checkpoint_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

    logger.info(f"SAM 다운로드 완료: {checkpoint_path}")
    return checkpoint_path


def load_sam_model(device: torch.device | None = None):
    """SAM 모델 로드. (SamPredictor, device) 반환."""
    from segment_anything import SamPredictor, sam_model_registry

    device = device or get_device()
    download_sam_checkpoint()
    sam = sam_model_registry[SAM_MODEL_TYPE](checkpoint=str(SAM_CHECKPOINT_PATH))
    sam = sam.to(device)
    logger.info(f"SAM 로드 완료: {SAM_MODEL_TYPE}")
    return SamPredictor(sam), device


def _generate_grid_points(h: int, w: int, grid_size: int = 3) -> np.ndarray:
    """그리드 기반 다중 포인트 생성 (잎 전체를 커버)."""
    margin_y, margin_w = h // (grid_size + 1), w // (grid_size + 1)
    points = []
    for i in range(1, grid_size + 1):
        for j in range(1, grid_size + 1):
            points.append([j * margin_w, i * margin_y])
    return np.array(points)


def _generate_negative_points(h: int, w: int, margin: int = SAM_NEGATIVE_MARGIN) -> np.ndarray:
    """이미지 모서리 4곳에 negative(배경) 포인트 생성."""
    return np.array([
        [margin, margin],
        [w - margin, margin],
        [margin, h - margin],
        [w - margin, h - margin],
    ])


def _postprocess_mask(mask: np.ndarray) -> np.ndarray:
    """morphological 후처리로 마스크 노이즈 제거 + 구멍 메우기.

    1) opening: 작은 노이즈 영역 제거
    2) closing: 마스크 내부 구멍 메우기
    3) 작은 연결 성분 제거 (전체 마스크 대비 1% 미만)
    """
    mask_uint8 = mask.astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (SAM_MORPH_KERNEL_SIZE, SAM_MORPH_KERNEL_SIZE),
    )

    # opening → closing
    cleaned = cv2.morphologyEx(mask_uint8, cv2.MORPH_OPEN, kernel, iterations=SAM_MORPH_OPEN_ITER)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_CLOSE, kernel, iterations=SAM_MORPH_CLOSE_ITER)

    # 작은 연결 성분 제거
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(cleaned, connectivity=8)
    total_mask_pixels = np.sum(cleaned > 0)
    if total_mask_pixels == 0:
        return mask  # 후처리로 전부 사라지면 원본 반환

    min_pixels = total_mask_pixels * SAM_MIN_COMPONENT_RATIO
    result = np.zeros_like(cleaned)
    for i in range(1, num_labels):  # 0은 배경
        if stats[i, cv2.CC_STAT_AREA] >= min_pixels:
            result[labels == i] = 255

    return result > 0


def _select_best_mask(
    masks: np.ndarray, scores: np.ndarray,
) -> tuple[np.ndarray, float]:
    """면적 비율 범위 내에서 최고 점수 마스크 선택."""
    best_idx = -1
    best_score = -1.0
    for i, (m, s) in enumerate(zip(masks, scores)):
        ratio = np.sum(m) / m.size
        if SAM_MASK_RATIO_MIN <= ratio <= SAM_MASK_RATIO_MAX and s > best_score:
            best_idx = i
            best_score = float(s)

    if best_idx >= 0:
        return masks[best_idx], best_score
    # 범위 밖이면 최고 점수 마스크 반환
    idx = int(np.argmax(scores))
    return masks[idx], float(scores[idx])


def _segment_leaf(predictor, image_rgb: np.ndarray) -> np.ndarray:
    """SAM으로 잎 전체 영역 세그멘테이션 (가장 큰 마스크).

    중앙점(positive) + 모서리 4개(negative)로 잎/배경 분리.
    """
    h, w = image_rgb.shape[:2]
    center = np.array([[w // 2, h // 2]])
    corners = _generate_negative_points(h, w)
    point_coords = np.vstack([center, corners])
    point_labels = np.array([1, 0, 0, 0, 0], dtype=int)

    masks, scores, _ = predictor.predict(
        point_coords=point_coords,
        point_labels=point_labels,
        multimask_output=True,
    )
    # 가장 큰 유효 마스크 선택 (잎 전체)
    best_idx = int(np.argmax([np.sum(m) for m in masks]))
    return masks[best_idx]


def _is_green_leaf(image_rgb: np.ndarray, leaf_mask: np.ndarray) -> bool:
    """잎이 녹색 계열인지 판별 (HSV H채널 중앙값 기준)."""
    hsv = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2HSV)
    h_values = hsv[:, :, 0][leaf_mask]
    if h_values.size == 0:
        return True
    median_h = float(np.median(h_values))
    return 35 <= median_h <= 85


def _is_variegated_leaf(
    image_rgb: np.ndarray, leaf_mask: np.ndarray, lab: np.ndarray | None = None,
) -> bool:
    """무늬 식물 여부 판별 (잎 내 색상 분산이 큰 경우)."""
    if lab is None:
        lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB)
    a_values = lab[:, :, 1][leaf_mask]
    b_values = lab[:, :, 2][leaf_mask]
    if a_values.size == 0:
        return False
    return float(np.std(a_values)) > 20.0 or float(np.std(b_values)) > 20.0


def _detect_lesion_by_texture(image_rgb: np.ndarray, leaf_mask: np.ndarray) -> np.ndarray:
    """텍스처 기반 병변 검출 (비녹색 잎용).

    Laplacian + Gaussian 필터로 질감 이상 영역 검출.
    """
    gray = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2GRAY)
    # Laplacian으로 질감 변화 감지
    laplacian = cv2.Laplacian(gray, cv2.CV_64F)
    abs_lap = np.abs(laplacian)

    # 잎 영역 내 통계
    leaf_lap = abs_lap[leaf_mask]
    if leaf_lap.size == 0:
        return np.zeros(image_rgb.shape[:2], dtype=bool)

    mean_lap = float(np.mean(leaf_lap))
    std_lap = float(np.std(leaf_lap))

    # 질감 이상치: mean + 2*std 초과 영역
    abnormal = abs_lap > (mean_lap + 2.0 * max(std_lap, 3.0))
    return abnormal & leaf_mask


def _detect_lesion_by_color(image_rgb: np.ndarray, leaf_mask: np.ndarray) -> np.ndarray:
    """잎 영역 내에서 색상/텍스처 이상 부분을 병변으로 검출.

    녹색 잎: LAB 색공간 이상치 검출.
    비녹색/무늬 잎: 텍스처 기반 검출로 전환.
    """
    lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB)

    # 비녹색 또는 무늬 식물이면 텍스처 기반으로 전환
    if not _is_green_leaf(image_rgb, leaf_mask) or _is_variegated_leaf(image_rgb, leaf_mask, lab):
        logger.debug("비녹색/무늬 잎 감지 → 텍스처 기반 병변 검출")
        return _detect_lesion_by_texture(image_rgb, leaf_mask)

    _, a_ch, b_ch = cv2.split(lab)

    # 잎 영역 내 a/b 채널 통계
    leaf_a = a_ch[leaf_mask]
    leaf_b = b_ch[leaf_mask]

    if leaf_a.size == 0:
        return np.zeros(image_rgb.shape[:2], dtype=bool)

    a_mean, a_std = float(np.mean(leaf_a)), float(np.std(leaf_a))
    b_mean, b_std = float(np.mean(leaf_b)), float(np.std(leaf_b))

    # mean ± 1.5*std 밖의 영역을 이상치(병변 후보)로 판정
    threshold = 1.5
    abnormal_a = np.abs(a_ch.astype(float) - a_mean) > (threshold * max(a_std, 5.0))
    abnormal_b = np.abs(b_ch.astype(float) - b_mean) > (threshold * max(b_std, 5.0))

    lesion_color = (abnormal_a | abnormal_b) & leaf_mask
    return lesion_color


def segment_lesion(
    predictor, image_rgb: np.ndarray, point_coords: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """SAM 2단계 세그멘테이션. (병변 마스크, 잎 마스크) 반환."""
    predictor.set_image(image_rgb)
    h, w = image_rgb.shape[:2]

    # ── 1단계: 잎 전체 영역 세그멘테이션 ──
    leaf_mask = _segment_leaf(predictor, image_rgb)
    leaf_mask = _postprocess_mask(leaf_mask)

    # ── 2단계: 잎 내부에서 병변 검출 ──
    if point_coords is not None:
        # 사용자 지정 포인트가 있으면 해당 포인트 + negative로 직접 세그멘테이션
        corners = _generate_negative_points(h, w)
        all_coords = np.vstack([point_coords, corners])
        pos_labels = np.ones(len(point_coords), dtype=int)
        neg_labels = np.zeros(len(corners), dtype=int)
        all_labels = np.concatenate([pos_labels, neg_labels])

        masks, scores, _ = predictor.predict(
            point_coords=all_coords,
            point_labels=all_labels,
            multimask_output=True,
        )
        raw_mask, _ = _select_best_mask(masks, scores)
        # 잎 영역으로 클리핑
        lesion_mask = raw_mask & leaf_mask
    else:
        # 자동 모드: 포인트 프롬프트 + 색상 분석 결합
        center = np.array([[w // 2, h // 2]])
        grid = _generate_grid_points(h, w, grid_size=3)
        corners = _generate_negative_points(h, w)
        all_coords = np.vstack([center, grid, corners])
        pos_labels = np.ones(len(center) + len(grid), dtype=int)
        neg_labels = np.zeros(len(corners), dtype=int)
        all_labels = np.concatenate([pos_labels, neg_labels])

        masks, scores, _ = predictor.predict(
            point_coords=all_coords,
            point_labels=all_labels,
            multimask_output=True,
        )
        sam_mask, _ = _select_best_mask(masks, scores)
        sam_mask = sam_mask & leaf_mask  # 잎 영역으로 클리핑

        # 색상 기반 병변 검출
        color_mask = _detect_lesion_by_color(image_rgb, leaf_mask)

        # SAM 마스크와 색상 마스크의 교집합 (둘 다 병변으로 판단한 영역)
        # 교집합이 너무 작으면 색상 마스크 단독 사용
        intersection = sam_mask & color_mask
        intersection_ratio = np.sum(intersection) / max(np.sum(leaf_mask), 1)

        if intersection_ratio >= 0.01:
            lesion_mask = intersection
        elif np.sum(color_mask) > 0:
            lesion_mask = color_mask
        else:
            lesion_mask = sam_mask

    # ── 3단계: 후처리 ──
    lesion_mask = _postprocess_mask(lesion_mask)

    logger.debug(
        f"잎 면적: {np.sum(leaf_mask)}px, "
        f"병변 면적: {np.sum(lesion_mask)}px, "
        f"비율: {np.sum(lesion_mask) / max(np.sum(leaf_mask), 1):.2%}",
    )
    return lesion_mask, leaf_mask


def calculate_lesion_ratio(
    lesion_mask: np.ndarray, leaf_mask: np.ndarray | None = None,
) -> float:
    """병변 면적 비율 (0.0 ~ 1.0).

    leaf_mask가 주어지면 잎 전체 대비 비율, 아니면 이미지 전체 대비.
    """
    if leaf_mask is not None:
        leaf_pixels = int(np.sum(leaf_mask))
        if leaf_pixels == 0:
            return 0.0
        return int(np.sum(lesion_mask)) / leaf_pixels
    if lesion_mask.size == 0:
        return 0.0
    return int(np.sum(lesion_mask)) / lesion_mask.size


def classify_severity(ratio: float, disease_name: str = "") -> str:
    """면적 비율 → 심각도 ("초기", "중기", "후기").

    질병별 테이블이 있으면 해당 임계값 사용, 없으면 기본값.
    """
    thresholds = DISEASE_SEVERITY_THRESHOLDS.get(disease_name, SEVERITY_THRESHOLDS)
    for severity, (low, high) in thresholds.items():
        if low <= ratio < high:
            return severity
    return "후기"


def assess_segmentation_quality(
    lesion_mask: np.ndarray, leaf_mask: np.ndarray, image_rgb: np.ndarray,
) -> str:
    """세그멘테이션 자가 검증. "양호" / "보통" / "낮음" 반환.

    검증 지표:
    1) 잎 마스크 커버리지: 이미지의 10% 미만이면 잎 세그멘테이션 실패 의심
    2) 마스크 compactness: 4π×면적/둘레² — 극단적으로 낮으면 비정상 형태
    3) 병변 색상 일관성: 병변 내부 색상 분산 vs 잎 전체 분산
    """
    issues = 0

    # 1) 잎 마스크 커버리지
    leaf_ratio = np.sum(leaf_mask) / leaf_mask.size
    if leaf_ratio < 0.10:
        logger.warning(f"잎 마스크 커버리지 낮음: {leaf_ratio:.1%}")
        issues += 1

    # 2) 병변 마스크 compactness
    lesion_pixels = int(np.sum(lesion_mask))
    if lesion_pixels > 0:
        mask_uint8 = lesion_mask.astype(np.uint8) * 255
        contours, _ = cv2.findContours(mask_uint8, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
            total_perimeter = sum(cv2.arcLength(c, True) for c in contours)
            if total_perimeter > 0:
                compactness = (4 * np.pi * lesion_pixels) / (total_perimeter ** 2)
                if compactness < 0.05:
                    logger.warning(f"마스크 compactness 낮음: {compactness:.3f}")
                    issues += 1

    # 3) 병변 내 색상 일관성 (LAB a채널 분산 비교)
    if lesion_pixels > 100:
        lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB)
        a_ch = lab[:, :, 1]
        lesion_std = float(np.std(a_ch[lesion_mask]))
        leaf_std = float(np.std(a_ch[leaf_mask])) if np.sum(leaf_mask) > 0 else 0.0
        # 병변 내부 분산이 잎 전체보다 크면 비정상
        if leaf_std > 0 and lesion_std > leaf_std * 1.5:
            logger.warning(f"병변 색상 불균일: lesion_std={lesion_std:.1f} > leaf_std={leaf_std:.1f}")
            issues += 1

    if issues >= 2:
        return "낮음"
    if issues == 1:
        return "보통"
    return "양호"


def create_overlay(
    image_rgb: np.ndarray, mask: np.ndarray,
    color: tuple[int, int, int] = OVERLAY_COLOR, alpha: float = OVERLAY_ALPHA,
) -> np.ndarray:
    """원본 위에 병변 마스크 반투명 오버레이."""
    overlay = image_rgb.copy()
    color_layer = np.zeros_like(image_rgb)
    color_layer[mask] = color
    overlay[mask] = cv2.addWeighted(
        image_rgb[mask].reshape(-1, 3), 1 - alpha,
        color_layer[mask].reshape(-1, 3), alpha, 0,
    ).reshape(-1, 3)
    return overlay


def image_to_base64(image_rgb: np.ndarray) -> str:
    """RGB 이미지를 base64 PNG 문자열로 변환."""
    buf = io.BytesIO()
    Image.fromarray(image_rgb).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ── 분류 전처리 상수 텐서 ─────────────────────────────────────
_IMAGENET_MEAN_T = torch.tensor(IMAGENET_MEAN).view(3, 1, 1)
_IMAGENET_STD_T = torch.tensor(IMAGENET_STD).view(3, 1, 1)


# ── 분류 모델 로드 ────────────────────────────────────────────


def _load_checkpoint_model(
    checkpoint_path: Path, device: torch.device,
) -> tuple[torch.nn.Module, dict[int, str]]:
    """체크포인트에서 모델+매핑 로드."""
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
    return model, idx_to_class


def _preprocess_for_classification(image_rgb: np.ndarray) -> torch.Tensor:
    """분류용 전처리: CLAHE → 리사이즈 → 텐서 → 정규화."""
    bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    bgr = apply_clahe(bgr, CLAHE_CLIP_LIMIT, CLAHE_TILE_GRID_SIZE)
    bgr = cv2.resize(bgr, (IMAGE_SIZE, IMAGE_SIZE))
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

    t = torch.from_numpy(rgb).float().permute(2, 0, 1) / 255.0
    return ((t - _IMAGENET_MEAN_T) / _IMAGENET_STD_T).unsqueeze(0)


def _get_tta_augmentations(tensor: torch.Tensor) -> list[torch.Tensor]:
    """TTA 3가지 변환 반환: 원본 + 좌우반전 + 밝기변화."""
    return [
        tensor,
        torch.flip(tensor, dims=[-1]),
        torch.clamp(tensor * 1.3, 0.0, 1.0),
    ]


def _classify_with_tta(
    model, tensor, idx_to_class, device, top_k: int = 1,
) -> list[tuple[str, float]]:
    """TTA 추론: 3가지 변환 평균 → top-k (클래스명, 신뢰도) 리스트.

    원본 + 좌우반전 + 90도 회전의 소프트맥스 평균.
    학습 평가와 동일한 3가지 변환만 사용하여 분포 일관성 유지.
    """
    probs = []
    with torch.no_grad():
        for t in _get_tta_augmentations(tensor):
            out = model(t.to(device))
            probs.append(torch.softmax(out, dim=1))
    avg_prob = torch.stack(probs).mean(dim=0)
    values, indices = avg_prob.topk(min(top_k, avg_prob.size(1)), dim=1)
    return [
        (idx_to_class[indices[0, i].item()], round(values[0, i].item(), 4))
        for i in range(values.size(1))
    ]


# ── 파이프라인 ────────────────────────────────────────────────


def _classify_confidence_level(confidence: float) -> str:
    """신뢰도 → 등급 ("높음" / "보통" / "낮음")."""
    if confidence >= CONFIDENCE_HIGH:
        return "높음"
    if confidence >= CONFIDENCE_MEDIUM:
        return "보통"
    return "낮음"


def _validate_species_disease(
    species_name: str, disease_name: str,
    disease_alternatives: list[tuple[str, float]],
) -> tuple[str, float, bool]:
    """종-질병 호환성 검증. 비호환이면 2순위로 교체 시도.

    Returns:
        (최종 질병명, 최종 신뢰도, 호환 여부).
    """
    # 종 이름에서 블랙리스트 키 매칭 (부분 매칭)
    blacklist: set[str] = set()
    for key, diseases in SPECIES_DISEASE_BLACKLIST.items():
        if key.lower() in species_name.lower():
            blacklist = diseases
            break

    if not blacklist or disease_name not in blacklist:
        return disease_name, disease_alternatives[0][1] if disease_alternatives else 0.0, True

    # 비호환 → 대안에서 호환되는 것 찾기
    for alt_name, alt_conf in disease_alternatives[1:]:
        if alt_name not in blacklist:
            logger.info(
                f"종-질병 비호환 교정: {species_name} + {disease_name} → {alt_name}",
            )
            return alt_name, alt_conf, False

    # 교체 불가 → 원래 결과 유지하되 비호환 플래그
    return disease_name, disease_alternatives[0][1] if disease_alternatives else 0.0, False


def _ensemble_classify(
    models: list[tuple[torch.nn.Module, dict[int, str]]],
    tensor: torch.Tensor,
    device: torch.device,
    top_k: int = 3,
) -> list[tuple[str, float]]:
    """다중 모델 앙상블: TTA softmax 평균의 평균 → top-k."""
    all_probs = []
    idx_to_class = models[0][1]  # 모든 모델의 클래스 매핑이 동일하다고 가정

    for model, _ in models:
        probs = []
        with torch.no_grad():
            for t in _get_tta_augmentations(tensor):
                out = model(t.to(device))
                probs.append(torch.softmax(out, dim=1))
        all_probs.append(torch.stack(probs).mean(dim=0))

    avg_prob = torch.stack(all_probs).mean(dim=0)
    values, indices = avg_prob.topk(min(top_k, avg_prob.size(1)), dim=1)
    return [
        (idx_to_class[indices[0, i].item()], round(values[0, i].item(), 4))
        for i in range(values.size(1))
    ]


class DiagnosisPipeline:
    """모델을 한 번 로드하고 재사용하는 진단 파이프라인."""

    def __init__(self) -> None:
        self.device = get_device()
        self._disease_models: list[tuple[torch.nn.Module, dict[int, str]]] = []
        self._species_model = None
        self._species_idx = None
        self._sam = None

    def _ensure_disease(self) -> None:
        if not self._disease_models:
            # 주 모델 (best_model.pth)
            best_path = DISEASE_MODEL_DIR / "best_model.pth"
            if best_path.exists():
                model, idx = _load_checkpoint_model(best_path, self.device)
                self._disease_models.append((model, idx))

            # 앙상블용 보조 모델 (second_model.pth — 비교 실험의 2등 모델)
            second_path = DISEASE_MODEL_DIR / "second_model.pth"
            if second_path.exists():
                model_b, idx_b = _load_checkpoint_model(second_path, self.device)
                self._disease_models.append((model_b, idx_b))
                logger.info("앙상블 모드: 2개 모델 로드 완료")
            else:
                logger.info("단일 모델 모드: second_model.pth 없음")

    def _ensure_species(self) -> None:
        if self._species_model is None:
            path = SPECIES_MODEL_DIR / "species_model.pth"
            self._species_model, self._species_idx = _load_checkpoint_model(path, self.device)

    def _ensure_sam(self) -> None:
        if self._sam is None:
            self._sam, _ = load_sam_model(device=self.device)

    def diagnose(
        self, image: np.ndarray | str | Path, point_coords: np.ndarray | None = None,
    ) -> DiagnosisResult:
        """전체 진단: 종 식별 + 병변 분류 + SAM 세그멘테이션.

        top-3 질병 후보, 신뢰도 등급, 종-질병 호환성, 세그멘테이션 검증 포함.
        """
        image_rgb, orig_size = self._load_image(image)
        tensor = _preprocess_for_classification(image_rgb)

        # ── 종 식별 ──
        self._ensure_species()
        sp_results = _classify_with_tta(
            self._species_model, tensor, self._species_idx, self.device, top_k=1,
        )
        sp_name, sp_conf = sp_results[0]

        # ── 질병 분류 (앙상블 or 단일) ──
        self._ensure_disease()
        if len(self._disease_models) >= 2:
            ds_results = _ensemble_classify(
                self._disease_models, tensor, self.device, top_k=3,
            )
        else:
            ds_results = _classify_with_tta(
                self._disease_models[0][0], tensor,
                self._disease_models[0][1], self.device, top_k=3,
            )

        ds_name = ds_results[0][0]

        # ── 종-질병 호환성 검증 ──
        ds_name, ds_conf, is_compatible = _validate_species_disease(
            sp_name, ds_name, ds_results,
        )

        # ── 신뢰도 등급 ──
        confidence_level = _classify_confidence_level(ds_conf)
        if not is_compatible:
            # 비호환 교정 시 한 단계 하향
            if confidence_level == "높음":
                confidence_level = "보통"

        # ── SAM 세그멘테이션 ──
        self._ensure_sam()
        mask, leaf_mask = segment_lesion(self._sam, image_rgb, point_coords)
        ratio = calculate_lesion_ratio(mask, leaf_mask)
        severity = classify_severity(ratio, ds_name)
        seg_quality = assess_segmentation_quality(mask, leaf_mask, image_rgb)
        overlay_b64 = image_to_base64(create_overlay(image_rgb, mask))

        # ── 대안 질병 목록 (2순위~3순위) ──
        alternatives = [
            DiseaseResult(name=name, confidence=conf)
            for name, conf in ds_results[1:3]
        ]

        return DiagnosisResult(
            species=SpeciesResult(name=sp_name, confidence=sp_conf),
            disease=DiseaseResult(name=ds_name, confidence=ds_conf),
            disease_alternatives=alternatives,
            confidence_level=confidence_level,
            lesion=LesionResult(
                ratio=round(ratio, 4), severity=severity,
                mask=mask, overlay_image_base64=overlay_b64,
                segmentation_quality=seg_quality,
            ),
            preprocessing={"clahe_applied": True, "original_size": list(orig_size)},
        )

    def _load_image(self, image) -> tuple[np.ndarray, tuple[int, int]]:
        if isinstance(image, (str, Path)):
            pil_img = Image.open(str(image)).convert("RGB")
            rgb = np.array(pil_img)
        else:
            rgb = image
        h, w = rgb.shape[:2]
        return rgb, (w, h)

    def segment_only(
        self, image: np.ndarray | str | Path, point_coords: np.ndarray | None = None,
    ) -> LesionResult:
        """SAM 세그멘테이션만 단독 실행."""
        image_rgb, _ = self._load_image(image)
        self._ensure_sam()
        mask, leaf_mask = segment_lesion(self._sam, image_rgb, point_coords)
        ratio = calculate_lesion_ratio(mask, leaf_mask)
        severity = classify_severity(ratio)
        seg_quality = assess_segmentation_quality(mask, leaf_mask, image_rgb)
        overlay_b64 = image_to_base64(create_overlay(image_rgb, mask))
        logger.info(f"면적: {ratio:.2%}, 심각도: {severity}, 품질: {seg_quality}")
        return LesionResult(
            ratio=round(ratio, 4), severity=severity,
            mask=mask, overlay_image_base64=overlay_b64,
            segmentation_quality=seg_quality,
        )


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        logger.error("사용법: python -m src.inference.diagnose <이미지_경로>")
        sys.exit(1)
    pipeline = DiagnosisPipeline()
    result = pipeline.segment_only(sys.argv[1])
    logger.info(f"면적 비율: {result.ratio:.2%}, 심각도: {result.severity}")
    out_path = Path(sys.argv[1]).with_suffix(".overlay.png")
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(result.overlay_image_base64))
    logger.info(f"오버레이 저장: {out_path}")
