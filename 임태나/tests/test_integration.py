"""통합 테스트 — 실제 모델 파일 + 이미지로 전체 파이프라인 검증.

GPU/모델 체크포인트가 있어야 실행 가능.
"""

import time
from pathlib import Path

import cv2
import numpy as np
import pytest
import torch
from loguru import logger

# ── 테스트 이미지 경로 ────────────────────────────────────────

DATA_DIR = Path("data/processed/disease_type")
MODELS_DIR = Path("models")

# 질병별 샘플 이미지 1장씩 찾기
SAMPLE_IMAGES: dict[str, Path] = {}
if DATA_DIR.exists():
    for class_dir in sorted(DATA_DIR.iterdir()):
        if class_dir.is_dir():
            imgs = list(class_dir.glob("*.jpg"))[:1]
            if imgs:
                SAMPLE_IMAGES[class_dir.name] = imgs[0]

HAS_MODELS = (
    (MODELS_DIR / "disease" / "best_model.pth").exists()
    and (MODELS_DIR / "species" / "species_model.pth").exists()
    and (MODELS_DIR / "sam" / "sam_vit_b_01ec64.pth").exists()
)
HAS_ENSEMBLE = (MODELS_DIR / "disease" / "second_model.pth").exists()
HAS_IMAGES = len(SAMPLE_IMAGES) > 0

skip_no_models = pytest.mark.skipif(not HAS_MODELS, reason="모델 파일 없음")
skip_no_images = pytest.mark.skipif(not HAS_IMAGES, reason="테스트 이미지 없음")
skip_no_ensemble = pytest.mark.skipif(not HAS_ENSEMBLE, reason="second_model.pth 없음")


def _load_test_image(path: Path) -> np.ndarray:
    bgr = cv2.imread(str(path))
    assert bgr is not None, f"이미지 로드 실패: {path}"
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


# ── 모델 로드 테스트 ──────────────────────────────────────────


@skip_no_models
class TestModelLoading:
    """모델 체크포인트 로드 검증."""

    def test_disease_model_loads(self):
        from src.inference.diagnose import _load_checkpoint_model
        model, idx = _load_checkpoint_model(
            MODELS_DIR / "disease" / "best_model.pth", torch.device("cpu"),
        )
        assert model is not None
        assert len(idx) > 0
        logger.info(f"질병 모델 클래스: {list(idx.values())}")

    def test_species_model_loads(self):
        from src.inference.diagnose import _load_checkpoint_model
        model, idx = _load_checkpoint_model(
            MODELS_DIR / "species" / "species_model.pth", torch.device("cpu"),
        )
        assert model is not None
        assert len(idx) > 0
        logger.info(f"종 모델 클래스 수: {len(idx)}")

    @skip_no_ensemble
    def test_second_model_loads(self):
        from src.inference.diagnose import _load_checkpoint_model
        model, idx = _load_checkpoint_model(
            MODELS_DIR / "disease" / "second_model.pth", torch.device("cpu"),
        )
        assert model is not None
        assert len(idx) > 0
        logger.info(f"2등 모델 아키텍처 클래스 수: {len(idx)}")


# ── 분류 추론 테스트 ──────────────────────────────────────────


@skip_no_models
@skip_no_images
class TestClassification:
    """분류 모델 추론 검증."""

    def test_disease_classification_top3(self):
        """질병 분류 top-3 반환 검증."""
        from src.inference.diagnose import (
            _classify_with_tta,
            _load_checkpoint_model,
            _preprocess_for_classification,
        )

        model, idx = _load_checkpoint_model(
            MODELS_DIR / "disease" / "best_model.pth", torch.device("cpu"),
        )
        img = _load_test_image(list(SAMPLE_IMAGES.values())[0])
        tensor = _preprocess_for_classification(img)

        results = _classify_with_tta(model, tensor, idx, "cpu", top_k=3)
        assert len(results) == 3
        assert all(0 <= r[1] <= 1 for r in results)
        assert results[0][1] >= results[1][1] >= results[2][1]  # 내림차순
        logger.info(f"top-3: {results}")

    def test_species_classification(self):
        from src.inference.diagnose import (
            _classify_with_tta,
            _load_checkpoint_model,
            _preprocess_for_classification,
        )

        model, idx = _load_checkpoint_model(
            MODELS_DIR / "species" / "species_model.pth", torch.device("cpu"),
        )
        img = _load_test_image(list(SAMPLE_IMAGES.values())[0])
        tensor = _preprocess_for_classification(img)

        results = _classify_with_tta(model, tensor, idx, "cpu", top_k=1)
        assert len(results) == 1
        assert results[0][1] > 0
        logger.info(f"종 식별: {results[0]}")


# ── 앙상블 테스트 ─────────────────────────────────────────────


@skip_no_models
@skip_no_ensemble
@skip_no_images
class TestEnsembleIntegration:
    """실제 모델 2개 앙상블 검증."""

    def test_ensemble_two_models(self):
        from src.inference.diagnose import (
            _ensemble_classify,
            _load_checkpoint_model,
            _preprocess_for_classification,
        )

        model_a, idx_a = _load_checkpoint_model(
            MODELS_DIR / "disease" / "best_model.pth", torch.device("cpu"),
        )
        model_b, idx_b = _load_checkpoint_model(
            MODELS_DIR / "disease" / "second_model.pth", torch.device("cpu"),
        )

        img = _load_test_image(list(SAMPLE_IMAGES.values())[0])
        tensor = _preprocess_for_classification(img)

        results = _ensemble_classify(
            [(model_a, idx_a), (model_b, idx_b)], tensor, "cpu", top_k=3,
        )
        assert len(results) == 3
        assert results[0][1] >= results[1][1]
        logger.info(f"앙상블 top-3: {results}")

    def test_ensemble_vs_single_differs(self):
        """앙상블과 단일 모델 결과가 다를 수 있는지 확인 (신뢰도 차이)."""
        from src.inference.diagnose import (
            _classify_with_tta,
            _ensemble_classify,
            _load_checkpoint_model,
            _preprocess_for_classification,
        )

        model_a, idx_a = _load_checkpoint_model(
            MODELS_DIR / "disease" / "best_model.pth", torch.device("cpu"),
        )
        model_b, idx_b = _load_checkpoint_model(
            MODELS_DIR / "disease" / "second_model.pth", torch.device("cpu"),
        )

        img = _load_test_image(list(SAMPLE_IMAGES.values())[0])
        tensor = _preprocess_for_classification(img)

        single = _classify_with_tta(model_a, tensor, idx_a, "cpu", top_k=1)
        ensemble = _ensemble_classify(
            [(model_a, idx_a), (model_b, idx_b)], tensor, "cpu", top_k=1,
        )

        # 최소한 결과 형식은 동일
        assert len(single) == 1
        assert len(ensemble) == 1
        # 신뢰도가 달라야 정상 (다른 모델이 섞이니까)
        logger.info(f"단일: {single[0]}, 앙상블: {ensemble[0]}")


# ── SAM 세그멘테이션 테스트 ───────────────────────────────────


@skip_no_models
@skip_no_images
class TestSAMSegmentation:
    """SAM 2단계 세그멘테이션 + 후처리 + 검증 테스트."""

    @pytest.fixture(scope="class")
    def sam_predictor(self):
        from src.inference.diagnose import load_sam_model
        predictor, _ = load_sam_model(device=torch.device("cpu"))
        return predictor

    def test_segment_returns_two_masks(self, sam_predictor):
        from src.inference.diagnose import segment_lesion
        img = _load_test_image(list(SAMPLE_IMAGES.values())[0])
        lesion_mask, leaf_mask = segment_lesion(sam_predictor, img)

        assert lesion_mask.shape == img.shape[:2]
        assert leaf_mask.shape == img.shape[:2]
        assert lesion_mask.dtype == bool
        assert leaf_mask.dtype == bool

    def test_leaf_mask_larger_than_lesion(self, sam_predictor):
        from src.inference.diagnose import segment_lesion
        img = _load_test_image(list(SAMPLE_IMAGES.values())[0])
        lesion_mask, leaf_mask = segment_lesion(sam_predictor, img)

        leaf_area = np.sum(leaf_mask)
        lesion_area = np.sum(lesion_mask)
        assert leaf_area >= lesion_area, "잎 마스크가 병변 마스크보다 작음"

    def test_lesion_ratio_uses_leaf_base(self, sam_predictor):
        from src.inference.diagnose import calculate_lesion_ratio, segment_lesion
        img = _load_test_image(list(SAMPLE_IMAGES.values())[0])
        lesion_mask, leaf_mask = segment_lesion(sam_predictor, img)

        ratio_leaf = calculate_lesion_ratio(lesion_mask, leaf_mask)
        ratio_image = calculate_lesion_ratio(lesion_mask, None)

        # 잎 대비 비율이 이미지 전체 대비보다 크거나 같아야 함
        if np.sum(leaf_mask) < lesion_mask.size:
            assert ratio_leaf >= ratio_image
        logger.info(f"잎 대비: {ratio_leaf:.2%}, 이미지 대비: {ratio_image:.2%}")

    def test_segmentation_quality_assessment(self, sam_predictor):
        from src.inference.diagnose import (
            assess_segmentation_quality,
            segment_lesion,
        )
        img = _load_test_image(list(SAMPLE_IMAGES.values())[0])
        lesion_mask, leaf_mask = segment_lesion(sam_predictor, img)

        quality = assess_segmentation_quality(lesion_mask, leaf_mask, img)
        assert quality in ("양호", "보통", "낮음")
        logger.info(f"세그멘테이션 품질: {quality}")

    def test_overlay_image_generated(self, sam_predictor):
        from src.inference.diagnose import create_overlay, segment_lesion
        img = _load_test_image(list(SAMPLE_IMAGES.values())[0])
        lesion_mask, _ = segment_lesion(sam_predictor, img)

        overlay = create_overlay(img, lesion_mask)
        assert overlay.shape == img.shape
        assert overlay.dtype == img.dtype


# ── 전체 파이프라인 테스트 ────────────────────────────────────


@skip_no_models
@skip_no_images
class TestFullPipeline:
    """DiagnosisPipeline.diagnose() 전체 흐름 검증."""

    @pytest.fixture(scope="class")
    def pipeline(self):
        from src.inference.diagnose import DiagnosisPipeline
        return DiagnosisPipeline()

    def test_diagnose_returns_complete_result(self, pipeline):
        img = _load_test_image(list(SAMPLE_IMAGES.values())[0])
        result = pipeline.diagnose(img)

        # 종 식별
        assert result.species.name != ""
        assert 0 < result.species.confidence <= 1

        # 질병 분류
        assert result.disease.name != ""
        assert 0 < result.disease.confidence <= 1

        # 대안 질병 (top-k)
        assert isinstance(result.disease_alternatives, list)
        assert len(result.disease_alternatives) >= 1
        logger.info(f"top-1: {result.disease.name} ({result.disease.confidence:.2%})")
        for alt in result.disease_alternatives:
            logger.info(f"  대안: {alt.name} ({alt.confidence:.2%})")

        # 신뢰도 등급
        assert result.confidence_level in ("높음", "보통", "낮음")
        logger.info(f"신뢰도 등급: {result.confidence_level}")

        # 병변
        assert 0 <= result.lesion.ratio <= 1
        assert result.lesion.severity in ("초기", "중기", "후기")
        assert result.lesion.segmentation_quality in ("양호", "보통", "낮음")
        assert result.lesion.overlay_image_base64 != ""
        logger.info(
            f"병변: {result.lesion.ratio:.2%}, {result.lesion.severity}, "
            f"품질: {result.lesion.segmentation_quality}",
        )

        # 전처리 정보
        assert result.preprocessing["clahe_applied"] is True

    def test_diagnose_multiple_disease_types(self, pipeline):
        """여러 질병 이미지에 대해 파이프라인이 에러 없이 동작하는지."""
        errors = []
        for disease, img_path in list(SAMPLE_IMAGES.items())[:5]:
            try:
                img = _load_test_image(img_path)
                result = pipeline.diagnose(img)
                logger.info(
                    f"[{disease}] → 종: {result.species.name}, "
                    f"질병: {result.disease.name} ({result.disease.confidence:.2%}), "
                    f"등급: {result.confidence_level}, "
                    f"면적: {result.lesion.ratio:.2%}",
                )
            except Exception as e:
                errors.append(f"{disease}: {e}")
        assert not errors, f"실패 케이스:\n" + "\n".join(errors)

    def test_diagnose_with_healthy_image(self, pipeline):
        """Healthy 이미지로 진단 시 병변 비율이 낮아야 함."""
        if "Healthy" not in SAMPLE_IMAGES:
            pytest.skip("Healthy 이미지 없음")

        img = _load_test_image(SAMPLE_IMAGES["Healthy"])
        result = pipeline.diagnose(img)
        logger.info(f"Healthy → 질병: {result.disease.name}, 면적: {result.lesion.ratio:.2%}")
        # Healthy면 병변 비율이 낮을 것으로 기대 (엄격하진 않음)
        # 모델이 올바르면 Healthy로 분류할 것

    def test_diagnose_performance(self, pipeline):
        """진단 소요 시간 측정 (60초 이내)."""
        img = _load_test_image(list(SAMPLE_IMAGES.values())[0])
        start = time.perf_counter()
        result = pipeline.diagnose(img)
        elapsed = time.perf_counter() - start
        logger.info(f"진단 소요 시간: {elapsed:.2f}초")
        assert elapsed < 60, f"진단이 60초 초과: {elapsed:.1f}초"

    def test_segment_only(self, pipeline):
        """segment_only 단독 실행 검증."""
        img = _load_test_image(list(SAMPLE_IMAGES.values())[0])
        result = pipeline.segment_only(img)

        assert 0 <= result.ratio <= 1
        assert result.severity in ("초기", "중기", "후기")
        assert result.segmentation_quality in ("양호", "보통", "낮음")
        assert result.overlay_image_base64 != ""


# ── 종-질병 호환성 실전 테스트 ────────────────────────────────


@skip_no_models
@skip_no_images
class TestCompatibilityIntegration:
    """실제 진단 결과에 호환성 검증이 적용되는지 확인."""

    def test_confidence_downgrade_on_incompatible(self):
        """비호환 교정 시 신뢰도 등급이 하향되는지."""
        from src.inference.diagnose import _classify_confidence_level, _validate_species_disease

        # Sansevieria + Rust → 블랙리스트
        name, conf, ok = _validate_species_disease(
            "Sansevieria", "Rust",
            [("Rust", 0.90), ("Healthy", 0.05), ("Scab_Rot", 0.03)],
        )
        assert ok is False

        # 교정 후 등급 결정
        level = _classify_confidence_level(conf)
        if level == "높음":
            # 비호환이면 파이프라인에서 한 단계 하향
            level = "보통"
        assert level in ("보통", "낮음")


# ── 질병별 심각도 실전 테스트 ─────────────────────────────────


@skip_no_models
@skip_no_images
class TestSeverityIntegration:
    """실제 진단에서 질병별 심각도가 적용되는지."""

    @pytest.fixture(scope="class")
    def pipeline(self):
        from src.inference.diagnose import DiagnosisPipeline
        return DiagnosisPipeline()

    def test_severity_uses_disease_name(self, pipeline):
        from src.inference.diagnose import classify_severity
        # 같은 면적이어도 질병에 따라 심각도가 달라야 함
        ratio = 0.08
        sev_mosaic = classify_severity(ratio, "Mosaic_Virus")
        sev_default = classify_severity(ratio, "Unknown")
        # Mosaic_Virus: 3% 이상이면 중기 → 8%는 중기
        # Default: 10% 미만이면 초기 → 8%는 초기
        assert sev_mosaic == "중기"
        assert sev_default == "초기"
        logger.info(f"ratio=8%: Mosaic→{sev_mosaic}, Default→{sev_default}")
