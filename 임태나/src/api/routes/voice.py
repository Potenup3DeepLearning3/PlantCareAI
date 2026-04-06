"""POST /consult/voice, POST /consult/text 엔드포인트."""

import tempfile
import time
from pathlib import Path

from fastapi import APIRouter, Form, HTTPException, UploadFile
from loguru import logger

from src.api.schemas import BoonzResponse, ConsultAnswerResponse, ConsultResponse
from src.inference.llm import respond_to_voice
from src.inference.stt import transcribe
from src.inference.tts import get_audio_url, text_to_speech

router = APIRouter()

_SUGGEST_PHOTO_MSG = "사진을 올려주시면 더 정확한 진단이 가능합니다"


def _boonz_msg(name: str, response_text: str) -> str:
    return f"{name}한테 물어봤어. " + response_text[:100]


def _suggest_action(text: str) -> str:
    return _SUGGEST_PHOTO_MSG if "사진" not in text and "이미지" not in text else ""


ALLOWED_AUDIO = {
    "audio/wav", "audio/mpeg", "audio/mp3", "audio/m4a",
    "audio/x-m4a", "audio/mp4", "audio/webm", "audio/ogg",
}
MAX_AUDIO_SIZE = 10 * 1024 * 1024  # 10MB


@router.post("/consult/voice", response_model=ConsultResponse)
async def voice_consult(
    file: UploadFile,
    nickname: str = Form(""),
    text_override: str = Form(""),
) -> ConsultResponse:
    """음성 상담: STT → LLM → TTS.

    text_override가 있으면 STT를 생략하고 텍스트 직접 사용.
    """
    name = nickname or "식물"
    start = time.perf_counter()

    if text_override:
        transcript = text_override
    else:
        content_type = file.content_type or ""
        if not content_type.startswith("audio/"):
            raise HTTPException(status_code=400, detail="음성 파일만 업로드 가능합니다 (wav/mp3/m4a).")

        contents = await file.read()
        if len(contents) > MAX_AUDIO_SIZE:
            raise HTTPException(status_code=400, detail="음성 파일은 10MB 이하여야 합니다.")

        suffix = Path(file.filename or "audio.wav").suffix or ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            transcript = transcribe(tmp_path)
        except Exception as e:
            logger.error(f"STT 실패: {e}")
            raise HTTPException(status_code=500, detail=f"음성 인식 실패: {e}")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    response_text = respond_to_voice(transcript, plant_nickname=name)
    audio_path = text_to_speech(response_text)
    audio_url = get_audio_url(audio_path)

    elapsed_ms = (time.perf_counter() - start) * 1000

    return ConsultResponse(
        transcript=transcript,
        question=transcript,
        answer=ConsultAnswerResponse(text=response_text, audio_url=audio_url),
        boonz=BoonzResponse(mood="happy", message=_boonz_msg(name, response_text)),
        suggested_action=_suggest_action(transcript),
        processing_time_ms=round(elapsed_ms, 1),
    )


@router.post("/consult/text", response_model=ConsultResponse)
async def text_consult(
    question: str = Form(...),
    nickname: str = Form(""),
    diagnosis_context: str = Form(""),
) -> ConsultResponse:
    """텍스트 상담: LLM → TTS."""
    name = nickname or "식물"
    start = time.perf_counter()

    response_text = respond_to_voice(
        question, plant_nickname=name, current_diagnosis=diagnosis_context,
    )
    audio_path = text_to_speech(response_text)
    audio_url = get_audio_url(audio_path)

    elapsed_ms = (time.perf_counter() - start) * 1000

    return ConsultResponse(
        transcript="",
        question=question,
        answer=ConsultAnswerResponse(text=response_text, audio_url=audio_url),
        boonz=BoonzResponse(mood="happy", message=_boonz_msg(name, response_text)),
        suggested_action=_suggest_action(question),
        processing_time_ms=round(elapsed_ms, 1),
    )
