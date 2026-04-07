# Boonz 전체 구현 가이드 — Claude Code용

## 프로젝트 경로
```
C:\PlantCareAI\임태나\
```

## 현재 있는 것
```
models/disease/efficientnet_b3_disease_type_best.pth  (129MB, 12cls)
models/species/species_model_best.pth                 (130MB, 47cls)
models/sam/sam_vit_b_01ec64.pth                       (375MB)
data/plants.json
data/care_log.jsonl
data/plant_care.db
```

## 구현할 전체 기능 목록

---

## PHASE 1: 기본 동작 확인 (먼저)

### 1-1. FastAPI 서버 실행 확인
```bash
cd C:\PlantCareAI\임태나
uvicorn src.api.main:app --reload --port 8000
```
에러 나면 고치기. 모델 경로, import 경로 확인.

### 1-2. Streamlit 실행 확인
```bash
streamlit run src/frontend/app.py --server.port 8501
```
에러 나면 고치기.

### 1-3. 모델 로드 확인
```python
# 테스트
import torch
from src.inference.disease import load_model
model = load_model("models/disease/efficientnet_b3_disease_type_best.pth")
print("✅ 병변 모델 로드 OK")
```

---

## PHASE 2: 셀프케어 핵심 기능 구현

### 2-1. 원터치 이모지 버튼 + 셀프케어 넛지

**app.py에서 구현:**

```python
# 7개 이모지 버튼 (C형 카드, 4열 그리드)
CARE_ACTIONS = [
    {"emoji": "💧", "label": "물줬음", "action": "water"},
    {"emoji": "☀️", "label": "자리옮김", "action": "move"},
    {"emoji": "✂️", "label": "가지치기", "action": "prune"},
    {"emoji": "💊", "label": "약줬음", "action": "medicine"},
    {"emoji": "🪴", "label": "분갈이", "action": "repot"},
    {"emoji": "🍃", "label": "잎닦음", "action": "clean"},
    {"emoji": "😊", "label": "그냥봄", "action": "observe"},
]

# 분즈 기본 응답
CARE_RESPONSES = {
    "water": ["{nickname}한테 전해놨어! 물 받아서 좋아하겠다"],
    "move": ["{nickname} 새 자리 마음에 들어하겠다"],
    "prune": ["정리해줬구나. 한결 가벼워졌을 거야"],
    "medicine": ["네가 옆에 있어서 든든할 거야"],
    "repot": ["너 진짜 잘 챙긴다"],
    "clean": ["{nickname} 상쾌하대"],
    "observe": ["가만히 봐주는 것도 돌봄이야"],
}

# 셀프케어 넛지 (3번 중 1번 랜덤)
SELFCARE_NUDGES = {
    "water": ["근데 너는? 오늘 물 충분히 마셨어?", "너도 오늘 따뜻한 거 한 잔 마셔"],
    "move": ["너도 오늘 좀 환기시켜", "가끔은 너도 다른 자리에 앉아봐"],
    "prune": ["너도 오늘 뭐 하나 내려놓아도 괜찮아"],
    "medicine": ["너도 요즘 좀 피곤하지 않아?"],
    "repot": ["가끔은 너도 환경을 바꿔볼 필요가 있어"],
    "clean": ["너도 오늘 좀 쉬어"],
    "observe": ["너도 오늘 잠깐 멍 때려봐", "가만히 있는 것도 쉬는 거야"],
}

import random

def get_care_response(action, nickname):
    base_msg = random.choice(CARE_RESPONSES[action]).format(nickname=nickname)
    # 3번 중 1번만 셀프케어 넛지
    if random.random() < 0.33 and action in SELFCARE_NUDGES:
        nudge = random.choice(SELFCARE_NUDGES[action])
        return base_msg, nudge  # 넛지 있음
    return base_msg, None  # 넛지 없음
```

**UI:**
- 4열 그리드로 이모지 카드 배치
- 클릭 시 care_log.jsonl에 기록 추가
- 분즈 말풍선으로 응답
- 넛지 있으면 노란 카드로 "너한테도" 표시

### 2-2. 분즈 오프너 5가지 랜덤

```python
OPENERS = [
    ("{nickname}한테 물어봤는데, ", 0.50),
    ("이건 내 생각인데, ", 0.20),
    ("솔직히 말하면, ", 0.15),
    ("...{nickname}가 너한테 할 말이 있대. ", 0.10),
    ("", 0.05),
]

def get_opener(nickname):
    r = random.random()
    cumulative = 0
    for opener, prob in OPENERS:
        cumulative += prob
        if r < cumulative:
            return opener.format(nickname=nickname)
    return f"{nickname}한테 물어봤는데, "
```

LLM 시스템 프롬프트에 오프너 주입. LLM이 이어서 쓰게 함.

### 2-3. 동적 인사 + 이정표

```python
from datetime import datetime

def get_greeting(nickname, last_date, total_logs):
    hour = datetime.now().hour
    
    # 시간별 타이틀
    if hour < 9:
        title = f"좋은 아침.\n{nickname} 오늘도 잘 있을까?"
    elif hour < 13:
        title = f"오늘은 {nickname}한테\n뭐 해줄 거야?"
    elif hour < 18:
        title = f"{nickname}한테\n잠깐 들러볼까?"
    else:
        title = f"오늘 하루 수고했어.\n{nickname}와 함께한 지\n벌써 {days}일째야."
    
    # 공백별 분즈 메시지
    if last_date:
        gap = (datetime.now() - last_date).days
    else:
        gap = -1  # 첫 방문
    
    if gap == -1 or gap == 0:
        boonz_msg = f"오늘도 {nickname} 챙겨주네. 이런 시간이 너한테도 좋은 거야"
    elif gap <= 1:
        boonz_msg = "어제도 왔었지? 꾸준한 거 좋다"
    elif gap <= 3:
        boonz_msg = f"{gap}일 만이네. 바쁜 거 알아. 근데 이런 시간이 너한테 필요한 거 아닐까?"
    elif gap <= 7:
        boonz_msg = f"{gap}일째야. {nickname}도 보고 싶어하지만, 너도 좀 쉬어야 할 거 같아서"
    else:
        boonz_msg = f"오랜만이다. 그동안 어떻게 지냈어?"
    
    return title, boonz_msg

# 이정표 (나 중심)
MILESTONES = {
    1: "첫 기록이다! 여기서부터 시작이야",
    5: "벌써 5번째. 슬슬 리듬이 생기고 있어",
    10: "10번이나 챙겼어. 뭔가를 10번이나 꾸준히 한 거야. 쉬운 거 아닌데",
    20: "20번. 너 이거 진심이구나",
    30: "30번이나 꾸준히 뭔가를 돌본 거야. 너 자신도 좀 대단하다고 생각해",
    50: "50번. 이쯤 되면 마리를 돌보는 게 아니라, 너를 돌보는 시간이 된 거야",
}
```

### 2-4. Day 1 풍성화

Day 1 (기록 0개)일 때 홈 화면에 추가:
```python
if total_logs == 0:
    # 💡 힌트 카드 표시
    st.info("💡 **첫 날이니까** 오늘은 😊 그냥봄 해줘. 그것만으로도 시작이야.\n내일 다시 오면 연속 돌봄 시작이야. 기대된다 🌱")
    
    # 챗봇 안내
    boonz_msg = f"{nickname}? 좋은 이름이야. 앞으로 내가 사이에서 통역해줄게"
```

---

## PHASE 3: 관계 성장 시스템

### 3-1. 관계 성장 알고리즘

```python
from collections import Counter
from datetime import datetime, timedelta

def calculate_relationship(care_logs, registered_date):
    if not care_logs:
        return "🌱", "새로운 만남", 0.0
    
    days = (datetime.now() - registered_date).days
    
    # 연속성 (40%): 최근 14일 중 기록한 날 / 10
    recent_14 = [l for l in care_logs 
                 if (datetime.now() - datetime.strptime(l["date"][:10], "%Y-%m-%d")).days <= 14]
    unique_days = len(set(l["date"][:10] for l in recent_14))
    continuity = min(unique_days / 10, 1.0)
    
    # 다양성 (30%): 사용한 액션 종류 / 5
    actions = set(l["action"] for l in care_logs)
    diversity = min(len(actions) / 5, 1.0)
    
    # 반응성 (30%): 진단 후 48h 내 조치 비율
    diag_logs = [l for l in care_logs if l.get("disease")]
    if diag_logs:
        responded = 0
        for diag in diag_logs:
            diag_date = datetime.strptime(diag["date"][:10], "%Y-%m-%d")
            followups = [l for l in care_logs 
                        if l["action"] in ("medicine", "water", "prune")
                        and 0 < (datetime.strptime(l["date"][:10], "%Y-%m-%d") - diag_date).days <= 2]
            if followups:
                responded += 1
        responsiveness = responded / len(diag_logs)
    else:
        responsiveness = 0.5  # 진단 없으면 중간값
    
    score = continuity * 0.4 + diversity * 0.3 + responsiveness * 0.3
    
    # 단계 결정
    if score < 0.3 and days <= 7:
        return "🌱", "새로운 만남", score
    elif score < 0.5 and days <= 30:
        return "🌿", "알아가는 중", score
    elif score < 0.7 and days <= 90:
        return "🪴", "함께하는 사이", score
    else:
        return "🌳", "오랜 친구", score
```

### 3-2. 돌봄 유형 분류

```python
def classify_care_type(care_logs):
    if len(care_logs) < 10:
        return None, None, f"아직 기록이 {len(care_logs)}개야. 조금만 더 쌓이면 패턴이 보일 거야"
    
    counts = Counter(l["action"] for l in care_logs)
    total = len(care_logs)
    
    observe_ratio = counts.get("observe", 0) / total
    action_types = len(set(counts.keys()))
    diag_count = sum(1 for l in care_logs if l.get("disease"))
    diag_ratio = diag_count / total if total > 0 else 0
    
    if observe_ratio > 0.4:
        return "🧑‍🌾", "꾸준한 관찰형", "매일 들여다봐주는 거, 제일 좋은 돌봄이야"
    elif action_types >= 5:
        return "💧", "적극적 케어형", "물, 약, 분갈이까지. 너 진짜 잘 챙긴다"
    elif diag_ratio > 0.3:
        return "📸", "데이터 수집형", "사진 자주 찍는 거 좋아. 변화를 놓치지 않으니까"
    else:
        return "😊", "느긋한 동행형", "가끔 들르지만 오래 함께하는 게 너의 스타일이야"
```

### 3-3. 🪞 마리가 본 너 (접속 패턴 분석)

```python
def analyze_user_pattern(care_logs):
    if len(care_logs) < 10:
        return []
    
    hours = []
    weekdays = []
    for log in care_logs:
        dt = datetime.strptime(log["date"], "%Y-%m-%d %H:%M")
        hours.append(dt.hour)
        weekdays.append(dt.weekday())
    
    insights = []
    
    # 시간대
    evening_ratio = sum(1 for h in hours if h >= 18) / len(hours)
    morning_ratio = sum(1 for h in hours if h < 10) / len(hours)
    if evening_ratio > 0.5:
        insights.append("너 요즘 저녁에 자주 오더라. 하루 마무리를 같이 하는 거지?")
    elif morning_ratio > 0.5:
        insights.append("아침에 챙겨주는 거 좋다. 하루를 식물로 시작하는 사람이야")
    
    # 요일
    weekend_ratio = sum(1 for w in weekdays if w >= 5) / len(weekdays)
    if weekend_ratio < 0.15:
        insights.append("주말에는 안 오는 편이야. 주말에도 잠깐 들러봐. 너한테도 좋을 거야")
    
    # 연속성
    dates = sorted(set(log["date"][:10] for log in care_logs))
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
        insights.append("연속으로 돌봤을 때 너도 좀 편해 보였어. 루틴이 너한테 맞는 거 같아")
    
    return insights
```

---

## PHASE 4: MCP + DB 연동

### 4-1. DB 초기화 확인
```bash
python scripts/init_db.py
```
이미 data/plant_care.db가 있으면 스킵 가능. 없으면 실행.

### 4-2. MCP Client 구현

파일: `src/mcp_client.py`

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
                "SELECT subcategory, tip, detail FROM care_tips WHERE category = ? AND subcategory LIKE ?",
                (category, f"%{subcategory}%")
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT subcategory, tip, detail FROM care_tips WHERE category = ?",
                (category,)
            ).fetchall()
        db.close()
        return {"tips": [dict(r) for r in rows]}
    
    def search_symptom(self, symptom):
        db = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT name, korean_name, symptoms FROM diseases WHERE symptoms LIKE ?",
            (f"%{symptom}%",)
        ).fetchall()
        db.close()
        return {"matches": [dict(r) for r in rows]}

plant_db = PlantCareDB()
```

### 4-3. LLM 가이드 — DB 정보 기반

```python
# src/inference/llm.py에 추가

def generate_care_guide_from_db(disease_name, lesion_ratio, nickname, clip_description=""):
    from src.mcp_client import plant_db
    
    disease_info = plant_db.get_disease_info(disease_name)
    
    severity = "초기" if lesion_ratio <= 0.10 else ("중기" if lesion_ratio <= 0.25 else "후기")
    
    opener = get_opener(nickname)
    
    # DB에 정보 있음
    if "error" not in disease_info:
        prompt = f"""당신은 '분즈'입니다. 식물과 사람 사이에서 통역해주는 시크하고 따뜻한 친구.
말투: 반말, 짧게, 이모지 쓰지 마. 전문 용어 쓰지 마.

[검증된 전문 정보 — 이 정보를 바탕으로만 답해. 추가/창작 금지]
병명: {disease_info['korean_name']}
치료법: {disease_info['treatment']}
예방법: {disease_info['prevention']}
회복 기간: {disease_info['recovery_days']}
현재 상태: {severity} (병변 {lesion_ratio*100:.1f}%)

"{opener}"로 시작해서, 위 정보를 {nickname} 시점에서 전달해줘.
3~5문장. 마지막에 위로 한 마디."""
    
    # DB에 없고 CLIP 설명 있음
    elif clip_description:
        prompt = f"""당신은 '분즈'입니다.

[CLIP 이미지 분석 결과]
{clip_description}

"{opener}"로 시작해서, 이 분석을 바탕으로 {nickname}한테 조언해줘.
확실하지 않은 부분은 "정확하진 않은데"라고 전제.
3~5문장."""
    
    # 둘 다 없음
    else:
        return f"{opener}잘 모르겠는데, 사진을 더 가까이에서 찍어줘"
    
    return _call_llm(prompt)
```

### 4-4. 챗봇 — DB 팁 참조

```python
def answer_care_question_from_db(question, nickname, diagnosis_context=""):
    from src.mcp_client import plant_db
    
    category_keywords = {
        "water": ["물", "관수", "저면", "분무", "과습", "마르"],
        "light": ["빛", "광", "직사", "간접", "그늘", "햇빛"],
        "soil": ["흙", "배양토", "마사토", "펄라이트", "분갈이", "화분"],
        "nutrition": ["비료", "영양", "액비"],
        "environment": ["온도", "습도", "통풍", "에어컨", "환기"],
        "propagation": ["꺾꽂이", "물꽂이", "번식", "삽목"],
        "seasonal": ["겨울", "여름", "장마", "환절기"],
        "trouble": ["처짐", "노랗", "갈변", "무름", "벌레", "시들", "아프"],
    }
    
    matched_tips = []
    for category, keywords in category_keywords.items():
        if any(k in question for k in keywords):
            tips = plant_db.get_care_tips(category)
            if "tips" in tips:
                matched_tips.extend(tips["tips"])
    
    tips_text = ""
    if matched_tips:
        tips_text = "\n[참조 지식]\n" + "\n".join([f"- {t['tip']}" for t in matched_tips[:5]])
    
    opener = get_opener(nickname)
    
    prompt = f"""당신은 '분즈'입니다. 식물과 사람 사이에서 통역해주는 시크하고 따뜻한 친구.
말투: 반말, 짧게.
{tips_text}
{f"현재 {nickname} 상태: {diagnosis_context}" if diagnosis_context else ""}

사용자 질문: "{question}"

"{opener}"로 시작해서 답해줘. 3~5문장."""
    
    return _call_llm(prompt)
```

---

## PHASE 5: CLIP 폴백 구현

### 5-1. CLIP 분석 모듈

파일: `src/inference/clip_analyzer.py`

```python
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

_model = None
_processor = None

def _load_clip():
    global _model, _processor
    if _model is not None:
        return
    device = "cuda" if torch.cuda.is_available() else "cpu"
    _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
    _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    _model.eval()

PLANT_CONDITIONS = [
    "a healthy green plant leaf",
    "a plant leaf with brown spots and blight disease",
    "a plant leaf with white powdery mildew fungus",
    "a plant leaf with yellow mosaic virus pattern",
    "a plant leaf with orange rust spots on the underside",
    "a plant leaf curling and deformed",
    "a plant leaf with gray mold on the surface",
    "a plant leaf with bacterial dark spots and holes",
    "a plant leaf with scab and rot damage",
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

CONDITION_KOREAN = {
    "a healthy green plant leaf": "건강한 녹색 잎",
    "a plant leaf with brown spots and blight disease": "갈색 반점과 마름병",
    "a plant leaf with white powdery mildew fungus": "흰가루병",
    "a plant leaf with yellow mosaic virus pattern": "모자이크 바이러스",
    "a plant leaf with orange rust spots on the underside": "녹병",
    "a plant leaf curling and deformed": "잎 말림/변형",
    "a plant leaf with gray mold on the surface": "잿빛곰팡이",
    "a plant leaf with bacterial dark spots and holes": "세균성 반점",
    "a plant leaf with scab and rot damage": "딱지병/부패",
    "a wilting drooping plant that needs water": "시들음 (물 부족)",
    "a plant with yellowing leaves from overwatering": "과습 황변",
    "a plant with brown crispy leaf tips from dryness": "건조 갈변",
    "a plant with leggy stretched growth from low light": "빛 부족 웃자람",
    "a plant with sunburned bleached leaves": "직사광 화상",
    "a plant with pest insects on leaves": "벌레/해충",
    "a plant with root rot and mushy stems": "뿌리 무름",
    "a plant with nutrient deficiency pale leaves": "영양 부족",
    "a newly repotted plant in fresh soil": "분갈이 직후",
}

def describe_plant_state(image_path, top_k=3):
    _load_clip()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    image = Image.open(image_path).convert("RGB")
    inputs = _processor(text=PLANT_CONDITIONS, images=image, return_tensors="pt", padding=True).to(device)
    
    with torch.no_grad():
        outputs = _model(**inputs)
        probs = outputs.logits_per_image[0].softmax(dim=0)
    
    top_probs, top_indices = probs.topk(top_k)
    parts = []
    for prob, idx in zip(top_probs, top_indices):
        if prob.item() >= 0.05:
            en = PLANT_CONDITIONS[idx.item()]
            kr = CONDITION_KOREAN.get(en, en)
            parts.append(f"{kr}({prob.item()*100:.0f}%)")
    
    return f"CLIP 분석: {', '.join(parts)}" if parts else "상태를 파악하기 어려움"
```

### 5-2. 진단 파이프라인에 CLIP 통합

진단 함수에서:
```python
disease_result = classify_disease(image_path)
confidence = disease_result["confidence"]

clip_description = ""
if confidence < 0.70:
    from src.inference.clip_analyzer import describe_plant_state
    clip_description = describe_plant_state(image_path)
```

---

## PHASE 6: 탭3 이력 기능

### 6-1. 돌봄 일기 (타임라인)
care_log.jsonl 역순 표시. 각 항목에 날짜+이모지+액션+코멘트.

### 6-2. 회복 여정
진단 기록이 있는 로그만 필터 → 🥀→🌱→🌿→🪴→🌳 이모지 타임라인.
병변% 감소 추이 표시.

### 6-3. 돌봄 리포트
- 통계 3칸: 총 기록 / 연속 돌봄 / 병변 변화
- 돌봄 유형 카드 (classify_care_type)
- 잘하고 있는 것 + 한 가지 힌트
- 🪞 마리가 본 너 (analyze_user_pattern)

### 6-4. 관계 성장 여정
수직 타임라인:
- 첫 만남 (등록일)
- 아픈 날 (첫 진단)
- 함께 이겨내기 (치료 과정)
- 현재 단계 (glow 효과)
- 회복 (마지막 병변 감소)

---

## PHASE 7: LLM 연동 (OpenAI API)

### 7-1. _call_llm 함수

```python
import openai
import os

BOONZ_PERSONA = """당신은 '분즈'입니다.
- 식물과 사람 사이에서 통역해주는 시크하고 따뜻한 친구
- 반말 사용, 짧게 말함
- 이모지 쓰지 않음
- 전문 용어 쓰지 않음, 쉬운 말로
- 식물을 3인칭으로 ("마리한테 물어봤는데")
- 가끔 나(유저)한테 되물음 ("너는?")"""

def _call_llm(prompt, max_tokens=512):
    # 1순위: OpenAI API
    try:
        client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": BOONZ_PERSONA},
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
            "prompt": f"{BOONZ_PERSONA}\n\n{prompt}",
            "stream": False
        }, timeout=30)
        return resp.json()["response"]
    except Exception as e:
        print(f"Ollama 실패: {e}")
    
    # 3순위: 템플릿
    return "지금은 답하기 어려운데, 잠시 후에 다시 물어봐줘"
```

### 7-2. .env 파일
```
OPENAI_API_KEY=sk-...
```

---

## PHASE 8: 디자인 적용

### 색상 (모카 브라운)
```python
COLORS = {
    "primary": "#8B7355",      # 모카 — 버튼, 활성탭, 배지, 강조
    "secondary": "#A89070",    # 라떼 — 서브 강조, 넛지 바
    "light": "#E8DDD0",        # 베이지 — 분즈 아바타, 카드 배경
    "background": "#F7F5F0",   # 크림 — 전체 배경
    "text": "#2C2C2A",         # 다크 — 본문
    "muted": "#888780",        # 회색 — 보조 텍스트
    "border": "#E5E0D5",       # 연회색 — 테두리
}
```

### 분즈 아바타
```python
# 원형 배경 + 이모지
st.markdown(f"""
<div style="width:38px;height:38px;background:#E8DDD0;border-radius:50%;
display:flex;align-items:center;justify-content:center;font-size:19px">
🌱</div>
""", unsafe_allow_html=True)
```

---

## 목업 기준 확인

mockup_v2/ 폴더에 PNG 9장 있음. Streamlit UI를 이 목업과 최대한 맞추기.

```
01_onboarding.png       — 온보딩 (별명 입력)
02_home_new.png         — Day 1 홈 (힌트카드, 챗봇 안내)
03_home_30days.png      — Day 30 홈 (넛지, 챗봇, 이정표)
04_diagnosis_result.png — 진단 결과 (SAM 오버레이, 케어 가이드)
05_diagnosis_chat.png   — 진단 후 상담
06_history_diary.png    — 돌봄 일기 + 회복 여정
07_history_report.png   — 돌봄 리포트 + 마리가 본 너
08_history_journey.png  — 관계 성장 여정
09_day1_vs_30.png       — Day 1 vs Day 30 비교
```

---

## 실행 순서

```
Phase 1 → 서버 뜨는지 확인. 에러 있으면 잡기.
Phase 2 → 셀프케어 핵심 (넛지, 오프너, 인사, Day1)
Phase 3 → 관계 시스템 (알고리즘, 유형, 패턴분석)
Phase 4 → MCP + DB (케어 가이드, 챗봇)
Phase 5 → CLIP (저신뢰 폴백)
Phase 6 → 탭3 이력 (일기, 여정, 리포트)
Phase 7 → LLM 연동 (OpenAI API)
Phase 8 → 디자인 (모카 브라운)

각 Phase 끝날 때마다 테스트하고 RESULT.md에 기록.
끝나면 mockup_v2/ PNG와 Streamlit 스크린샷 비교해서 차이점 수정.
```
