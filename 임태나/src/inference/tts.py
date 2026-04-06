"""TTS 모듈.

우선순위: Qwen3-TTS (로컬) → ElevenLabs (API) → gTTS (폴백).
Qwen3-TTS는 lazy loading — 첫 호출 시 모델 로드, 이후 재사용.
GPU 메모리 부족 또는 로드 실패 시 자동 폴백.
"""

import os
import uuid
from pathlib import Path
from typing import Literal

from loguru import logger

from src.config import PROJECT_ROOT

AUDIO_DIR = PROJECT_ROOT / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# ── Qwen3-TTS 설정 ───────────────────────────────────────────
QWEN_MODEL_ID = os.getenv("QWEN_TTS_MODEL", "Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice")
QWEN_SPEAKER = os.getenv("QWEN_TTS_SPEAKER", "sohee")

# ── ElevenLabs 설정 (폴백 2순위) ─────────────────────────────
ELEVENLABS_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")
ELEVENLABS_MODEL = "eleven_multilingual_v2"

# ── Qwen3-TTS 싱글턴 ─────────────────────────────────────────
_qwen_model = None
_qwen_status: Literal["unloaded", "ready", "failed"] = "unloaded"


def _get_qwen_model():
    """Qwen3-TTS 모델 lazy load. 실패 시 None 반환."""
    global _qwen_model, _qwen_status

    if _qwen_status == "ready":
        return _qwen_model
    if _qwen_status == "failed":
        return None

    try:
        from qwen_tts import Qwen3TTSModel
        logger.info(f"Qwen3-TTS 로드 중: {QWEN_MODEL_ID}")
        _qwen_model = Qwen3TTSModel.from_pretrained(QWEN_MODEL_ID)
        _qwen_status = "ready"
        logger.info("Qwen3-TTS 로드 완료")
        return _qwen_model
    except Exception as e:
        logger.warning(f"Qwen3-TTS 로드 실패, 폴백 사용: {e}")
        _qwen_status = "failed"
        return None


# ── 공개 함수 ────────────────────────────────────────────────


def text_to_speech(text: str, output_path: Path | None = None) -> Path:
    """텍스트를 음성 파일로 변환.

    우선순위: Qwen3-TTS → ElevenLabs → gTTS.

    Args:
        text: 변환할 텍스트.
        output_path: 저장 경로. None이면 자동 생성.

    Returns:
        생성된 오디오 파일 경로.
    """
    uid = uuid.uuid4().hex[:8]

    # Qwen3-TTS 시도 (wav)
    wav_path = output_path or (AUDIO_DIR / f"guide_{uid}.wav")
    wav_path = Path(wav_path)
    wav_path.parent.mkdir(parents=True, exist_ok=True)

    if _try_qwen(text, wav_path):
        return wav_path

    # ElevenLabs 시도 (mp3)
    mp3_path = AUDIO_DIR / f"guide_{uid}.mp3"
    if ELEVENLABS_KEY and _try_elevenlabs(text, mp3_path):
        return mp3_path

    # gTTS 폴백 (mp3)
    return _gtts_fallback(text, AUDIO_DIR / f"guide_{uid}.mp3")


def get_audio_url(audio_path: Path) -> str:
    """오디오 파일 경로를 API URL로 변환."""
    return f"/audio/{audio_path.name}"


# ── 내부 함수 ────────────────────────────────────────────────


def _try_qwen(text: str, output_path: Path) -> bool:
    """Qwen3-TTS로 음성 생성. 성공 시 True.

    CustomVoice 모델: generate_custom_voice(speaker=...) 사용.
    Base 모델: speaker가 없으므로 False 반환 (폴백으로 넘김).
    """
    model = _get_qwen_model()
    if model is None:
        return False

    # Base 모델은 predefined speaker 미지원 → 폴백
    model_type = getattr(model.model, "tts_model_type", "")
    if model_type == "base":
        logger.warning("Qwen3-TTS base 모델은 predefined speaker 미지원. 폴백 사용.")
        return False

    try:
        import soundfile as sf

        arrays, sample_rate = model.generate_custom_voice(
            text=text,
            speaker=QWEN_SPEAKER,
            language="korean",
            non_streaming_mode=True,
        )
        sf.write(str(output_path), arrays[0], sample_rate)
        logger.info(f"Qwen3-TTS 완료: {output_path}")
        return True
    except Exception as e:
        logger.warning(f"Qwen3-TTS 생성 실패, 폴백: {e}")
        return False


def _try_elevenlabs(text: str, output_path: Path) -> bool:
    """ElevenLabs TTS 시도. 성공 시 True."""
    try:
        from elevenlabs import ElevenLabs

        client = ElevenLabs(api_key=ELEVENLABS_KEY)
        audio = client.text_to_speech.convert(
            text=text,
            voice_id=ELEVENLABS_VOICE_ID,
            model_id=ELEVENLABS_MODEL,
            output_format="mp3_44100_128",
        )
        with open(output_path, "wb") as f:
            for chunk in audio:
                f.write(chunk)
        logger.info(f"ElevenLabs TTS 완료: {output_path}")
        return True
    except Exception as e:
        logger.warning(f"ElevenLabs 실패, gTTS 폴백: {e}")
        return False


def _gtts_fallback(text: str, output_path: Path) -> Path:
    """gTTS 폴백."""
    from gtts import gTTS

    try:
        tts = gTTS(text=text, lang="ko")
        tts.save(str(output_path))
        logger.info(f"gTTS 완료: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"gTTS 실패: {e}")
        raise


if __name__ == "__main__":
    path = text_to_speech("마리? 잘 부탁해.")
    logger.info(f"테스트 완료: {path} ({path.stat().st_size:,} bytes)")
