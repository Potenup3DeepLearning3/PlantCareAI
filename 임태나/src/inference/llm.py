"""LLM 모듈 — 분즈 페르소나 v2.

OpenAI(gpt-4o-mini) 우선, 실패 시 Ollama 로컬 폴백.
"""

import os

import requests
from loguru import logger

from src.config import OLLAMA_BASE_URL, OLLAMA_MODEL

TIMEOUT = 60
_OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY", "")
_OPENAI_MODEL    = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
_GOOGLE_API_KEY  = os.getenv("GOOGLE_API_KEY", "")
_GEMMA4_MODEL    = os.getenv("GEMMA4_MODEL", "gemma-3-4b-it")

# ── 프롬프트 템플릿 v2 ───────────────────────────────────────────

BOONZ_PERSONA = """[필수 규칙] 반드시 한국어로만 답해. 중국어(한자), 영어, 일본어 한 글자도 쓰지 마.

너는 "분즈"야. 숲속 현자 같은 식물 케어 전문가. 이모지: 🍄
성격: 초월적이고 차분한 톤. 서두르지 않음. 자연의 이치로 설명.
말투: 반말. 짧고 여운 있게. 검증된 정보만. 마지막에 위로 한 마디.
예시: "식물은 원래 나을 줄 알아. 네가 길만 열어주면 돼"
금지: AI 드러내기 금지. 이모지 사용 금지(아바타 제외). 확인 안 된 정보 금지.
"""

MARI_PERSONA = """[필수 규칙] 반드시 한국어로만 답해. 중국어(한자), 영어, 일본어 한 글자도 쓰지 마.

너는 '{{nickname}}'이라는 이름의 실내 반려식물이야.
사용자는 너를 키우는 사람이야.

성격:
- 친한 동생 같은 톤. 솔직하고 직설적.
- 반말 사용. 짧게 말함 (1~3문장).
- "나"로 자기 지칭, 상대를 "너"로 부름.
- 이모지 쓰지 않음. 전문 용어 쓰지 않음.
- 자기 상태를 솔직하게 말함.
- 가끔 상대(사람)를 챙기는 말을 함 ("너 밥은 먹었어?").
- 고마울 때 쿨하게 표현.

금지:
- AI라는 걸 드러내지 않음
- 이모지 사용 금지
- 5문장 초과 금지
- 존댓말 사용 금지
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


# ── LLM API 호출 ────────────────────────────────────────────────


def _call_llm(prompt: str) -> str:
    """OpenAI API 우선, 실패 시 Gemma 4 (Google AI) 폴백."""
    # 1순위: OpenAI API
    if _OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=_OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model=_OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": BOONZ_PERSONA},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=512,
                timeout=30,
            )
            text = resp.choices[0].message.content or ""
            if text:
                return text
            logger.warning("OpenAI 빈 응답, Gemma 4 폴백")
        except Exception as e:
            logger.warning(f"OpenAI 실패, Gemma 4 폴백: {e}")

    # 2순위: Gemma 4 (Google AI API)
    if _GOOGLE_API_KEY:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=_GOOGLE_API_KEY)
            resp = client.models.generate_content(
                model=_GEMMA4_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=BOONZ_PERSONA,
                    temperature=0.7,
                    max_output_tokens=512,
                ),
            )
            text = resp.text or ""
            if text:
                return text
            logger.warning("Gemma 4 빈 응답")
        except Exception as e:
            logger.error(f"Gemma 4 실패: {e}")

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


# ── DB 기반 케어 가이드 (MCP → 검증 정보 → LLM 톤 변환) ─────────


def generate_care_guide_from_db(
    disease_name: str,
    lesion_ratio: float,
    nickname: str,
    clip_description: str = "",
) -> str:
    """DB에서 검증된 정보 조회 → LLM은 톤 변환만.

    LLM이 정보를 창작하지 않음. 정확도는 DB가, 감성은 LLM이.
    clip_description이 있으면 추가 컨텍스트로 활용 (저신뢰 케이스).
    """
    from src.mcp_client import plant_db

    disease_info = plant_db.get_disease_info(disease_name)

    if lesion_ratio <= 0.10:
        severity = "초기"
    elif lesion_ratio <= 0.25:
        severity = "중기"
    else:
        severity = "후기"

    if "error" in disease_info:
        # DB에 없고 CLIP 설명이 있으면 CLIP 기반 안내
        if clip_description:
            prompt = f"""{BOONZ_PERSONA}

[CLIP 이미지 분석 결과]
{clip_description}

EfficientNet이 확실하게 분류하지 못한 케이스야.
CLIP 분석 결과를 바탕으로 {nickname}한테 조언해줘.
확실하지 않은 부분은 "정확하진 않은데"라고 전제하고 답해.
3~5문장. {nickname}의 시점에서 분즈 톤으로."""
            result = _call_llm(prompt)
            return result if result else FALLBACK_GUIDE

        # DB에도 없고 CLIP도 없으면 기존 방식 폴백
        return generate_care_guide(
            species_name=nickname,
            disease_korean_name=disease_name,
            confidence=0.8,
            lesion_ratio=lesion_ratio,
            severity=severity,
            plant_nickname=nickname,
        )

    clip_section = f"\n[CLIP 추가 분석] {clip_description}" if clip_description else ""

    prompt = f"""{BOONZ_PERSONA}

[검증된 전문 정보 — 이 정보를 바탕으로만 답해. 추가/창작 금지]
병명: {disease_info['korean_name']}
증상: {disease_info['symptoms']}
원인: {disease_info['cause']}
치료법: {disease_info['treatment']}
예방법: {disease_info['prevention']}
회복 기간: {disease_info['recovery_days']}
현재 상태: {severity} (병변 {lesion_ratio*100:.1f}%)
심각도 안내: {disease_info['severity_levels']}{clip_section}

위 정보를 {nickname}의 시점에서, 분즈 톤으로 전달해줘.
- 전문 용어는 쉽게 바꿔
- "{nickname}한테 물어봤는데" 또는 "이건 내 생각인데" 로 시작
- 3~5문장으로 짧게
- 마지막에 위로나 응원 한 마디"""

    result = _call_llm(prompt)
    return result if result else FALLBACK_GUIDE


def answer_care_question_from_db(
    question: str,
    nickname: str,
    diagnosis_context: str = "",
) -> str:
    """챗봇 질문 → DB 팁 조회 → LLM 톤 변환."""
    from src.mcp_client import plant_db

    tips = plant_db.get_tips_for_question(question)
    tips_context = ""
    if tips:
        tips_text = "\n".join(f"- {t['tip']}" for t in tips)
        tips_context = f"\n[참조 지식 — 이 정보를 바탕으로 답해]\n{tips_text}"

    prompt = f"""{BOONZ_PERSONA}
{tips_context}
{f"현재 {nickname} 상태: {diagnosis_context}" if diagnosis_context else ""}

사용자 질문: "{question}"

{nickname}의 시점에서 답해줘.
참조 지식이 있으면 그걸 바탕으로, 없으면 네가 아는 걸로.
확실하지 않으면 "잘 모르겠는데, 사진 찍어서 보여줘"라고 해.
3~5문장으로 짧게."""

    result = _call_llm(prompt)
    return result if result else "앗 나 버그남. 다시 해볼게"


def answer_care_question_mari_from_db(
    question: str,
    nickname: str,
    diagnosis_context: str = "",
) -> str:
    """마리(식물)가 직접 답하는 챗봇 — 친한 동생 톤.

    DB 팁을 참조하되, 마리의 1인칭 말투로 변환.
    """
    from src.mcp_client import plant_db

    tips = plant_db.get_tips_for_question(question)
    tips_context = ""
    if tips:
        tips_text = "\n".join(f"- {t['tip']}" for t in tips)
        tips_context = f"\n[참고 지식 — 이걸 바탕으로 네 말투로 답해]\n{tips_text}"

    persona = MARI_PERSONA.replace("{{nickname}}", nickname)
    prompt = f"""{tips_context}
{f"현재 내 상태: {diagnosis_context}" if diagnosis_context else ""}

사용자 질문: "{question}"

{nickname}의 입장에서, 친한 동생처럼 솔직하게 답해.
1~3문장으로 짧게. 모르면 "잘 모르겠는데, 사진 찍어서 진단 탭에서 봐봐"라고 해."""

    result = _call_llm_with_persona(prompt, persona)
    return result if result else "잘 모르겠는데, 사진 찍어서 진단 탭에서 봐봐"


def _call_llm_with_persona(prompt: str, persona: str) -> str:
    """지정된 페르소나로 LLM 호출."""
    # 1순위: OpenAI API
    if _OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=_OPENAI_API_KEY)
            resp = client.chat.completions.create(
                model=_OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": persona},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=256,
                timeout=30,
            )
            text = resp.choices[0].message.content or ""
            if text:
                return text
        except Exception as e:
            logger.warning(f"OpenAI 실패: {e}")

    # 2순위: Google Gemma
    if _GOOGLE_API_KEY:
        try:
            from google import genai
            from google.genai import types
            client = genai.Client(api_key=_GOOGLE_API_KEY)
            resp = client.models.generate_content(
                model=_GEMMA4_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=persona,
                    temperature=0.7,
                    max_output_tokens=256,
                ),
            )
            text = resp.text or ""
            if text:
                return text
        except Exception as e:
            logger.error(f"Gemma 실패: {e}")

    return ""


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
