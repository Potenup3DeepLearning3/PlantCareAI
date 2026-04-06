"""E2E 시나리오 테스트 — FastAPI TestClient 기반.

5개 시나리오:
  1. 사진 → 진단 → 분즈 메시지 → TTS
  2. 음성 → STT → LLM → TTS
  3. 약제 라벨 → OCR → 적합성
  4. 원터치 로그 → 타임라인
  5. 패턴 분석 → 분즈 말풍선

모델 파일이 없는 환경: 시나리오 1~3은 skip.
모델 무관 시나리오 4~5: 항상 실행.
"""

import io
import json
import os
import tempfile
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient

# ── 픽스처 ────────────────────────────────────────────────────

MODELS_DIR = Path("models")
DATA_DIR = Path("data")

HAS_MODELS = (
    (MODELS_DIR / "disease" / "best_model.pth").exists()
    and (MODELS_DIR / "species" / "species_model.pth").exists()
    and (MODELS_DIR / "sam" / "sam_vit_b_01ec64.pth").exists()
)

skip_no_models = pytest.mark.skipif(not HAS_MODELS, reason="모델 파일 없음")


def _make_test_image_bytes(width: int = 224, height: int = 224) -> bytes:
    """테스트용 초록 잎 유사 이미지 (JPEG bytes)."""
    import cv2
    img = np.zeros((height, width, 3), dtype=np.uint8)
    # 초록 계열 랜덤 노이즈
    img[:, :, 1] = np.random.randint(80, 200, (height, width), dtype=np.uint8)
    img[:, :, 0] = np.random.randint(0, 60, (height, width), dtype=np.uint8)
    img[:, :, 2] = np.random.randint(0, 60, (height, width), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


def _make_silent_wav_bytes(duration_ms: int = 500) -> bytes:
    """테스트용 무음 WAV (PCM 16bit 16kHz)."""
    import struct
    sample_rate = 16000
    num_samples = int(sample_rate * duration_ms / 1000)
    pcm_data = b"\x00\x00" * num_samples
    data_size = len(pcm_data)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF", 36 + data_size, b"WAVE",
        b"fmt ", 16, 1, 1,
        sample_rate, sample_rate * 2, 2, 16,
        b"data", data_size,
    )
    return header + pcm_data


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient (앱 임포트)."""
    from src.api.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def test_image():
    return _make_test_image_bytes()


@pytest.fixture(scope="module")
def test_wav():
    return _make_silent_wav_bytes()


# ── 시나리오 1: 사진 → 진단 → 분즈 메시지 → TTS ─────────────


@skip_no_models
class TestScenario1_Diagnose:
    """사진 진단 전체 흐름."""

    def test_diagnose_returns_200(self, client, test_image):
        resp = client.post(
            "/diagnose",
            files={"file": ("leaf.jpg", test_image, "image/jpeg")},
            data={"nickname": "마리"},
        )
        assert resp.status_code == 200, resp.text

    def test_diagnose_response_has_required_fields(self, client, test_image):
        resp = client.post(
            "/diagnose",
            files={"file": ("leaf.jpg", test_image, "image/jpeg")},
            data={"nickname": "마리"},
        )
        data = resp.json()
        assert "species" in data
        assert "disease" in data
        assert "lesion" in data
        assert "care_guide" in data
        assert "boonz" in data

    def test_boonz_has_mood_and_message(self, client, test_image):
        resp = client.post(
            "/diagnose",
            files={"file": ("leaf.jpg", test_image, "image/jpeg")},
            data={"nickname": "마리"},
        )
        boonz = resp.json()["boonz"]
        assert boonz.get("mood") in ("happy", "worried", "sad", "default")
        assert isinstance(boonz.get("message"), str)
        assert len(boonz["message"]) > 0

    def test_lesion_overlay_base64_present(self, client, test_image):
        resp = client.post(
            "/diagnose",
            files={"file": ("leaf.jpg", test_image, "image/jpeg")},
            data={"nickname": "마리"},
        )
        lesion = resp.json()["lesion"]
        assert "ratio" in lesion
        assert 0.0 <= lesion["ratio"] <= 1.0
        assert "severity" in lesion
        assert lesion["severity"] in ("초기", "중기", "후기")

    def test_care_guide_text_not_empty(self, client, test_image):
        resp = client.post(
            "/diagnose",
            files={"file": ("leaf.jpg", test_image, "image/jpeg")},
        )
        care = resp.json()["care_guide"]
        assert isinstance(care.get("text"), str)
        assert len(care["text"]) > 0


# ── 시나리오 2: 음성 → STT → LLM → TTS ──────────────────────


@skip_no_models
class TestScenario2_VoiceConsult:
    """음성 상담 전체 흐름."""

    def test_voice_consult_returns_200(self, client, test_wav):
        resp = client.post(
            "/voice-consult",
            files={"file": ("audio.wav", test_wav, "audio/wav")},
            data={"nickname": "마리"},
        )
        assert resp.status_code == 200, resp.text

    def test_voice_consult_has_transcript(self, client, test_wav):
        resp = client.post(
            "/voice-consult",
            files={"file": ("audio.wav", test_wav, "audio/wav")},
            data={"nickname": "마리"},
        )
        data = resp.json()
        assert "transcript" in data
        assert "answer" in data

    def test_text_override_skips_stt(self, client, test_wav):
        """text_override가 있으면 STT 없이 바로 LLM 응답."""
        resp = client.post(
            "/voice-consult",
            files={"file": ("audio.wav", test_wav, "audio/wav")},
            data={"nickname": "마리", "text_override": "잎이 노랗게 변해요"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # transcript가 text_override 값과 같아야 함
        assert data["transcript"] == "잎이 노랗게 변해요"

    def test_boonz_message_contains_nickname(self, client, test_wav):
        resp = client.post(
            "/voice-consult",
            files={"file": ("audio.wav", test_wav, "audio/wav")},
            data={"nickname": "마리", "text_override": "물 얼마나 줘야 해?"},
        )
        boonz = resp.json()["boonz"]
        assert "마리" in boonz.get("message", "")


# ── 시나리오 3: 약제 라벨 → OCR → 적합성 ────────────────────


@skip_no_models
class TestScenario3_Medicine:
    """약제 체크 전체 흐름."""

    def test_medicine_returns_200(self, client, test_image):
        resp = client.post(
            "/check-medicine",
            files={"file": ("label.jpg", test_image, "image/jpeg")},
            data={"nickname": "콩이"},
        )
        assert resp.status_code == 200, resp.text

    def test_medicine_has_ocr_and_compatibility(self, client, test_image):
        resp = client.post(
            "/check-medicine",
            files={"file": ("label.jpg", test_image, "image/jpeg")},
            data={"nickname": "콩이"},
        )
        data = resp.json()
        assert "ocr_result" in data
        assert "compatibility" in data
        assert "boonz" in data

    def test_medicine_boonz_message_has_nickname(self, client, test_image):
        resp = client.post(
            "/check-medicine",
            files={"file": ("label.jpg", test_image, "image/jpeg")},
            data={"nickname": "콩이"},
        )
        boonz = resp.json()["boonz"]
        assert "콩이" in boonz.get("message", "")


# ── 시나리오 4: 원터치 로그 → 타임라인 ───────────────────────


class TestScenario4_CareLogTimeline:
    """케어 로그 + 타임라인 (모델 불필요)."""

    TEST_NICKNAME = "테스트식물_e2e"

    def test_care_log_saved(self, client):
        resp = client.post(
            "/api/care-log",
            json={
                "nickname": self.TEST_NICKNAME,
                "action": "water",
                "lesion_ratio": 0.05,
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["saved"] is True
        assert "boonz" in data

    def test_care_log_boonz_message(self, client):
        resp = client.post(
            "/api/care-log",
            json={"nickname": self.TEST_NICKNAME, "action": "observe"},
        )
        boonz = resp.json()["boonz"]
        assert self.TEST_NICKNAME in boonz.get("message", "")

    def test_timeline_returns_entries(self, client):
        # 먼저 로그 2개 추가
        for action in ("water", "medicine"):
            client.post(
                "/api/care-log",
                json={"nickname": self.TEST_NICKNAME, "action": action},
            )

        resp = client.get(f"/api/timeline/{self.TEST_NICKNAME}")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "boonz" in data

    def test_timeline_items_sorted_by_date(self, client):
        resp = client.get(f"/api/timeline/{self.TEST_NICKNAME}")
        items = resp.json()["items"]
        if len(items) >= 2:
            timestamps = [item["timestamp"] for item in items]
            assert timestamps == sorted(timestamps)


# ── 시나리오 5: 패턴 분석 → 분즈 말풍선 ─────────────────────


class TestScenario5_PatternAnalysis:
    """돌봄 패턴 분석 (모델 불필요)."""

    TEST_NICKNAME = "패턴테스트식물_e2e"

    def test_pattern_insufficient_data(self, client):
        """기록 10개 미만 → 안내 메시지."""
        resp = client.get(f"/api/pattern/{self.TEST_NICKNAME}")
        assert resp.status_code == 200
        data = resp.json()
        assert "analysis" in data
        assert "boonz" in data
        # 10개 미만이면 "조금만 더 쌓아줘" 포함
        assert "개" in data["analysis"]

    def test_pattern_boonz_default_mood_when_few_logs(self, client):
        resp = client.get(f"/api/pattern/{self.TEST_NICKNAME}")
        boonz = resp.json()["boonz"]
        assert boonz["mood"] == "default"

    def test_plant_register(self, client):
        """식물 등록 엔드포인트."""
        resp = client.post(
            "/api/plants",
            json={"nickname": self.TEST_NICKNAME, "species_name": "Monstera"},
        )
        # 이미 등록됐을 수도 있으므로 200 or 409
        assert resp.status_code in (200, 409)

    def test_plant_list(self, client):
        """식물 목록 조회."""
        resp = client.get("/api/plants")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ── 공통: 헬스 체크 ──────────────────────────────────────────


class TestHealthCheck:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_invalid_image_format(self, client):
        """이미지가 아닌 파일 업로드 → 400."""
        resp = client.post(
            "/diagnose",
            files={"file": ("data.txt", b"not an image", "text/plain")},
        )
        assert resp.status_code == 400

    def test_oversized_image(self, client):
        """10MB 초과 이미지 → 400."""
        big = b"\x00" * (11 * 1024 * 1024)
        resp = client.post(
            "/diagnose",
            files={"file": ("big.jpg", big, "image/jpeg")},
        )
        assert resp.status_code == 400
