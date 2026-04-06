"""Whisper STT 모듈.

OpenAI Whisper large-v3 로컬 실행으로 음성을 텍스트로 변환한다.
"""

from pathlib import Path

import numpy as np
from loguru import logger

_model = None


def _get_model():
    """Whisper 모델 싱글턴 로드."""
    global _model
    if _model is None:
        import whisper
        _model = whisper.load_model("turbo")
        logger.info("Whisper turbo 로드 완료")
    return _model


def transcribe(audio_path: str | Path, language: str = "ko") -> str:
    """음성 파일을 텍스트로 변환.

    Args:
        audio_path: 음성 파일 경로 (wav/mp3/m4a).
        language: 언어 코드 (기본 한국어).

    Returns:
        변환된 텍스트.
    """
    model = _get_model()
    try:
        result = model.transcribe(str(audio_path), language=language)
        text = result["text"].strip()
        logger.info(f"STT 완료: '{text[:50]}...' ({len(text)}자)")
        return text
    except Exception as e:
        logger.error(f"STT 실패: {e}")
        return "음성을 인식할 수 없습니다. 다시 시도해주세요."


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        logger.error("사용법: python -m src.inference.stt <음성_파일>")
        sys.exit(1)
    text = transcribe(sys.argv[1])
    logger.info(f"결과: {text}")
