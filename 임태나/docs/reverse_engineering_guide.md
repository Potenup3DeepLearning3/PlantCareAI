# Boonz 역설계 가이드 (파악용)

> 아키텍처 맵 → 구현 로드맵 → 코드 블록 레퍼런스 순서.
> 이 파일만 보고 재구현할 수 있는 수준으로 작성됨.

---

## 1. 아키텍처 맵

```
┌─────────────────────────────────────────┐
│  Streamlit  (localhost:8501)            │
│  app.py — 3탭: 홈 / 진단 / 이력         │
└───────────────┬─────────────────────────┘
                │ HTTP (multipart/form-data, JSON)
                ▼
┌─────────────────────────────────────────┐
│  FastAPI  (localhost:8000)              │
│  POST /diagnose                         │
│  POST /care-guide                       │
│  POST /consult/text                     │
│  GET  /pattern/{nickname}               │
└──┬──────────────┬────────────────┬──────┘
   │              │                │
   ▼              ▼                ▼
ML Pipeline    LLM Stack        SQLite DB
EfficientNet   OpenAI           data/plant_care.db
SAM            → Ollama         (diseases, care_tips,
CLIP (폴백)    → 하드코딩        species_care)
```

### 파일 구조

```
src/
  api/
    main.py              # FastAPI 앱 진입점, CORS, 라우터 등록
    routes/
      diagnose.py        # POST /diagnose
      care_guide.py      # POST /care-guide
      consult.py         # POST /consult/text
      pattern.py         # GET /pattern/{nickname}
    schemas.py           # Pydantic 응답 스키마 전체
  inference/
    diagnose.py          # DiagnosisPipeline (EfficientNet + SAM)
    llm.py               # _call_llm, 프롬프트 템플릿, 공개 함수
    clip_analyzer.py     # describe_plant_state (신뢰도 < 70% 폴백)
  data/
    db.py                # SQLite 조회 헬퍼
  config.py              # 경로, URL, 모델명 상수
  frontend/
    app.py               # Streamlit UI
data/
  plant_care.db          # SQLite (scripts/init_db.py로 생성)
  plants.json            # 등록 식물 목록
  care_log.jsonl         # 케어 기록 (줄 단위 JSON)
models/
  disease/efficientnet_b3_disease_type_best.pth
  species/species_model_best.pth
  sam/sam_vit_b_01ec64.pth
scripts/
  init_db.py             # DB 스키마 생성 + 12클래스 데이터 삽입
  generate_demo_data.py  # 마리 30일치 시뮬레이션 데이터
```

---

## 2. 구현 순서 로드맵

### Phase 0 — 환경 세팅

```
1. uv venv → uv pip install -r requirements.txt
2. .env 작성 (OPENAI_API_KEY, OLLAMA_BASE_URL)
3. python scripts/init_db.py
4. python scripts/generate_demo_data.py
```

### Phase 1 — 모델 로드 (가장 먼저 검증)

```
src/inference/diagnose.py
  └─ DiagnosisPipeline.__init__()
       ├─ _load_disease_model()   ← EfficientNet-B3, 12클래스
       ├─ _load_species_model()   ← EfficientNet-B3, 47클래스
       └─ _load_sam()             ← SAM vit_b
```

검증 명령:
```bash
python -c "from src.inference.diagnose import DiagnosisPipeline; p = DiagnosisPipeline(); print('OK')"
```

### Phase 2 — FastAPI 엔드포인트

```
POST /diagnose        → 모델 추론만 (LLM 없음, 300ms 목표)
POST /care-guide      → DB 조회 + LLM 호출
POST /consult/text    → LLM 호출 (진단 맥락 포함)
GET  /pattern/{nick}  → 케어 로그 집계 + LLM 분석
```

### Phase 3 — Streamlit UI

```
탭 1 (홈):    식물 선택 → 원터치 케어 → 챗봇
탭 2 (진단):  파일 업로드 → /diagnose → /care-guide → 케어 버튼
탭 3 (이력):  타임라인 → 추세선 → 패턴 분석
```

### Phase 4 — CLIP 폴백

```
/diagnose에서 confidence < 0.70이면
  clip_analyzer.describe_plant_state(image) 호출
  → 설명 텍스트를 /care-guide 요청에 포함
```

---

## 3. 코드 블록 레퍼런스

### 3-1. 체크포인트 로드 (공통 패턴)

모든 `.pth` 파일 구조: `{model_state_dict, optimizer_state_dict, epoch, val_accuracy, class_to_idx, architecture}`

```python
import torch

def _load_model(path: str, model):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(path, map_location=device)
    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
        num_classes = len(checkpoint["class_to_idx"])
    else:
        model.load_state_dict(checkpoint)
        num_classes = -1
    model.to(device).eval()
    return num_classes
```

### 3-2. 이미지 로드 (PIL 우회 — 한글 경로 대응)

```python
from PIL import Image
import numpy as np
import io

# 파일 경로에서
img = np.array(Image.open(filepath).convert("RGB"))

# FastAPI UploadFile 바이트에서
contents = await file.read()
img = np.array(Image.open(io.BytesIO(contents)).convert("RGB"))
```

### 3-3. 모델 정의 (EfficientNet-B3)

```python
# 병변 분류 — 12클래스
model = create_efficientnet_b3(num_classes=12)
# 파일: models/disease/efficientnet_b3_disease_type_best.pth

# 종 식별 — 47클래스
model = create_species_model(num_classes=47)
# 파일: models/species/species_model_best.pth
```

12클래스 목록:
```python
DISEASE_KOREAN = {
    "Bacterial_Spot": "세균성 반점", "Early_Blight": "초기 마름병",
    "Greening":        "그리닝병",   "Healthy":       "건강",
    "Late_Blight":    "후기 마름병", "Leaf_Curl":     "잎 말림",
    "Leaf_Mold":       "잎 곰팡이",  "Leaf_Spot":     "잎 반점",
    "Mosaic_Virus":   "모자이크 바이러스", "Powdery_Mildew": "흰가루병",
    "Rust":            "녹병",       "Scab_Rot":      "딱지병/부패",
}
```

### 3-4. Pydantic 스키마 전체 (`src/api/schemas.py`)

```python
from pydantic import BaseModel

class BoonzResponse(BaseModel):
    mood: str = "default"      # happy | worried | sad | default
    message: str = ""

class SpeciesResponse(BaseModel):
    name: str
    confidence: float
    korean: str = ""

class DiseaseResponse(BaseModel):
    name: str
    confidence: float
    korean: str = ""

class LesionResponse(BaseModel):
    ratio: float               # 0.0 ~ 1.0
    severity: str              # 초기 | 중기 | 후기
    overlay_base64: str = ""

class CareGuideResponse(BaseModel):
    text: str
    audio_url: str = ""

class ClipResponse(BaseModel):
    used: bool = False
    description: str = ""

class DiagnoseResponse(BaseModel):
    species: SpeciesResponse
    disease: DiseaseResponse
    disease_alternatives: list[DiseaseResponse] = []
    confidence_level: str = "높음"
    lesion: LesionResponse
    care_guide: CareGuideResponse
    boonz: BoonzResponse = BoonzResponse()
    processing_time_ms: float = 0
    clip: ClipResponse = ClipResponse()
```

### 3-5. `/diagnose` 엔드포인트 (`src/api/routes/diagnose.py`)

```python
from fastapi import APIRouter, Form, HTTPException, UploadFile

router = APIRouter()
_pipeline = None

def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        from src.inference.diagnose import DiagnosisPipeline
        _pipeline = DiagnosisPipeline()
    return _pipeline

@router.post("/diagnose", response_model=DiagnoseResponse)
async def diagnose(file: UploadFile, nickname: str = Form("")):
    if not file.content_type.startswith("image/"):
        raise HTTPException(400, "이미지 파일만 업로드 가능합니다.")

    contents = await file.read()
    pil_image = Image.open(io.BytesIO(contents)).convert("RGB")
    image_rgb = np.array(pil_image)

    result = _get_pipeline().diagnose(image_rgb)

    # CLIP 폴백 — 신뢰도 70% 미만
    clip_used, clip_desc = False, ""
    if result.disease.confidence < 0.70:
        try:
            from src.inference.clip_analyzer import describe_plant_state
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
                pil_image.save(tmp.name)
                clip_desc = describe_plant_state(tmp.name)
            os.unlink(tmp.name)
            clip_used = True
        except Exception as e:
            logger.warning(f"CLIP 실패: {e}")

    mood, message = get_boonz_mood(result.lesion.ratio, nickname)
    if clip_used and clip_desc:
        mood = "default"
        message = f"{nickname or '식물'} 상태가 좀 복잡한데... {clip_desc}"

    return DiagnoseResponse(
        species=SpeciesResponse(name=result.species.name, confidence=result.species.confidence),
        disease=DiseaseResponse(
            name=result.disease.name,
            confidence=result.disease.confidence,
            korean=DISEASE_KOREAN.get(result.disease.name, result.disease.name),
        ),
        lesion=LesionResponse(
            ratio=result.lesion.ratio,
            severity=result.lesion.severity,
            overlay_base64=result.lesion.overlay_image_base64,
        ),
        care_guide=CareGuideResponse(text=""),  # /care-guide로 별도 요청
        boonz=BoonzResponse(mood=mood, message=message),
        clip=ClipResponse(used=clip_used, description=clip_desc),
    )
```

### 3-6. LLM 이중화 (`src/inference/llm.py`)

```python
import os, requests
from loguru import logger

_OPENAI_KEY  = os.getenv("OPENAI_API_KEY", "")
OLLAMA_URL   = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:14b")

BOONZ_PERSONA = """[필수 규칙] 반드시 한국어로만 답해. 영어·한자 한 글자도 쓰지 마.
너는 "분즈"야. 반말. 짧고 직관적. 감동 팔이 없음."""

def _call_llm(prompt: str) -> str:
    # 1순위: OpenAI gpt-4o-mini
    if _OPENAI_KEY:
        try:
            r = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {_OPENAI_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": BOONZ_PERSONA},
                        {"role": "user",   "content": prompt},
                    ],
                    "temperature": 0.7, "max_tokens": 1024,
                },
                timeout=30,
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"OpenAI 실패: {e}")

    # 2순위: Ollama 로컬
    try:
        r = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "prompt": prompt,
                  "stream": False, "options": {"temperature": 0.7, "num_predict": 1024}},
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["response"]
    except Exception as e:
        logger.error(f"Ollama도 실패: {e}")
        return ""
```

### 3-7. 분즈 mood 로직

```python
def get_boonz_mood(lesion_ratio: float, nickname: str = "") -> tuple[str, str]:
    name = nickname or "식물"
    if lesion_ratio <= 0.05:
        return "happy",   f"{name}한테 물어봤는데, 요즘 컨디션 좋대. 네가 잘 돌봐준 거야"
    if lesion_ratio <= 0.10:
        return "default", f"{name}한테 물어봤는데, 살짝 신경 쓰이는 데가 있대"
    if lesion_ratio <= 0.25:
        return "worried", f"{name}가 좀 힘들다는데? 같이 돌보자"
    return   "sad",       f"{name}가 많이 아프대... 빨리 도와줘야 할 거 같아"
```

### 3-8. Streamlit 탭 구조 (`src/frontend/app.py`)

```python
import streamlit as st
import requests

FASTAPI_URL = "http://localhost:8000"

st.set_page_config(page_title="분즈", layout="centered", page_icon="🌱")

nickname = st.selectbox("식물 선택", get_plant_list(), label_visibility="collapsed")

tab1, tab2, tab3 = st.tabs(["🏠 홈", "📷 진단", "📊 이력"])

# ── 탭1: 홈 ──────────────────────────────────────────────────────
with tab1:
    cols = st.columns(4)
    care_items = {
        "💧 물줬음": "water", "☀️ 자리옮김": "move",
        "✂️ 가지치기": "prune", "💊 약줬음": "medicine",
        "🪴 분갈이": "repot", "🍃 잎닦음": "clean", "😊 그냥봄": "observe",
    }
    for i, (label, action) in enumerate(care_items.items()):
        with cols[i % 4]:
            if st.button(label, key=f"h_{action}", use_container_width=True):
                save_care_log(nickname, action)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for msg in st.session_state.chat_history[-8:]:
        align = "right" if msg["role"] == "user" else "left"
        st.markdown(f'<div style="text-align:{align}">{msg["content"]}</div>',
                    unsafe_allow_html=True)

    question = st.text_input("질문", placeholder="예: 잎이 노랗게 변하는데 왜 그래?",
                              label_visibility="collapsed")

# ── 탭2: 진단 ─────────────────────────────────────────────────────
with tab2:
    uploaded = st.file_uploader("잎 사진", type=["jpg","jpeg","png"],
                                 label_visibility="collapsed")
    if uploaded:
        r = requests.post(f"{FASTAPI_URL}/diagnose",
                          files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
                          data={"nickname": nickname})
        result = r.json()
        st.session_state.last_diagnosis = result

        st.image(uploaded, use_container_width=True)
        st.write(f"**{result['disease']['korean']}** · 신뢰도 {result['disease']['confidence']:.0%}")
        st.write(result["boonz"]["message"])

        cols = st.columns(4)
        for i, (label, action) in enumerate(care_items.items()):
            with cols[i % 4]:
                if st.button(label, key=f"t2_{action}", use_container_width=True):
                    save_care_log(nickname, action)

# ── 탭3: 이력 ─────────────────────────────────────────────────────
with tab3:
    pass  # 타임라인, 추세선, 패턴 분석
```

### 3-9. SQLite DB 스키마 (`scripts/init_db.py`)

```python
import sqlite3
from pathlib import Path

DB_PATH = Path("data/plant_care.db")
db = sqlite3.connect(DB_PATH)

db.execute("""CREATE TABLE IF NOT EXISTS diseases (
    name TEXT PRIMARY KEY, korean_name TEXT,
    symptoms TEXT, cause TEXT, treatment TEXT,
    prevention TEXT, recovery_days TEXT, severity_levels TEXT
)""")

db.execute("""CREATE TABLE IF NOT EXISTS care_tips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT, subcategory TEXT,
    species TEXT DEFAULT 'general', tip TEXT, detail TEXT
)""")

db.execute("""CREATE TABLE IF NOT EXISTS species_care (
    species TEXT PRIMARY KEY, korean_name TEXT,
    light TEXT, water_frequency TEXT, humidity TEXT,
    temperature TEXT, soil_mix TEXT, fertilizer TEXT, difficulty TEXT
)""")

db.commit()
db.close()
```

### 3-10. CLIP 폴백 (`src/inference/clip_analyzer.py`)

18개 식물 상태 후보 × 이미지 유사도 비교. 신뢰도 < 70% 시 호출.

```python
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

CANDIDATES = [
    "갈색 반점이 있는 식물 잎",     "흰 가루가 덮인 식물 잎",
    "녹슨 색 포자가 있는 잎",        "잎이 말려 있는 식물",
    "모자이크 무늬가 있는 잎",        "잎 뒷면에 곰팡이가 있는 식물",
    "검게 썩어가는 식물 줄기",        "잎에 구멍이 난 식물",
    "노랗게 변색된 잎",              "수침상 반점이 있는 잎",
    "건강하고 선명한 녹색 잎",        "과습으로 시든 식물",
    "햇빛 부족으로 웃자란 식물",      "잎 끝이 갈색으로 탄 식물",
    "진딧물이 붙은 식물",            "뿌리가 썩어 축 처진 식물",
    "회색 곰팡이(잿빛곰팡이)가 핀 잎", "잎맥만 남고 살이 없어진 잎",
]

_model = None
_processor = None

def _get_clip():
    global _model, _processor
    if _model is None:
        _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        _model.eval()
    return _model, _processor

def describe_plant_state(image_path: str, top_k: int = 3) -> str:
    model, processor = _get_clip()
    image = Image.open(image_path).convert("RGB")

    inputs = processor(text=CANDIDATES, images=image, return_tensors="pt", padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
        probs = outputs.logits_per_image.softmax(dim=1)[0]

    top_indices = probs.topk(top_k).indices.tolist()
    parts = [f"{CANDIDATES[i]}({probs[i]:.0%})" for i in top_indices]
    return "CLIP 분석 결과: " + ", ".join(parts)
```

---

## 4. 주요 상수 / 설정 (`src/config.py`)

```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent  # PROJECT_DIR 아님!
MODELS_DIR   = PROJECT_ROOT / "models"
DATA_DIR     = PROJECT_ROOT / "data"

DISEASE_MODEL_PATH = MODELS_DIR / "disease" / "efficientnet_b3_disease_type_best.pth"
SPECIES_MODEL_PATH = MODELS_DIR / "species" / "species_model_best.pth"
SAM_CHECKPOINT     = MODELS_DIR / "sam"     / "sam_vit_b_01ec64.pth"
SAM_MODEL_TYPE     = "vit_b"

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL    = "qwen2.5:14b"

DB_PATH       = DATA_DIR / "plant_care.db"
PLANTS_FILE   = DATA_DIR / "plants.json"
CARE_LOG_FILE = DATA_DIR / "care_log.jsonl"
```

---

## 5. 우선순위별 구현 체크리스트

| 순위 | 항목 | 파일 |
|------|------|------|
| P0 | 체크포인트 로드 패턴 | `src/inference/diagnose.py` |
| P0 | PIL 이미지 로드 | 모든 이미지 처리 파일 |
| P0 | 12클래스 `DISEASE_KOREAN` | `app.py`, `routes/diagnose.py` |
| P0 | `/diagnose` LLM 제거 (추론만) | `routes/diagnose.py` |
| P0 | `/care-guide` 엔드포인트 추가 | `routes/care_guide.py` |
| P0 | LLM 이중화 (OpenAI → Ollama) | `src/inference/llm.py` |
| P0 | Streamlit 3탭 재구축 | `src/frontend/app.py` |
| P1 | CLIP 폴백 (신뢰도 < 70%) | `src/inference/clip_analyzer.py` |
| P1 | SQLite DB + MCP 연동 | `scripts/init_db.py`, `src/data/db.py` |
| P1 | 시뮬레이션 데이터 | `scripts/generate_demo_data.py` |
| P2 | 패턴 분석 탭 | `routes/pattern.py`, `app.py` 탭3 |
