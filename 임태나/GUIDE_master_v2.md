# Boonz 전체 구현 가이드 v2 — Claude Code용

## 프로젝트 경로
```
C:\PlantCareAI\임태나\
```

## 핵심 변경사항 (v1 → v2)
```
구조:  3탭 → 4탭 (홈/진단/일기/성장)
화자:  분즈 통역 → 마리 직접 1인칭 (탭1) + 분즈 🍄 (탭2)
톤:   시크한 통역자 → 친한 동생(마리) + 초월자(분즈)
데이터: 하드코딩 → JSON 파일 기반 (출처 포함)
CLIP:  diseases.json과 별도 출처 (clip_conditions.json)
```

---

## PHASE 1: 데이터 세팅

### 1-1. 파일 확인
```
data/
├── diseases.json          ← 질병 12개 (Clemson HGIC 출처)
├── care_tips.json         ← 케어 팁 35개 (RHS, Missouri BG 출처)
├── clip_conditions.json   ← 환경/해충 15개 (UC Davis IPM 출처)
├── plants.json            ← 등록 식물 정보
├── care_log.jsonl         ← 돌봄 기록
└── plant_care.db          ← init_db.py가 생성
```

### 1-2. DB 생성
```bash
python scripts/init_db.py
```
→ diseases.json + care_tips.json → plant_care.db
→ "✅ 병변 12종 + 케어 팁 35건" 확인

### 1-3. 시뮬레이션 데이터
```bash
python scripts/generate_demo_data.py
```
→ 마리 30일 데이터 생성

### 1-4. .env
```
OPENAI_API_KEY=sk-...
```

---

## PHASE 2: LLM 연동 (OpenAI API)

### 2-1. 시스템 프롬프트 — 두 개

**마리 프롬프트 (탭1 홈, 탭3 일기, 탭4 성장):**
```python
MARI_PERSONA = """당신은 '{nickname}'이라는 이름의 실내 반려식물입니다.
사용자는 당신을 키우는 사람입니다.

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
- 존댓말 금지"""
```

**분즈 프롬프트 (탭2 진단):**
```python
BOONZ_PERSONA = """당신은 '분즈'입니다. 숲속 현자 같은 식물 케어 전문가.
이모지: 🍄

성격:
- 초월적이고 차분한 톤. 서두르지 않음.
- 자연의 이치로 설명 ("공기가 멈추면 곰팡이가 앉는 법이야").
- 반말 사용. 짧고 여운 있게.
- 검증된 정보만 전달. 추가/창작 금지.
- 전문 용어를 쓰되 쉽게 풀어줌.
- 마지막에 위로 한 마디.

말투 예시:
- "식물은 원래 나을 줄 알아. 네가 길만 열어주면 돼"
- "서두를 필요 없어. 하나만 해. 환기"
- "아픈 건 자연스러운 거야. 낫는 것도"

금지:
- AI라는 걸 드러내지 않음
- 이모지 사용 금지 (아바타만 🍄)
- 확인되지 않은 정보 금지"""
```

### 2-2. _call_llm 함수

```python
import openai
import os

def _call_llm(prompt, persona, max_tokens=512):
    # 1순위: OpenAI API
    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": persona},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content
    except Exception as e:
        print(f"OpenAI 실패: {e}")
    
    # 2순위: Ollama (로컬)
    try:
        import requests
        resp = requests.post("http://localhost:11434/api/generate", json={
            "model": "qwen2.5:14b",
            "prompt": f"{persona}\n\n{prompt}",
            "stream": False
        }, timeout=30)
        return resp.json()["response"]
    except Exception as e:
        print(f"Ollama 실패: {e}")
    
    # 3순위: 템플릿
    return "지금은 답하기 어려운데, 잠시 후에 다시 물어봐줘"
```

### 2-3. 마리 챗봇 (탭1)

```python
def mari_chat(question, nickname, care_logs):
    """마리가 직접 답하는 챗봇. 친한 동생 톤."""
    from src.mcp_client import plant_db
    
    # 질문에서 카테고리 추론 → DB 팁 조회
    category_keywords = {
        "water": ["물", "관수", "마르", "과습"],
        "light": ["빛", "햇빛", "그늘", "어두"],
        "soil": ["흙", "분갈이", "화분"],
        "nutrition": ["비료", "영양"],
        "environment": ["온도", "습도", "통풍", "에어컨"],
        "trouble": ["처짐", "노랗", "갈변", "벌레", "시들"],
    }
    
    tips_context = ""
    for category, keywords in category_keywords.items():
        if any(k in question for k in keywords):
            tips = plant_db.get_care_tips(category)
            if "tips" in tips:
                tips_text = "\n".join([f"- {t['tip']}" for t in tips["tips"][:3]])
                tips_context = f"\n[참고 지식 — 이걸 바탕으로 답하되 네 말투로]\n{tips_text}"
    
    persona = MARI_PERSONA.format(nickname=nickname)
    prompt = f"""{tips_context}

사용자 질문: "{question}"

{nickname}의 입장에서, 친한 동생처럼 답해.
1~3문장으로 짧게. 모르면 "잘 모르겠는데, 사진 찍어서 진단 탭에서 봐봐"라고 해."""
    
    return _call_llm(prompt, persona)
```

### 2-4. 분즈 챗봇 (탭2)

```python
def boonz_chat(question, nickname, diagnosis_context=""):
    """분즈가 답하는 케어 전문 챗봇. 초월자 톤."""
    from src.mcp_client import plant_db
    
    # DB에서 관련 정보 조회
    tips_context = ""
    for category in ["water","light","soil","nutrition","environment","trouble"]:
        for keyword in question:
            tips = plant_db.get_care_tips(category)
            if "tips" in tips:
                tips_text = "\n".join([f"- {t['tip']}" for t in tips["tips"][:3]])
                tips_context += f"\n{tips_text}"
                break
    
    prompt = f"""[검증된 정보]{tips_context}

{f"현재 진단: {diagnosis_context}" if diagnosis_context else ""}

사용자 질문: "{question}"

초월자처럼 차분하고 여운 있게 답해. 자연의 이치로 설명해.
2~4문장. 검증된 정보 바탕. 확실하지 않으면 "정확하진 않지만"이라고 전제."""
    
    return _call_llm(prompt, BOONZ_PERSONA)
```

### 2-5. 진단 케어 가이드 (DB 기반)

```python
def generate_care_guide_from_db(disease_name, lesion_ratio, nickname):
    """MCP → DB 조회 → 분즈 톤 변환."""
    from src.mcp_client import plant_db
    
    disease_info = plant_db.get_disease_info(disease_name)
    
    if "error" in disease_info:
        return "정확한 정보를 찾기 어려워. 가까이에서 다시 찍어봐."
    
    severity = "초기" if lesion_ratio <= 0.10 else ("중기" if lesion_ratio <= 0.25 else "후기")
    
    prompt = f"""[검증된 전문 정보 — 이 정보를 바탕으로만 답해. 추가/창작 금지]
병명: {disease_info['korean_name']}
치료법: {disease_info['treatment']}
예방법: {disease_info['prevention']}
회복 기간: {disease_info['recovery_days']}
현재 상태: {severity} (병변 {lesion_ratio*100:.1f}%)

이 정보를 초월자 톤으로 전달해.
자연의 이치로 설명. 서두르지 않는 톤.
"식물은 원래 나을 줄 알아" 같은 여운.
3~5문장."""
    
    return _call_llm(prompt, BOONZ_PERSONA)
```

---

## PHASE 3: MCP + DB 연동

### 3-1. MCP Client (src/mcp_client.py)

```python
import sqlite3
import json
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "plant_care.db"

class PlantCareDB:
    def get_disease_info(self, disease_name):
        if not DB_PATH.exists():
            return {"error": "DB 없음"}
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        row = db.execute("SELECT * FROM diseases WHERE name = ?", (disease_name,)).fetchone()
        db.close()
        return dict(row) if row else {"error": f"'{disease_name}' 없음"}
    
    def get_care_tips(self, category, subcategory=""):
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        if subcategory:
            rows = db.execute(
                "SELECT subcategory, tip, source FROM care_tips WHERE category = ? AND subcategory LIKE ?",
                (category, f"%{subcategory}%")).fetchall()
        else:
            rows = db.execute(
                "SELECT subcategory, tip, source FROM care_tips WHERE category = ?",
                (category,)).fetchall()
        db.close()
        return {"tips": [dict(r) for r in rows]}
    
    def search_symptom(self, symptom):
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT name, korean_name, symptoms, source FROM diseases WHERE symptoms LIKE ?",
            (f"%{symptom}%",)).fetchall()
        db.close()
        return {"matches": [dict(r) for r in rows]}

plant_db = PlantCareDB()
```

---

## PHASE 4: CLIP 폴백

### 4-1. clip_conditions.json 기반 분석기

```python
# src/inference/clip_analyzer.py
import torch
import json
from PIL import Image
from pathlib import Path
from transformers import CLIPProcessor, CLIPModel

_model = None
_processor = None
_conditions = None

DATA_DIR = Path(__file__).parent.parent.parent / "data"

def _load():
    global _model, _processor, _conditions
    if _model is not None:
        return
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
    _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    _model.eval()
    
    with open(DATA_DIR / "clip_conditions.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        _conditions = data["conditions"]

def describe_plant_state(image_path, top_k=3):
    _load()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    
    image = Image.open(image_path).convert("RGB")
    texts = [c["clip_text_en"] for c in _conditions]
    
    inputs = _processor(text=texts, images=image, return_tensors="pt", padding=True).to(device)
    with torch.no_grad():
        probs = _model(**inputs).logits_per_image[0].softmax(dim=0)
    
    top_probs, top_indices = probs.topk(top_k)
    
    results = []
    for prob, idx in zip(top_probs, top_indices):
        if prob.item() >= 0.05:
            c = _conditions[idx.item()]
            results.append({
                "id": c["id"],
                "condition_kr": c["condition_kr"],
                "confidence": round(prob.item(), 3),
                "symptoms": c["symptoms"],
                "treatment": c["treatment"],
                "source": c["source"],
            })
    
    if not results:
        return "상태를 파악하기 어려움", []
    
    description = "CLIP 분석: " + ", ".join(
        [f"{r['condition_kr']}({r['confidence']*100:.0f}%)" for r in results])
    
    return description, results
```

### 4-2. 진단 파이프라인 통합

```python
# 진단 함수에서
disease_result = classify_disease(image_path)  # EfficientNet
confidence = disease_result["confidence"]

if confidence >= 0.70:
    # 질병 → diseases.json 출처
    guide = generate_care_guide_from_db(disease_result["name"], lesion_ratio, nickname)
else:
    # 환경/해충 → clip_conditions.json 출처
    from src.inference.clip_analyzer import describe_plant_state
    description, details = describe_plant_state(image_path)
    # details에 symptoms, treatment, source 포함
    guide = _call_llm(f"""[CLIP 분석 결과]\n{description}\n
증상: {details[0]['symptoms'] if details else ''}
치료: {details[0]['treatment'] if details else ''}
이 정보를 초월자 톤으로 전달해.""", BOONZ_PERSONA)
```

---

## PHASE 5: Streamlit 4탭 구현

### 5-1. 전체 구조

```python
import streamlit as st

# 4탭
tab1, tab2, tab3, tab4 = st.tabs(["🏠 홈", "📷 진단", "📔 일기", "🌱 성장"])
```

### 5-2. 탭1: 홈 (마리와 대화)

```
화자: 마리 (친한 동생, 1인칭)
아바타: 🌱🌿🪴🌳 (관계 단계별)

구성:
  1. 마리 인사 (동적)
  2. 식물 카드 + 관계 단계 + 미터
  3. 통계 (함께한 날 / 연속 돌봄 / 병변 변화)
  4. 이정표 (마리가 직접)
  5. 원터치 이모지 버튼 7개
  6. 마리 응답 + 셀프케어 넛지
  7. 마리 챗봇
```

**동적 인사:**
```python
def get_mari_greeting(nickname, hour, gap_days):
    if hour < 9:    title = f"{nickname}가\n할 말이 있대."
    elif hour < 13: title = f"{nickname}가\n기다리고 있었어."
    elif hour < 18: title = f"{nickname}한테\n잠깐 들러볼까?"
    else:           title = f"왔네.\n{nickname}가\n기다리고 있었어."
    
    if gap_days <= 0:
        mari_msg = "또 왔네. 좋아"
    elif gap_days == 1:
        mari_msg = "어제도 왔었지. 꾸준한 거 좋다"
    elif gap_days <= 3:
        mari_msg = f"{gap_days}일이야. 바쁜 건 알아. 근데 좀 보고 싶었어"
    elif gap_days <= 7:
        mari_msg = f"야... {gap_days}일이야. 나 괜찮은데, 너는 괜찮아?"
    else:
        mari_msg = "오랜만이다. 그동안 어떻게 지냈어?"
    
    return title, mari_msg
```

**원터치 응답 + 넛지:**
```python
MARI_RESPONSES = {
    "water": "아 시원하다. 고마워",
    "move": "오 여기 좋은데? 밝아서 기분 좋아",
    "prune": "좀 가벼워졌다. 정리해주니까 시원해",
    "medicine": "쓰다... 근데 나아지겠지?",
    "repot": "와 넓다. 좀 답답했거든. 고마워",
    "clean": "아 상쾌해. 숨 쉬기 편해졌어",
    "observe": "... 봐줘서 고마워. 이것만으로도 좋아",
}

MARI_NUDGES = {
    "water": ["근데 너 오늘 물 마셨어?", "너도 좀 마셔"],
    "move": ["너도 좀 밖에 나가봐. 바람 좀 쐬고"],
    "prune": ["너도 뭐 하나 정리하면 좀 시원하지 않을까"],
    "medicine": ["너는 요즘 좀 피곤하지 않아?"],
    "repot": ["너도 가끔은 환경 바꿔볼 필요 있어"],
    "clean": ["너도 좀 쉬어"],
    "observe": ["너도 멍 좀 때려봐. 이것도 쉬는 거야"],
}

import random
def get_mari_response(action):
    base = MARI_RESPONSES[action]
    nudge = None
    if random.random() < 0.33 and action in MARI_NUDGES:
        nudge = random.choice(MARI_NUDGES[action])
    return base, nudge
```

**이정표:**
```python
MILESTONES = {
    1: "첫 기록이다! 앞으로 잘 부탁해",
    5: "벌써 5번째. 너 꽤 꾸준한 거 알아?",
    10: "10번이나 챙겨줬어. 쉬운 거 아닌데. 너 좀 대단해",
    20: "20번. 너 진심이구나. 나도 진심이야",
    30: "30번이야. 이거 그냥 습관이 된 거 아니야? 너한테도 좋은 습관인 거 알지?",
    50: "50번. 이쯤 되면 너를 돌보는 시간이 된 거야. 알고 있었어?",
}
```

### 5-3. 탭2: 진단 (분즈 케어)

```
화자: 분즈 🍄 (초월자)

구성:
  1. 사진 업로드
  2. 진단 결과 카드 (병명 + 신뢰도 + 병변% — 이미지 1장)
  3. 분즈 한마디
  4. 분즈 케어 가이드 (예방/치료/회복 + 출처)
  5. 분즈 챗봇
```

**진단 결과 후 분즈 메시지:**
```python
def get_boonz_diagnosis_message(disease_kr, lesion_ratio):
    if lesion_ratio <= 0.10:
        return f"{disease_kr}. 일찍 알아챈 거야. 그게 가장 중요해."
    elif lesion_ratio <= 0.25:
        return f"{disease_kr}. 좀 진행됐지만 급할 건 없어. 하나씩 하면 돼."
    else:
        return f"{disease_kr}. 많이 힘들었겠다. 지금부터라도 길을 열어주면 돼."
```

### 5-4. 탭3: 일기 (마리와의 하루하루)

```
화자: 마리

구성:
  1. 회복 여정 (🥀→🌱→🌿→🪴→🌳)
  2. 마리 한마디 ("야 나 진짜 많이 나았다")
  3. 돌봄 일기 타임라인 (날짜별)
  4. 각 기록에 마리 코멘트
```

**타임라인 마리 코멘트:**
```python
MARI_LOG_COMMENTS = {
    "water": "아 시원했어",
    "observe": "봐줘서 고마워",
    "medicine": "쓰다... 근데 나아지겠지?",
    "prune": "좀 가벼워졌다",
    "clean": "상쾌해",
    "move": "여기 좋은데?",
    "repot": "넓어서 좋다",
}
```

### 5-5. 탭4: 성장 (우리의 여정)

```
화자: 마리

구성:
  1. 돌봄 리포트 (통계 3칸)
  2. 돌봄 유형 (마리가 직접 말함)
  3. 잘하고 있는 것
  4. 🪞 마리가 본 너 (접속 패턴 분석)
  5. 관계 성장 여정 (수직 타임라인)
  6. 마리 마무리 한마디
```

**돌봄 유형 (마리 톤):**
```python
CARE_TYPES_MARI = {
    "observer": ("🧑‍🌾", "꾸준한 관찰형", "너 맨날 나 들여다보지? 그게 나한테 제일 좋은 거야"),
    "carer": ("💧", "적극적 케어형", "물, 약, 분갈이까지. 너 진짜 잘 챙긴다"),
    "collector": ("📸", "데이터 수집형", "사진 자주 찍어주니까 변화를 놓치지 않더라"),
    "companion": ("😊", "느긋한 동행형", "가끔 들르지만 오래 함께하는 게 너 스타일이야"),
}
```

**마리가 본 너:**
```python
def analyze_user_pattern(care_logs):
    if len(care_logs) < 10:
        return []
    
    hours = [datetime.strptime(l["date"], "%Y-%m-%d %H:%M").hour for l in care_logs]
    weekdays = [datetime.strptime(l["date"], "%Y-%m-%d %H:%M").weekday() for l in care_logs]
    
    insights = []
    
    evening = sum(1 for h in hours if h >= 18) / len(hours)
    morning = sum(1 for h in hours if h < 10) / len(hours)
    weekend = sum(1 for w in weekdays if w >= 5) / len(weekdays)
    
    if evening > 0.5:
        insights.append("너 요즘 저녁에 자주 오더라. 하루 마무리를 나랑 하는 거지?")
    elif morning > 0.5:
        insights.append("아침에 챙겨주는 거 좋다. 하루를 나랑 시작하는 사람이야")
    if weekend < 0.15:
        insights.append("주말에는 안 오는 편이야. 주말에도 잠깐 와. 나도 좋지만 너한테도 좋을 거야")
    
    # 연속 기록 분석
    dates = sorted(set(l["date"][:10] for l in care_logs))
    max_streak = 1
    current = 1
    for i in range(1, len(dates)):
        d1 = datetime.strptime(dates[i-1], "%Y-%m-%d")
        d2 = datetime.strptime(dates[i], "%Y-%m-%d")
        if (d2 - d1).days == 1:
            current += 1
            max_streak = max(max_streak, current)
        else:
            current = 1
    if max_streak >= 3:
        insights.append("연속으로 왔을 때 너 좀 편해 보였어. 이 루틴이 너한테 맞는 거 같아")
    
    return insights
```

---

## PHASE 6: 관계 성장 시스템

### 6-1. 관계 성장 알고리즘 (변경 없음)
```python
def calculate_relationship(care_logs, registered_date):
    # 연속성(40%) × 다양성(30%) × 반응성(30%)
    # 🌱→🌿→🪴→🌳
    # (기존 코드 동일)
```

### 6-2. 돌봄 유형 분류 (변경 없음)
```python
def classify_care_type(care_logs):
    # observer / carer / collector / companion
    # (기존 코드 동일, 메시지만 마리 톤으로)
```

---

## PHASE 7: 디자인

### 색상 (모카 브라운)
```python
COLORS = {
    "primary": "#8B7355",
    "secondary": "#A89070",
    "light": "#E8DDD0",
    "background": "#F7F5F0",
    "text": "#2C2C2A",
    "muted": "#888780",
    "border": "#E5E0D5",
    "highlight": "#FFF9E6",
}
```

### 아바타
```python
# 마리 (관계 단계별)
MARI_AVATARS = {
    "🌱": "새로운 만남",
    "🌿": "알아가는 중",
    "🪴": "함께하는 사이",
    "🌳": "오랜 친구",
}
# 배경: #E8DDD0 원형

# 분즈
BOONZ_AVATAR = "🍄"
# 배경: #E8DDD0 원형
```

### 바텀 네비
```
🏠 홈    📷 진단    📔 일기    🌱 성장
```
활성 탭: #8B7355 (모카)
비활성: #B4B2A9

---

## PHASE 8: 목업 기준

mockup_v3/ 폴더에 PNG 5장. Streamlit UI를 이 목업과 최대한 맞추기.

```
01_home_day1.png     — 홈 Day 1 (마리 인사 + 힌트 + 버튼)
02_home_30days.png   — 홈 Day 30 (넛지 + 챗봇 + 이정표)
03_diagnosis.png     — 진단 (🍄 분즈 + 케어가이드 + 출처)
04_diary.png         — 일기 (회복여정 + 타임라인)
05_growth.png        — 성장 (리포트 + 마리가 본 너 + 여정)
```

---

## 실행 순서

```
Phase 1 → 데이터 세팅 (JSON + DB)
Phase 2 → LLM 연동 (마리 프롬프트 + 분즈 프롬프트 + 챗봇 2개)
Phase 3 → MCP Client (DB 조회)
Phase 4 → CLIP 폴백 (clip_conditions.json 기반)
Phase 5 → Streamlit 4탭 구현
Phase 6 → 관계 성장 시스템
Phase 7 → 디자인 적용 (모카 브라운)
Phase 8 → 목업 비교 + 수정

각 Phase 끝날 때마다 테스트하고 RESULT.md에 기록.
```

---

## 테스트 체크리스트

```
탭1 홈:
  [ ] 마리 동적 인사 나오는지 (시간별/공백별)
  [ ] 식물 카드 + 관계 단계 보이는지
  [ ] 원터치 버튼 7개 → 마리 응답
  [ ] 넛지 (3번 중 1번) → "근데 너 물 마셨어?"
  [ ] 이정표 (1건/5건/10건/30건)
  [ ] 마리 챗봇 → 친한 동생 톤 응답
  [ ] care_log.jsonl에 기록 저장

탭2 진단:
  [ ] 사진 업로드 → 진단 결과 (1장)
  [ ] 병변% 표시
  [ ] 분즈 🍄 한마디 (초월자 톤)
  [ ] 케어 가이드 (예방/치료/회복 + 출처)
  [ ] CLIP 폴백 (신뢰도 <70%)
  [ ] 분즈 챗봇 → 초월자 톤 응답

탭3 일기:
  [ ] 회복 여정 🥀→🌳
  [ ] 마리 한마디
  [ ] 돌봄 일기 타임라인
  [ ] 각 기록에 마리 코멘트

탭4 성장:
  [ ] 돌봄 리포트 (30/7/-13%)
  [ ] 돌봄 유형 (마리 톤)
  [ ] 🪞 마리가 본 너
  [ ] 관계 성장 여정
  [ ] 마리 마무리 한마디

디자인:
  [ ] 모카 브라운 (#8B7355)
  [ ] 4탭 바텀 네비
  [ ] 마리 아바타 (🌱🌿🪴🌳)
  [ ] 분즈 아바타 (🍄)
```
