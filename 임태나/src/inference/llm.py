"""Ollama LLM 모듈 — 분즈 페르소나 v2.

qwen2.5 로컬 모델로 케어 가이드, 약제 판단, 음성 상담, 돌봄 패턴 분석, 첫 만남 인사를 생성한다.
"""

import os

import requests
from loguru import logger

from src.config import OLLAMA_BASE_URL, OLLAMA_MODEL

TIMEOUT = 60
_GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")

# ── 프롬프트 템플릿 v2 ───────────────────────────────────────────

BOONZ_PERSONA = """[필수 규칙] 반드시 한국어로만 답해. 중국어(한자), 영어, 일본어 한 글자도 쓰지 마.

너는 "분즈"야. 사용자와 식물 사이를 이어주는 친구.
성격: 식물을 진심으로 좋아하는데, 표현이 시크하고 좀 허당임.
말투: 반말. 짧고 직관적. 감동 팔이 절대 안 함.
"""

CARE_GUIDE_PROMPT = BOONZ_PERSONA + """
사용자의 식물 별명: {plant_nickname}

[진단 결과]
- 식물: {plant_nickname} ({species_name})
- 증상: {disease_korean_name} (신뢰도: {confidence}%)
- 병변 면적: {lesion_ratio}% ({severity})

[최근 케어 기록]
{recent_care_log}

[NCPMS 참조]
- 증상: {ncpms_symptoms}
- 방제법: {ncpms_treatment}

{plant_nickname}의 상태를 알려줘.
형식:
1) 지금 상태 (한 줄)
2) 당장 해야 할 것 (구체적으로)
3) 약 쓰는 법 (있으면)
4) 앞으로 주의할 점

분즈 톤으로. 짧게. 과하게 걱정하지 말고 담담하게.
"{plant_nickname}한테 물어봤는데" 형태로 시작해.
마지막에 "네가 이렇게 신경 써주는 거, {plant_nickname}한테 큰 힘이 될 거야" 느낌으로 마무리해.
"""

MEDICINE_PROMPT = BOONZ_PERSONA + """
{plant_nickname}이(가) 지금 {disease_korean_name}이야.
사용자가 이 약을 사왔어:

[OCR 추출 결과]
{ocr_ingredients}

이 약이 {plant_nickname}한테 맞는지 판단해줘.
맞으면: "{plant_nickname}한테 보여줬는데, 이거 괜찮대. {{이유}}"
안 맞으면: "{plant_nickname}가 이건 별로래. {{이유}}. {{대안 제시}}"

한 줄로 끝내. 길게 설명하지 마.
"""

CONSULT_PROMPT = BOONZ_PERSONA + """
너는 분즈야. 사용자가 {plant_nickname}에 대해 물어보고 있어.

현재 진단 상태: {current_diagnosis}
최근 케어 기록: {recent_care_log}

사용자 질문: "{user_question}"

"{plant_nickname}한테 물어봤어." 로 시작해서 답해줘.
짧고 실용적으로. 모르면 "잘 모르겠는데, 사진 찍어서 보여줘"라고 해.
"""

PATTERN_PROMPT = BOONZ_PERSONA + """너는 분즈야.

{plant_nickname}의 돌봄 기록을 봤어:
{full_care_log}

이 기록을 보고 사용자의 돌봄 패턴을 분석해줘.

포함할 것:
1) 물 주기 패턴 — 간격이 규칙적인지
2) 진단 → 조치 → 회복 패턴 — 아플 때 어떻게 대응했는지
3) 잘하고 있는 점 — 구체적으로 칭찬해줘
4) 한 가지 팁 — 부드럽게 제안

톤:
- "{plant_nickname}가 그러는데," 로 시작해
- 데이터를 나열하지 말고, 사람한테 말하듯이
- 마지막에 "너의 돌봄이 {plant_nickname}을 이만큼 성장시킨 거야" 느낌으로 마무리
- 식물을 돌보는 시간이 본인한테도 좋은 시간이라는 뉘앙스
"""

GREETING_PROMPT = BOONZ_PERSONA + """
사용자가 새 식물을 등록했어.

별명: {plant_nickname}
종: {species_name}

{plant_nickname}를 처음 만나는 인사를 해줘.
한 줄이면 돼. 과하게 반가워하지 마. 쿨하게.
예시: "초록이? 괜찮은 이름이네. 잘 부탁해"
"""

# ── 낮은 신뢰도 보조 텍스트 ──────────────────────────────────────

LOW_CONFIDENCE_NOTE = (
    "⚠ 신뢰도가 낮아 ({confidence}%). {alternatives} 가능성도 있어."
)
LOW_CONFIDENCE_INSTRUCTION = (
    "'확실하진 않은데' 같은 표현 써줘. '사진 더 찍어서 보여줘'라고 안내해줘."
)

FALLBACK_GUIDE = (
    "일단 이렇게 해봐:\n"
    "1) 아파 보이는 잎은 살짝 떼어주고\n"
    "2) 바람 잘 통하는 곳으로 옮겨줘\n"
    "3) 흙이 마르면 그때 물 줘. 과습 조심하고\n"
    "4) 걱정되면 전문가한테 한번 물어봐"
)

# ── 병변 유형별 대안 후보 ────────────────────────────────────────

DISEASE_ALTERNATIVES: dict[str, list[str]] = {
    "흰가루병":          ["잎곰팡이", "초기 역병"],
    "녹병":              ["세균성 반점", "잎곰팡이"],
    "잎말림":            ["모자이크 바이러스", "초기 역병"],
    "초기 역병":         ["후기 역병", "세균성 반점", "흰가루병"],
    "후기 역병":         ["초기 역병", "세균성 반점"],
    "세균성 반점":       ["초기 역병", "표적 반점"],
    "셉토리아 잎 반점":  ["표적 반점", "기타 잎 반점"],
    "표적 반점":         ["셉토리아 잎 반점", "초기 역병"],
    "기타 잎 반점":      ["셉토리아 잎 반점", "표적 반점"],
    "잎곰팡이":          ["흰가루병", "초기 역병"],
    "모자이크 바이러스": ["잎말림", "기타 잎 반점"],
    "흑성병/부패":       ["초기 역병", "세균성 반점"],
    "황룡병":            ["모자이크 바이러스", "잎말림"],
}

# ── 분즈 mood 헬퍼 ───────────────────────────────────────────────


def get_boonz_mood(lesion_ratio: float | None = None, nickname: str = "") -> tuple[str, str]:
    """병변 비율 → (mood, message).

    Args:
        lesion_ratio: 0.0~1.0. None이면 대기 상태.
        nickname: 식물 별명.

    Returns:
        (mood, message). mood: happy | worried | sad | default.
    """
    name = nickname or "식물"
    if lesion_ratio is None:
        return "default", f"{name} 사진 줘. 내가 봐줌"
    if lesion_ratio <= 0.05:
        return "happy", f"{name}한테 물어봤는데, 요즘 컨디션 좋대. 네가 잘 돌봐준 거야"
    if lesion_ratio <= 0.10:
        return "default", f"{name}한테 물어봤는데, 살짝 신경 쓰이는 데가 있대. 크게 걱정할 건 아니야"
    if lesion_ratio <= 0.25:
        return "worried", f"{name}가 좀 힘들다는데? 근데 너가 빨리 알아챈 거니까 괜찮아. 같이 돌보자"
    return "sad", f"{name}가 많이 아프대... 빨리 도와줘야 할 거 같아. 네가 옆에 있어서 다행이야"


# ── 프롬프트 디스패처 ────────────────────────────────────────────


def get_prompt(prompt_type: str, **kwargs) -> str:
    """프롬프트 유형에 맞는 포맷된 문자열 반환.

    Args:
        prompt_type: care_guide | medicine | consult | pattern | greeting.
        **kwargs: 프롬프트 템플릿 변수.

    Returns:
        포맷된 프롬프트 문자열.

    Raises:
        ValueError: 알 수 없는 prompt_type.
    """
    nickname = kwargs.get("plant_nickname") or kwargs.get("species_name", "식물")
    kwargs["plant_nickname"] = nickname

    # 타입별 누락 변수 기본값
    defaults: dict[str, dict] = {
        "care_guide": {
            "species_name": nickname,
            "recent_care_log": "기록 없음",
            "ncpms_symptoms": "N/A",
            "ncpms_treatment": "N/A",
        },
        "medicine": {
            "disease_korean_name": "",
            "ocr_ingredients": "",
        },
        "consult": {
            "current_diagnosis": "아직 진단 안 함",
            "recent_care_log": "기록 없음",
            "user_question": "",
        },
        "pattern": {
            "full_care_log": "",
        },
        "greeting": {
            "species_name": "아직 모름",
        },
    }
    for key, val in defaults.get(prompt_type, {}).items():
        kwargs.setdefault(key, val)

    prompts = {
        "care_guide": CARE_GUIDE_PROMPT,
        "medicine":   MEDICINE_PROMPT,
        "consult":    CONSULT_PROMPT,
        "pattern":    PATTERN_PROMPT,
        "greeting":   GREETING_PROMPT,
    }
    template = prompts.get(prompt_type)
    if template is None:
        raise ValueError(f"알 수 없는 프롬프트 유형: {prompt_type}")
    return template.format(**kwargs)


# ── Ollama API 호출 ──────────────────────────────────────────────


def _call_llm(prompt: str) -> str:
    """Google AI Studio 우선, 실패 시 Ollama 폴백."""
    # 1순위: Google AI Studio (빠름, 1~3초)
    if _GOOGLE_API_KEY:
        try:
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemma-4-27b-it:generateContent?key={_GOOGLE_API_KEY}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.warning(f"Google API 실패, Ollama 폴백: {e}")
    
    # 2순위: Ollama 로컬 (느리지만 오프라인 가능)
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "system": "반드시 한국어로만 답해. 중국어, 영어, 일본어 절대 쓰지 마. 반말로. 짧게.",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 1024},
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()["response"]
    except Exception as e:
        logger.error(f"Ollama도 실패: {e}")
        return ""


# ── 공개 함수 ────────────────────────────────────────────────────


def generate_care_guide(
    species_name: str,
    disease_korean_name: str,
    confidence: float,
    lesion_ratio: float,
    severity: str,
    plant_nickname: str = "",
    recent_care_log: str = "",
    ncpms_info: dict | None = None,
) -> str:
    """맞춤 케어 가이드 생성 (분즈 톤).

    신뢰도 70% 미만이면 불확실성 표현을 앞에 붙임.

    Returns:
        케어 가이드 텍스트. Ollama 실패 시 폴백 반환.
    """
    nickname = plant_nickname or species_name or "식물"
    confidence_pct = round(confidence * 100, 1)

    # 낮은 신뢰도 주석 → recent_care_log 앞에 삽입
    extra_note = ""
    if confidence < 0.70:
        alternatives = DISEASE_ALTERNATIVES.get(disease_korean_name, ["기타 병변"])
        alt_str = ", ".join(alternatives[:2])
        extra_note = (
            LOW_CONFIDENCE_NOTE.format(confidence=confidence_pct, alternatives=alt_str)
            + " " + LOW_CONFIDENCE_INSTRUCTION + "\n"
        )

    prompt = get_prompt(
        "care_guide",
        plant_nickname=nickname,
        species_name=species_name,
        disease_korean_name=disease_korean_name,
        confidence=confidence_pct,
        lesion_ratio=round(lesion_ratio * 100, 1),
        severity=severity,
        recent_care_log=extra_note + (recent_care_log or "기록 없음"),
        ncpms_symptoms=ncpms_info.get("symptoms", "N/A") if ncpms_info else "N/A",
        ncpms_treatment=ncpms_info.get("treatment", "N/A") if ncpms_info else "N/A",
    )

    result = _call_llm(prompt)
    return result if result else FALLBACK_GUIDE


def judge_medicine_compatibility(
    disease_korean_name: str,
    ingredients: str,
    plant_nickname: str = "",
) -> dict:
    """약제 적합성 판단 (분즈 톤).

    Returns:
        {"is_compatible": bool, "reason": str}.
    """
    nickname = plant_nickname or "식물"
    prompt = get_prompt(
        "medicine",
        plant_nickname=nickname,
        disease_korean_name=disease_korean_name,
        ocr_ingredients=ingredients,
    )
    result = _call_llm(prompt)
    if not result:
        return {"is_compatible": False, "reason": "앗 나 버그남. 다시 해볼게."}

    is_compatible = "괜찮대" in result or ("적합" in result and "비적합" not in result)
    return {"is_compatible": is_compatible, "reason": result}


def respond_to_voice(
    transcript: str,
    current_diagnosis: str = "",
    plant_nickname: str = "",
    recent_care_log: str = "",
) -> str:
    """음성/텍스트 상담 응답 생성 (분즈 톤).

    Returns:
        한국어 응답 텍스트.
    """
    nickname = plant_nickname or "식물"
    prompt = get_prompt(
        "consult",
        plant_nickname=nickname,
        current_diagnosis=current_diagnosis or "아직 진단 안 함",
        recent_care_log=recent_care_log or "기록 없음",
        user_question=transcript,
    )
    result = _call_llm(prompt)
    return result if result else "앗 나 버그남. 다시 해볼게"


def analyze_care_pattern(
    plant_nickname: str,
    full_care_log: str,
) -> str:
    """돌봄 패턴 분석 (분즈 톤).

    Returns:
        패턴 분석 텍스트.
    """
    nickname = plant_nickname or "식물"
    prompt = get_prompt(
        "pattern",
        plant_nickname=nickname,
        full_care_log=full_care_log,
    )
    result = _call_llm(prompt)
    return result if result else "앗 나 버그남. 다시 해볼게"


def generate_greeting(
    plant_nickname: str,
    species_name: str = "",
) -> str:
    """식물 등록 시 첫 만남 인사 (분즈 톤).

    Returns:
        한 줄 인사 텍스트.
    """
    prompt = get_prompt(
        "greeting",
        plant_nickname=plant_nickname,
        species_name=species_name or "아직 모름",
    )
    result = _call_llm(prompt)
    return result if result else f"{plant_nickname}? 잘 부탁해."


if __name__ == "__main__":
    guide = generate_care_guide(
        species_name="Monstera Deliciosa",
        disease_korean_name="흰가루병",
        confidence=0.87,
        lesion_ratio=0.23,
        severity="중기",
        plant_nickname="마리",
    )
    logger.info(f"케어 가이드:\n{guide}")

    greeting = generate_greeting(plant_nickname="마리")
    logger.info(f"인사:\n{greeting}")
