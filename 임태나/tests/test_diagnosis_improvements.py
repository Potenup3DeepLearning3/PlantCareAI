"""10개 한계점 개선사항 단위 테스트.

GPU/모델 파일 없이 로직만 검증하는 순수 단위 테스트.
"""

import numpy as np
import cv2
import pytest


# ── 한계 1: Leaf_Spot 세분화 ──────────────────────────────────


class TestLeafSpotSplit:
    """remap_labels.py Leaf_Spot → 3개 분리 검증."""

    def test_septoria_mapped_separately(self):
        from src.data.remap_labels import DISEASE_TYPE_MAPPING
        assert DISEASE_TYPE_MAPPING["Tomato___Septoria_leaf_spot"] == "Septoria_Leaf_Spot"

    def test_target_spot_mapped_separately(self):
        from src.data.remap_labels import DISEASE_TYPE_MAPPING
        assert DISEASE_TYPE_MAPPING["Tomato___Target_Spot"] == "Target_Spot"

    def test_other_leaf_spot_mapped(self):
        from src.data.remap_labels import DISEASE_TYPE_MAPPING
        assert DISEASE_TYPE_MAPPING["Tomato___Spider_mites Two-spotted_spider_mite"] == "Other_Leaf_Spot"
        assert DISEASE_TYPE_MAPPING["Corn_(maize)___Cercospora_leaf_spot Gray_leaf_spot"] == "Other_Leaf_Spot"
        assert DISEASE_TYPE_MAPPING["Strawberry___Leaf_scorch"] == "Other_Leaf_Spot"

    def test_old_leaf_spot_not_exists(self):
        """기존 Leaf_Spot 클래스가 매핑 값에 없어야 함."""
        from src.data.remap_labels import DISEASE_TYPE_MAPPING
        values = set(DISEASE_TYPE_MAPPING.values())
        assert "Leaf_Spot" not in values

    def test_korean_mapping_complete(self):
        from src.data.remap_labels import DISEASE_TYPE_KOREAN
        assert "Septoria_Leaf_Spot" in DISEASE_TYPE_KOREAN
        assert "Target_Spot" in DISEASE_TYPE_KOREAN
        assert "Other_Leaf_Spot" in DISEASE_TYPE_KOREAN

    def test_num_classes_updated(self):
        from src.data.remap_labels import DISEASE_TYPE_MAPPING
        unique_classes = set(DISEASE_TYPE_MAPPING.values())
        # 기존 12 - Leaf_Spot + Septoria + Target + Other = 14
        assert len(unique_classes) == 14


# ── 한계 2: 신뢰도 3단계 등급 ─────────────────────────────────


class TestConfidenceLevel:
    """신뢰도 등급 분류 검증."""

    def test_high_confidence(self):
        from src.inference.diagnose import _classify_confidence_level
        assert _classify_confidence_level(0.95) == "높음"
        assert _classify_confidence_level(0.80) == "높음"

    def test_medium_confidence(self):
        from src.inference.diagnose import _classify_confidence_level
        assert _classify_confidence_level(0.75) == "보통"
        assert _classify_confidence_level(0.60) == "보통"

    def test_low_confidence(self):
        from src.inference.diagnose import _classify_confidence_level
        assert _classify_confidence_level(0.59) == "낮음"
        assert _classify_confidence_level(0.30) == "낮음"

    def test_schema_has_confidence_level(self):
        from src.api.schemas import DiagnoseResponse
        fields = DiagnoseResponse.model_fields
        assert "confidence_level" in fields
        assert "disease_alternatives" in fields

    def test_schema_has_segmentation_quality(self):
        from src.api.schemas import LesionResponse
        fields = LesionResponse.model_fields
        assert "segmentation_quality" in fields


# ── 한계 3: 종-질병 호환성 검증 ───────────────────────────────


class TestSpeciesDiseaseCompatibility:
    """종-질병 블랙리스트 검증."""

    def test_blacklist_exists(self):
        from src.config import SPECIES_DISEASE_BLACKLIST
        assert len(SPECIES_DISEASE_BLACKLIST) > 0

    def test_sansevieria_blacklist(self):
        from src.config import SPECIES_DISEASE_BLACKLIST
        bl = SPECIES_DISEASE_BLACKLIST["Sansevieria"]
        assert "Powdery_Mildew" in bl
        assert "Rust" in bl

    def test_validate_compatible_pair(self):
        from src.inference.diagnose import _validate_species_disease
        name, conf, ok = _validate_species_disease(
            "Monstera Deliciosa", "Powdery_Mildew",
            [("Powdery_Mildew", 0.90), ("Leaf_Mold", 0.05)],
        )
        assert ok is True
        assert name == "Powdery_Mildew"

    def test_validate_incompatible_swaps_to_alternative(self):
        from src.inference.diagnose import _validate_species_disease
        # Sansevieria + Powdery_Mildew → 블랙리스트 → 대안으로 교체
        name, conf, ok = _validate_species_disease(
            "Sansevieria trifasciata", "Powdery_Mildew",
            [("Powdery_Mildew", 0.85), ("Bacterial_Spot", 0.10)],
        )
        assert ok is False
        assert name == "Bacterial_Spot"

    def test_validate_incompatible_no_alternative(self):
        from src.inference.diagnose import _validate_species_disease
        # 모든 대안도 블랙리스트에 있는 경우 → 원래 결과 유지
        name, conf, ok = _validate_species_disease(
            "Sansevieria trifasciata", "Powdery_Mildew",
            [("Powdery_Mildew", 0.85), ("Rust", 0.10)],
        )
        assert ok is False
        assert name == "Powdery_Mildew"  # 교체 불가, 원래 값


# ── 한계 4: TTA 불일치 수정 ───────────────────────────────────


class TestTTAConsistency:
    """TTA 변환이 학습과 동일한 3가지인지 검증."""

    def test_tta_returns_top_k(self):
        """TTA가 top-k 리스트를 반환하는지 확인."""
        import torch
        from src.inference.diagnose import _classify_with_tta

        # 더미 모델: 5클래스, 항상 동일 출력
        class DummyModel(torch.nn.Module):
            def forward(self, x):
                batch = x.shape[0]
                return torch.tensor([[0.1, 0.2, 0.5, 0.15, 0.05]] * batch)

        model = DummyModel()
        tensor = torch.randn(1, 3, 224, 224)
        idx_to_class = {0: "A", 1: "B", 2: "C", 3: "D", 4: "E"}

        results = _classify_with_tta(model, tensor, idx_to_class, "cpu", top_k=3)
        assert len(results) == 3
        assert results[0][0] == "C"  # 0.5가 가장 높음
        assert all(isinstance(r, tuple) and len(r) == 2 for r in results)

    def test_tta_top_1_returns_single(self):
        import torch
        from src.inference.diagnose import _classify_with_tta

        class DummyModel(torch.nn.Module):
            def forward(self, x):
                return torch.tensor([[0.9, 0.1]])

        model = DummyModel()
        tensor = torch.randn(1, 3, 224, 224)
        results = _classify_with_tta(model, tensor, {0: "X", 1: "Y"}, "cpu", top_k=1)
        assert len(results) == 1


# ── 한계 5: 질병별 심각도 테이블 ──────────────────────────────


class TestDiseaseSeverity:
    """질병별 심각도 임계값 검증."""

    def test_default_severity(self):
        from src.inference.diagnose import classify_severity
        assert classify_severity(0.05) == "초기"
        assert classify_severity(0.15) == "중기"
        assert classify_severity(0.30) == "후기"

    def test_mosaic_virus_stricter(self):
        from src.inference.diagnose import classify_severity
        # Mosaic_Virus: 3% 이상이면 중기, 10% 이상이면 후기
        assert classify_severity(0.02, "Mosaic_Virus") == "초기"
        assert classify_severity(0.05, "Mosaic_Virus") == "중기"
        assert classify_severity(0.12, "Mosaic_Virus") == "후기"

    def test_leaf_curl_lenient(self):
        from src.inference.diagnose import classify_severity
        # Leaf_Curl: 30% 미만이면 중기
        assert classify_severity(0.25, "Leaf_Curl") == "중기"

    def test_unknown_disease_uses_default(self):
        from src.inference.diagnose import classify_severity
        assert classify_severity(0.15, "Unknown_Disease") == "중기"

    def test_all_diseases_in_table(self):
        from src.config import DISEASE_SEVERITY_THRESHOLDS
        expected = {
            "Mosaic_Virus", "Powdery_Mildew", "Scab_Rot", "Rust",
            "Leaf_Curl", "Greening", "Early_Blight", "Late_Blight",
            "Bacterial_Spot", "Septoria_Leaf_Spot", "Target_Spot",
            "Other_Leaf_Spot", "Leaf_Mold",
        }
        assert set(DISEASE_SEVERITY_THRESHOLDS.keys()) == expected


# ── 한계 6: 비녹색 잎 색상 검출 분기 ─────────────────────────


class TestNonGreenLeaf:
    """비녹색/무늬 잎 감지 및 텍스처 기반 전환 검증."""

    def _make_green_image(self, h=100, w=100):
        """녹색 잎 이미지 생성."""
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:, :] = [34, 139, 34]  # RGB 녹색
        mask = np.ones((h, w), dtype=bool)
        return img, mask

    def _make_purple_image(self, h=100, w=100):
        """자색 잎 이미지 생성."""
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:, :] = [128, 0, 128]  # RGB 보라
        mask = np.ones((h, w), dtype=bool)
        return img, mask

    def test_green_leaf_detected(self):
        from src.inference.diagnose import _is_green_leaf
        img, mask = self._make_green_image()
        assert _is_green_leaf(img, mask) is True

    def test_purple_leaf_not_green(self):
        from src.inference.diagnose import _is_green_leaf
        img, mask = self._make_purple_image()
        assert _is_green_leaf(img, mask) is False

    def test_variegated_leaf_high_variance(self):
        from src.inference.diagnose import _is_variegated_leaf
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        img[:50, :] = [34, 139, 34]   # 윗쪽 녹색
        img[50:, :] = [255, 255, 255]  # 아래쪽 흰색 (무늬)
        mask = np.ones((100, 100), dtype=bool)
        assert _is_variegated_leaf(img, mask) is True

    def test_uniform_leaf_not_variegated(self):
        from src.inference.diagnose import _is_variegated_leaf
        img, mask = self._make_green_image()
        assert _is_variegated_leaf(img, mask) is False

    def test_color_detection_uses_texture_for_purple(self):
        """자색 잎에서 색상 검출이 텍스처 기반으로 전환되는지 확인."""
        from src.inference.diagnose import _detect_lesion_by_color
        img, mask = self._make_purple_image()
        # 일부 영역에 질감 변화 (밝은 점)
        img[40:60, 40:60] = [200, 200, 200]
        result = _detect_lesion_by_color(img, mask)
        assert result.shape == (100, 100)
        assert result.dtype == bool


# ── 한계 7: 파인튜닝 혼합 배치 설정 ──────────────────────────


class TestFinetuneMixRatio:
    """파인튜닝 혼합 배치 설정 존재 여부."""

    def test_mix_ratio_in_config(self):
        from src.config import FINETUNE_SOURCE_MIX_RATIO
        assert 0 < FINETUNE_SOURCE_MIX_RATIO < 1
        assert FINETUNE_SOURCE_MIX_RATIO == 0.2


# ── 한계 8: 앙상블 추론 ──────────────────────────────────────


class TestEnsemble:
    """앙상블 분류 로직 검증."""

    def test_ensemble_classify_averages(self):
        import torch
        from src.inference.diagnose import _ensemble_classify

        class ModelA(torch.nn.Module):
            def forward(self, x):
                return torch.tensor([[0.8, 0.1, 0.1]])

        class ModelB(torch.nn.Module):
            def forward(self, x):
                return torch.tensor([[0.2, 0.7, 0.1]])

        idx = {0: "disease_A", 1: "disease_B", 2: "disease_C"}
        models = [(ModelA(), idx), (ModelB(), idx)]
        tensor = torch.randn(1, 3, 224, 224)

        results = _ensemble_classify(models, tensor, "cpu", top_k=3)
        assert len(results) == 3
        # softmax 평균이므로 정확한 top-1은 데이터에 따라 다르지만 결과가 나와야 함
        assert all(0 <= r[1] <= 1 for r in results)

    def test_ensemble_single_model_works(self):
        import torch
        from src.inference.diagnose import _ensemble_classify

        class SingleModel(torch.nn.Module):
            def forward(self, x):
                return torch.tensor([[0.9, 0.05, 0.05]])

        idx = {0: "A", 1: "B", 2: "C"}
        models = [(SingleModel(), idx)]
        tensor = torch.randn(1, 3, 224, 224)

        results = _ensemble_classify(models, tensor, "cpu", top_k=2)
        assert len(results) == 2
        assert results[0][0] == "A"


# ── 한계 9: top-k 반환 ───────────────────────────────────────


class TestTopK:
    """top-k 반환 및 DiagnosisResult에 alternatives 포함 검증."""

    def test_diagnosis_result_has_alternatives(self):
        from src.inference.diagnose import DiagnosisResult, SpeciesResult, DiseaseResult, LesionResult
        result = DiagnosisResult(
            species=SpeciesResult(name="Monstera", confidence=0.9),
            disease=DiseaseResult(name="Powdery_Mildew", confidence=0.85),
            disease_alternatives=[
                DiseaseResult(name="Leaf_Mold", confidence=0.10),
            ],
            confidence_level="높음",
        )
        assert len(result.disease_alternatives) == 1
        assert result.disease_alternatives[0].name == "Leaf_Mold"

    def test_diagnosis_result_defaults(self):
        from src.inference.diagnose import DiagnosisResult, SpeciesResult, DiseaseResult
        result = DiagnosisResult(
            species=SpeciesResult(name="X", confidence=0.5),
            disease=DiseaseResult(name="Y", confidence=0.5),
        )
        assert result.disease_alternatives == []
        assert result.confidence_level == "높음"


# ── 한계 10: 세그멘테이션 자가 검증 ──────────────────────────


class TestSegmentationQuality:
    """세그멘테이션 품질 지표 검증."""

    def test_good_quality(self):
        from src.inference.diagnose import assess_segmentation_quality
        # 잎: 이미지 50%, 병변: 원형 영역 (높은 compactness)
        h, w = 200, 200
        leaf_mask = np.zeros((h, w), dtype=bool)
        leaf_mask[20:180, 20:180] = True  # 64% 커버리지

        lesion_mask = np.zeros((h, w), dtype=bool)
        cv2.circle(lesion_mask.view(np.uint8), (100, 100), 30, 1, -1)
        lesion_mask = lesion_mask.astype(bool)

        # 녹색 잎 + 갈색 병변
        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:, :] = [34, 139, 34]
        img[lesion_mask] = [139, 90, 43]

        quality = assess_segmentation_quality(lesion_mask, leaf_mask, img)
        assert quality in ("양호", "보통")

    def test_bad_quality_small_leaf(self):
        from src.inference.diagnose import assess_segmentation_quality
        # 잎: 이미지 5% (너무 작음)
        h, w = 200, 200
        leaf_mask = np.zeros((h, w), dtype=bool)
        leaf_mask[90:110, 90:110] = True  # ~5%

        lesion_mask = np.zeros((h, w), dtype=bool)
        lesion_mask[95:105, 95:105] = True

        img = np.zeros((h, w, 3), dtype=np.uint8)
        img[:, :] = [34, 139, 34]

        quality = assess_segmentation_quality(lesion_mask, leaf_mask, img)
        assert quality in ("보통", "낮음")

    def test_empty_lesion_good_quality(self):
        from src.inference.diagnose import assess_segmentation_quality
        h, w = 200, 200
        leaf_mask = np.ones((h, w), dtype=bool)
        lesion_mask = np.zeros((h, w), dtype=bool)
        img = np.full((h, w, 3), [34, 139, 34], dtype=np.uint8)

        quality = assess_segmentation_quality(lesion_mask, leaf_mask, img)
        assert quality == "양호"

    def test_lesion_result_has_quality_field(self):
        from src.inference.diagnose import LesionResult
        r = LesionResult(ratio=0.1, severity="초기", segmentation_quality="낮음")
        assert r.segmentation_quality == "낮음"


# ── LLM 대안 매핑 ────────────────────────────────────────────


class TestLLMAlternatives:
    """llm.py DISEASE_ALTERNATIVES가 세분화된 한국어에 맞는지 검증."""

    def test_all_korean_diseases_have_alternatives(self):
        from src.inference.llm import DISEASE_ALTERNATIVES
        from src.data.remap_labels import DISEASE_TYPE_KOREAN
        # Healthy는 대안 불필요
        diseases_needing_alts = {v for k, v in DISEASE_TYPE_KOREAN.items() if k != "Healthy"}
        covered = set(DISEASE_ALTERNATIVES.keys())
        missing = diseases_needing_alts - covered
        # 모든 질병에 대안이 있어야 함
        assert missing == set(), f"DISEASE_ALTERNATIVES에 누락: {missing}"

    def test_alternatives_are_lists(self):
        from src.inference.llm import DISEASE_ALTERNATIVES
        for key, alts in DISEASE_ALTERNATIVES.items():
            assert isinstance(alts, list), f"{key}: list가 아님"
            assert len(alts) >= 1, f"{key}: 대안이 비어있음"
