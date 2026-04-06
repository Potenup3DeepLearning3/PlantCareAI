# Boonz CLIP 구현 가이드 — 저신뢰 케이스 보완

## 역할

```
EfficientNet 신뢰도 높음 (≥70%) → 그대로 사용
EfficientNet 신뢰도 낮음 (<70%) → CLIP이 이미지를 텍스트로 설명
                                  → 그 설명을 LLM에 전달
                                  → 12클래스 밖의 증상도 커버
```

## 설치

```bash
pip install transformers pillow --break-system-packages
# CLIP 모델: openai/clip-vit-base-patch32 (약 600MB)
# 처음 실행 시 자동 다운로드
```

---

## 단계 1: CLIP 추론 모듈

### 파일: src/inference/clip_analyzer.py

```python
"""
CLIP 기반 식물 상태 분석.
EfficientNet 신뢰도가 낮을 때 폴백으로 사용.
이미지를 텍스트 설명으로 변환하여 LLM에 전달.
"""
import torch
from PIL import Image
from pathlib import Path
from transformers import CLIPProcessor, CLIPModel
import logging

logger = logging.getLogger(__name__)

# 모델 싱글턴
_model = None
_processor = None
_device = None


def _load_clip():
    """CLIP 모델 로드 (최초 1회)"""
    global _model, _processor, _device
    if _model is not None:
        return

    _device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"CLIP 로딩 중... (device: {_device})")

    _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(_device)
    _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    _model.eval()
    logger.info("CLIP 로드 완료")


# ==========================================
# 식물 상태 후보 텍스트 (CLIP이 비교할 대상)
# ==========================================
PLANT_CONDITIONS = [
    # 병변 관련
    "a healthy green plant leaf",
    "a plant leaf with brown spots and blight disease",
    "a plant leaf with white powdery mildew fungus",
    "a plant leaf with yellow mosaic virus pattern",
    "a plant leaf with orange rust spots on the underside",
    "a plant leaf curling and deformed",
    "a plant leaf with gray mold on the surface",
    "a plant leaf with bacterial dark spots and holes",
    "a plant leaf with scab and rot damage",
    # 상태 관련
    "a wilting drooping plant that needs water",
    "a plant with yellowing leaves from overwatering",
    "a plant with brown crispy leaf tips from dryness",
    "a plant with leggy stretched growth from low light",
    "a plant with sunburned bleached leaves",
    "a plant with pest insects on leaves",
    "a plant with root rot and mushy stems",
    "a plant with nutrient deficiency pale leaves",
    "a newly repotted plant in fresh soil",
]

# 한글 매핑
CONDITION_KOREAN = {
    "a healthy green plant leaf": "건강한 녹색 잎",
    "a plant leaf with brown spots and blight disease": "갈색 반점과 마름병",
    "a plant leaf with white powdery mildew fungus": "흰가루병 (곰팡이)",
    "a plant leaf with yellow mosaic virus pattern": "모자이크 바이러스 패턴",
    "a plant leaf with orange rust spots on the underside": "녹병 (주황색 포자)",
    "a plant leaf curling and deformed": "잎 말림/변형",
    "a plant leaf with gray mold on the surface": "잿빛곰팡이",
    "a plant leaf with bacterial dark spots and holes": "세균성 반점 (구멍)",
    "a plant leaf with scab and rot damage": "딱지병/부패",
    "a wilting drooping plant that needs water": "시들고 처진 상태 (물 부족)",
    "a plant with yellowing leaves from overwatering": "과습으로 잎이 노랗게",
    "a plant with brown crispy leaf tips from dryness": "건조해서 잎 끝이 갈변",
    "a plant with leggy stretched growth from low light": "빛 부족으로 웃자람",
    "a plant with sunburned bleached leaves": "직사광 화상",
    "a plant with pest insects on leaves": "벌레/해충",
    "a plant with root rot and mushy stems": "뿌리 무름",
    "a plant with nutrient deficiency pale leaves": "영양 부족 (잎 창백)",
    "a newly repotted plant in fresh soil": "새로 분갈이한 식물",
}


def analyze_image(image_path: str, top_k: int = 3) -> list[dict]:
    """
    이미지를 CLIP으로 분석하여 상위 k개 상태 반환.

    Args:
        image_path: 이미지 파일 경로
        top_k: 반환할 상위 결과 수

    Returns:
        [{"condition": "갈색 반점과 마름병", "confidence": 0.82, "en": "..."}, ...]
    """
    _load_clip()

    # 이미지 로드 (한글 경로 대응)
    image = Image.open(image_path).convert("RGB")

    # CLIP 추론
    inputs = _processor(
        text=PLANT_CONDITIONS,
        images=image,
        return_tensors="pt",
        padding=True
    ).to(_device)

    with torch.no_grad():
        outputs = _model(**inputs)
        logits = outputs.logits_per_image[0]  # [num_texts]
        probs = logits.softmax(dim=0)

    # 상위 k개
    top_probs, top_indices = probs.topk(top_k)

    results = []
    for prob, idx in zip(top_probs, top_indices):
        en_text = PLANT_CONDITIONS[idx.item()]
        results.append({
            "condition": CONDITION_KOREAN.get(en_text, en_text),
            "condition_en": en_text,
            "confidence": round(prob.item(), 3),
        })

    return results


def describe_plant_state(image_path: str) -> str:
    """
    이미지를 분석하여 한글 텍스트 설명 반환.
    LLM 프롬프트에 바로 넣을 수 있는 형태.

    Returns:
        "이 식물은 갈색 반점과 마름병(82%), 과습으로 잎이 노랗게(12%) 상태입니다."
    """
    results = analyze_image(image_path, top_k=3)

    if not results:
        return "식물 상태를 분석하지 못했습니다."

    parts = []
    for r in results:
        if r["confidence"] >= 0.05:  # 5% 이상만
            parts.append(f"{r['condition']}({r['confidence']*100:.0f}%)")

    if not parts:
        return "식물 상태가 명확하지 않습니다."

    return f"CLIP 분석 결과: {', '.join(parts)}"


# ==========================================
# 테스트
# ==========================================
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("사용법: python -m src.inference.clip_analyzer <이미지경로>")
        sys.exit(1)

    path = sys.argv[1]
    print(f"분석 중: {path}")
    results = analyze_image(path)
    for r in results:
        print(f"  {r['condition']}: {r['confidence']*100:.1f}%")
    print()
    print(describe_plant_state(path))
```

---

## 단계 2: 진단 파이프라인에 CLIP 통합

### 파일: src/inference/diagnosis.py (또는 해당 파일) 수정

```python
# 기존 진단 함수에 CLIP 폴백 추가

async def diagnose_plant(image_path: str, nickname: str = ""):
    """
    1. EfficientNet으로 병변 분류
    2. 신뢰도 < 70%이면 CLIP 보완
    3. SAM으로 세그멘테이션
    4. 결과 반환
    """
    # Step 1: EfficientNet 병변 분류
    disease_result = classify_disease(image_path)  # 기존 함수
    disease_name = disease_result["name"]
    confidence = disease_result["confidence"]

    # Step 2: 신뢰도 낮으면 CLIP 보완
    clip_description = ""
    if confidence < 0.70:
        from src.inference.clip_analyzer import describe_plant_state
        clip_description = describe_plant_state(image_path)
        logger.info(f"CLIP 보완: {clip_description}")

    # Step 3: SAM 세그멘테이션
    sam_result = segment_lesion(image_path)  # 기존 함수

    # Step 4: 결과 조합
    result = {
        "disease": {
            "name": disease_name,
            "confidence": confidence,
        },
        "lesion": {
            "ratio": sam_result["ratio"],
        },
        "clip": {
            "used": bool(clip_description),
            "description": clip_description,
        },
        "species": classify_species(image_path),  # 기존 함수
        "overlay_image": sam_result.get("overlay_base64", ""),
    }

    return result
```

---

## 단계 3: LLM 가이드에 CLIP 정보 전달

### 파일: src/inference/llm.py 수정

```python
async def generate_care_guide_from_db(disease_name, lesion_ratio, nickname, clip_description=""):
    """
    MCP → DB 조회 → LLM 톤 변환.
    CLIP 설명이 있으면 추가 컨텍스트로 활용.
    """
    from src.mcp_client import plant_db

    disease_info = await plant_db.get_disease_info(disease_name)

    # 심각도 판단
    if lesion_ratio <= 0.10:
        severity = "초기"
    elif lesion_ratio <= 0.25:
        severity = "중기"
    else:
        severity = "후기"

    # DB에 정보가 있는 경우
    if "error" not in disease_info:
        prompt = f"""{BOONZ_PERSONA}

[검증된 전문 정보]
병명: {disease_info['korean_name']}
치료법: {disease_info['treatment']}
예방법: {disease_info['prevention']}
회복 기간: {disease_info['recovery_days']}
현재 상태: {severity} (병변 {lesion_ratio*100:.1f}%)

{f"[CLIP 추가 분석] {clip_description}" if clip_description else ""}

위 정보를 {nickname}의 시점에서 분즈 톤으로 전달해줘.
3~5문장. 마지막에 위로 한 마디."""

    # DB에 없고, CLIP 설명이 있는 경우 (12클래스 밖)
    elif clip_description:
        prompt = f"""{BOONZ_PERSONA}

[CLIP 이미지 분석 결과]
{clip_description}

EfficientNet이 확실하게 분류하지 못한 케이스야.
CLIP 분석 결과를 바탕으로 {nickname}한테 조언해줘.
확실하지 않은 부분은 "정확하진 않은데"라고 전제하고 답해.
3~5문장. {nickname}의 시점에서 분즈 톤으로."""

    # 둘 다 없는 경우
    else:
        prompt = f"""{BOONZ_PERSONA}
{nickname}의 상태를 정확히 파악하기 어려워.
"잘 모르겠는데, 사진을 더 가까이에서 찍어줘"라고 답해."""

    return _call_llm(prompt)
```

---

## 단계 4: FastAPI 엔드포인트 수정

### /diagnose 응답에 CLIP 필드 추가

```python
@app.post("/diagnose")
async def diagnose(file: UploadFile, nickname: str = ""):
    # ... 기존 코드 ...

    result = await diagnose_plant(temp_path, nickname)

    # CLIP 사용 여부를 분즈 메시지에 반영
    confidence = result["disease"]["confidence"]
    lesion_ratio = result["lesion"]["ratio"]
    clip_used = result["clip"]["used"]

    if confidence >= 0.70:
        mood = "worried" if lesion_ratio > 0.05 else "happy"
        disease_kr = DISEASE_KOREAN.get(result["disease"]["name"], result["disease"]["name"])
        msg = get_boonz_diagnosis_message(disease_kr, lesion_ratio, nickname)
    else:
        mood = "default"
        msg = f"{nickname} 상태가 좀 복잡한데... CLIP으로 좀 더 살펴봤어. {result['clip']['description']}"

    result["boonz"] = {"mood": mood, "message": msg}
    return result
```

---

## 단계 5: 테스트

```bash
# CLIP 단독 테스트
python -c "
from src.inference.clip_analyzer import analyze_image, describe_plant_state

# 테스트 이미지로
results = analyze_image('test_leaf.jpg')
for r in results:
    print(f'{r[\"condition\"]}: {r[\"confidence\"]*100:.1f}%')

print()
print(describe_plant_state('test_leaf.jpg'))
"

# EfficientNet + CLIP 통합 테스트
curl -X POST http://localhost:8000/diagnose \
  -F "file=@test_leaf.jpg" \
  -F "nickname=마리"

# 응답에서 clip.used 확인
# confidence >= 70%: clip.used = false
# confidence < 70%: clip.used = true, clip.description 있음
```

---

## 발표 멘트

```
"EfficientNet은 12클래스 병변을 97.9%로 분류합니다.
 근데 학습하지 않은 증상이 오면 어떻게 할까요?

 신뢰도가 70% 미만이면 CLIP이 보완합니다.
 CLIP은 이미지를 '갈색 반점과 마름병 82%, 과습 12%'처럼
 텍스트로 설명해요.

 이 설명을 LLM에 전달하면
 12클래스 밖의 증상도 가이드를 생성할 수 있습니다.

 EfficientNet이 확신하면 → DB에서 검증된 정보
 확신 못 하면 → CLIP 설명 → LLM이 추론

 정확도와 커버리지 둘 다 잡는 구조입니다."
```

---

## 최종 기술 스택

```
비전:
  EfficientNet-B3 병변 12cls (97.9%)  — 1차 분류
  EfficientNet-B3 종 47cls (88.2%)   — 종 식별
  SAM vit_b                          — 세그멘테이션
  CLIP vit-base-patch32              — 저신뢰 폴백 (NEW)

LLM:
  OpenAI API (우선) → Ollama (폴백)

데이터:
  MCP + SQLite                       — 검증된 지식 DB

알고리즘:
  관계 성장 (연속성×다양성×반응성)
  돌봄 유형 분류
  개인화 추천
```

---

## 적용 순서 (Claude Code)

```
1. pip install transformers --break-system-packages
2. src/inference/clip_analyzer.py 생성
3. 진단 파이프라인에 CLIP 폴백 조건 추가
4. llm.py에 clip_description 파라미터 추가
5. FastAPI /diagnose에 clip 필드 추가
6. 테스트: 고신뢰 이미지 + 저신뢰 이미지 둘 다
```
