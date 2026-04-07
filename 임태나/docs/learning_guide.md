# Boonz 학습 가이드

> **사용 규칙**
> 1. 개념 설명 읽기
> 2. 도전 과제 확인 → **스크롤 내리지 말고** 직접 코드 작성
> 3. 막히면 "힌트:" 부분만 확인
> 4. 그래도 모르면 "해설:" 확인
>
> 이 순서를 지키면 학습이 됩니다. 강제 장치는 없으니 스스로 지켜주세요.

---

## 챕터 1. PyTorch 체크포인트 로드

### 개념 설명

`torch.save()`로 모델을 저장할 때 두 가지 방식이 있습니다.

**방식 A — state_dict만 저장 (단순)**
```python
torch.save(model.state_dict(), "model.pth")
# 로드: model.load_state_dict(torch.load("model.pth"))
```

**방식 B — 체크포인트 전체 저장 (실무 표준)**
```python
torch.save({
    "model_state_dict": model.state_dict(),
    "optimizer_state_dict": optimizer.state_dict(),
    "epoch": 42,
    "val_accuracy": 0.91,
    "class_to_idx": {"Healthy": 0, "Late_Blight": 1, ...},
    "architecture": "efficientnet_b3",
}, "checkpoint.pth")
```

방식 B를 쓰면 epoch, 정확도, 클래스 목록까지 함께 보존돼 재현성이 높아집니다.

Boonz 프로젝트의 `.pth` 파일은 **전부 방식 B**입니다.

---

### 도전 과제 1-1

아래 조건으로 체크포인트를 로드하는 함수를 작성해보세요.

- 파일 경로와 모델 객체를 인자로 받음
- `checkpoint["model_state_dict"]`로 가중치 적용
- 실제 클래스 수는 `checkpoint["class_to_idx"]`에서 읽음
- CPU/GPU 자동 대응 (`map_location` 처리)
- 딕셔너리가 아닌 순수 state_dict가 들어올 경우도 방어

```python
# 여기에 작성해보세요
def load_checkpoint(path: str, model) -> int:
    """
    Returns: 클래스 수 (int)
    """
    ...
```

> **힌트:** `torch.load(..., map_location=device)` → `isinstance(ckpt, dict)` 분기 → `ckpt["model_state_dict"]`

<details>
<summary>해설 보기 (직접 시도 후 확인)</summary>

```python
import torch

def load_checkpoint(path: str, model) -> int:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    checkpoint = torch.load(path, map_location=device)

    if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
        model.load_state_dict(checkpoint["model_state_dict"])
        num_classes = len(checkpoint["class_to_idx"])
    else:
        # 순수 state_dict가 저장된 경우 폴백
        model.load_state_dict(checkpoint)
        num_classes = -1  # 알 수 없음

    model.to(device)
    model.eval()
    return num_classes
```

**핵심 포인트:**
- `map_location=device` — GPU 없는 환경에서도 CPU로 로드됨
- `isinstance(..., dict)` 방어 — 방식 A로 저장된 레거시 파일 대응
- 로드 후 `.eval()` — BatchNorm, Dropout이 추론 모드로 전환됨

</details>

---

### 도전 과제 1-2

Boonz의 병변 분류 모델은 `EfficientNet-B3`, 12클래스입니다.
아래 클래스 목록을 보고 `class_to_idx` 딕셔너리를 직접 만들어보세요.

클래스: `Bacterial_Spot`, `Early_Blight`, `Greening`, `Healthy`, `Late_Blight`,
`Leaf_Curl`, `Leaf_Mold`, `Leaf_Spot`, `Mosaic_Virus`, `Powdery_Mildew`, `Rust`, `Scab_Rot`

```python
# 알파벳 순으로 인덱스를 부여해보세요
class_to_idx = {
    ...
}
```

<details>
<summary>해설 보기</summary>

```python
class_to_idx = {
    "Bacterial_Spot": 0,
    "Early_Blight":   1,
    "Greening":        2,
    "Healthy":         3,
    "Late_Blight":     4,
    "Leaf_Curl":       5,
    "Leaf_Mold":       6,
    "Leaf_Spot":       7,
    "Mosaic_Virus":    8,
    "Powdery_Mildew":  9,
    "Rust":           10,
    "Scab_Rot":       11,
}
```

학습 시 `ImageFolder`가 자동으로 알파벳 순 인덱스를 부여하기 때문에 이 순서와 일치해야 합니다.

</details>

---

## 챕터 2. 한글 경로와 이미지 처리

### 개념 설명

`cv2.imread()`는 내부적으로 ANSI 인코딩을 사용해, **한글/유니코드가 포함된 경로에서 None을 반환**합니다.

```python
import cv2
img = cv2.imread("C:/사진/잎.jpg")  # → None (한글 경로 실패)
```

**PIL로 우회**하면 Python의 유니코드 경로 처리를 그대로 사용합니다.

```python
from PIL import Image
import numpy as np
img = np.array(Image.open("C:/사진/잎.jpg").convert("RGB"))  # → (H, W, 3) numpy array
```

OpenCV 함수에 그대로 넘길 수 있고, PyTorch 전처리에도 사용 가능합니다.

---

### 도전 과제 2-1

아래 함수를 완성하세요. 경로를 받아 `(H, W, 3)` uint8 numpy 배열을 반환해야 합니다.
cv2.imread는 사용하지 마세요.

```python
def read_image_safe(filepath: str) -> np.ndarray:
    """한글 경로에서도 안전하게 이미지를 로드합니다."""
    ...
```

> **힌트:** `Image.open()` → `.convert("RGB")` → `np.array()`

<details>
<summary>해설 보기</summary>

```python
from PIL import Image
import numpy as np

def read_image_safe(filepath: str) -> np.ndarray:
    pil_image = Image.open(filepath).convert("RGB")
    return np.array(pil_image)
```

FastAPI에서 업로드 바이트를 받을 때도 같은 패턴:
```python
import io
pil_image = Image.open(io.BytesIO(file_bytes)).convert("RGB")
image_rgb = np.array(pil_image)
```

</details>

---

## 챕터 3. FastAPI 응답 설계

### 개념 설명

FastAPI에서 응답 형태를 Pydantic 모델로 정의하면 자동 직렬화 + 문서화를 얻습니다.

```python
from pydantic import BaseModel
from fastapi import FastAPI

class DiseaseResult(BaseModel):
    name: str
    confidence: float
    korean: str = ""   # 기본값 지정 가능

app = FastAPI()

@app.post("/diagnose", response_model=DiseaseResult)
async def diagnose():
    return DiseaseResult(name="Late_Blight", confidence=0.87, korean="후기 마름병")
```

`response_model` 지정 시 반환값이 스키마와 다르면 FastAPI가 422 에러를 냅니다.

---

### 도전 과제 3-1

Boonz의 `/diagnose`는 아래 정보를 반환해야 합니다.
Pydantic 스키마를 작성해보세요.

필드 목록:
- 종 정보: 이름, 신뢰도
- 병변 정보: 이름, 신뢰도, 한국어 이름
- 병변 분석: 면적 비율(`ratio` 0.0~1.0), 심각도 문자열, 오버레이 이미지(base64)
- 분즈 메시지: mood 문자열, message 문자열
- 처리 시간(ms)

```python
# 여기에 작성해보세요
class BoonzResponse(BaseModel):
    ...

class DiagnoseResponse(BaseModel):
    ...
```

> **힌트:** 중첩 모델을 써야 합니다. `BoonzResponse`를 먼저 만들고 `DiagnoseResponse`에 포함.

<details>
<summary>해설 보기</summary>

```python
from pydantic import BaseModel

class BoonzResponse(BaseModel):
    mood: str = "default"
    message: str = ""

class SpeciesResponse(BaseModel):
    name: str
    confidence: float

class DiseaseResponse(BaseModel):
    name: str
    confidence: float
    korean: str = ""

class LesionResponse(BaseModel):
    ratio: float
    severity: str
    overlay_base64: str = ""

class DiagnoseResponse(BaseModel):
    species: SpeciesResponse
    disease: DiseaseResponse
    lesion: LesionResponse
    boonz: BoonzResponse = BoonzResponse()
    processing_time_ms: float = 0
```

`boonz: BoonzResponse = BoonzResponse()` — 기본값을 인스턴스로 지정해 항상 포함됩니다.

</details>

---

### 도전 과제 3-2

분즈 mood 규칙을 함수로 구현해보세요.

| 병변 비율 | mood | 메시지 예시 |
|---|---|---|
| 0 ~ 10% | `happy` | `"{nickname}한테 물어봤는데, 요즘 컨디션 좋대"` |
| 10 ~ 25% | `worried` | `"{nickname}가 좀 힘들다는데? 약 좀 사다줘"` |
| 25%+ | `sad` | `"{nickname}가 많이 아프대... 빨리 도와줘야 할 거 같아"` |

```python
def get_boonz_mood(lesion_ratio: float, nickname: str) -> tuple[str, str]:
    ...
```

> **힌트:** 비율은 0.0~1.0 (소수)입니다. 10%는 `0.10`입니다.

<details>
<summary>해설 보기</summary>

```python
def get_boonz_mood(lesion_ratio: float, nickname: str) -> tuple[str, str]:
    name = nickname or "식물"
    if lesion_ratio <= 0.10:
        return "happy", f"{name}한테 물어봤는데, 요즘 컨디션 좋대. 네가 잘 돌봐준 거야"
    if lesion_ratio <= 0.25:
        return "worried", f"{name}가 좀 힘들다는데? 약 좀 사다줘"
    return "sad", f"{name}가 많이 아프대... 빨리 도와줘야 할 거 같아"
```

</details>

---

## 챕터 4. Streamlit 멀티탭 UI

### 개념 설명

Streamlit의 `st.tabs()`는 탭 컨테이너를 반환합니다. 각 탭 안에서 `with` 문으로 UI를 구성합니다.

```python
tab1, tab2, tab3 = st.tabs(["📷 진단", "💬 상담", "📊 이력"])

with tab1:
    st.write("진단 화면")

with tab2:
    st.write("상담 화면")
```

세션 상태는 `st.session_state`에 저장합니다. 탭이 바뀌어도 값이 유지됩니다.

---

### 도전 과제 4-1

진단 탭에서 파일 업로드 → FastAPI 호출 → 결과 표시 흐름을 작성해보세요.

```python
with tab1:
    uploaded = st.file_uploader(...)

    if uploaded:
        # 1. FastAPI /diagnose 호출
        # 2. 응답에서 disease.korean, lesion.ratio 꺼내기
        # 3. boonz mood에 맞는 이모지(😊 / 😟 / 😢)로 메시지 표시
        ...
```

> **힌트:** `requests.post(url, files={"file": (name, bytes, type)}, data={"nickname": ...})`

<details>
<summary>해설 보기</summary>

```python
import requests

FASTAPI_URL = "http://localhost:8000"

with tab1:
    uploaded = st.file_uploader("잎 사진", type=["jpg", "jpeg", "png"],
                                 label_visibility="collapsed")

    if uploaded:
        files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
        resp = requests.post(f"{FASTAPI_URL}/diagnose",
                             files=files, data={"nickname": nickname})
        result = resp.json()

        disease_kr = result["disease"]["korean"]
        ratio = result["lesion"]["ratio"] * 100
        mood = result["boonz"]["mood"]
        message = result["boonz"]["message"]

        emoji = {"happy": "😊", "worried": "😟", "sad": "😢"}.get(mood, "🌱")
        st.markdown(f"**{emoji} {message}**")
        st.caption(f"{disease_kr} · 병변 {ratio:.1f}%")
```

</details>

---

### 도전 과제 4-2

원터치 케어 버튼 7개를 `st.columns(4)`로 배치하고,
클릭 시 `save_care_log(nickname, action)`을 호출하는 코드를 작성해보세요.

케어 항목:
```python
care_items = {
    "💧 물줬음": "water", "☀️ 자리옮김": "move",
    "✂️ 가지치기": "prune", "💊 약줬음": "medicine",
    "🪴 분갈이": "repot", "🍃 잎닦음": "clean",
    "😊 그냥봄": "observe",
}
```

> **힌트:** `i % 4`로 열 인덱스 계산. `key=f"btn_{action}"` 필수 (중복 key 방지).

<details>
<summary>해설 보기</summary>

```python
st.markdown(f"**방금 {nickname}한테 뭐 해줬어?**")
cols = st.columns(4)
for i, (label, action) in enumerate(care_items.items()):
    with cols[i % 4]:
        if st.button(label, key=f"t1_{action}", use_container_width=True):
            save_care_log(nickname, action)
            st.toast(f"{nickname}한테 전해놨어!")
```

`i % 4` — 0,1,2,3,0,1,2 순서로 4개 열에 배치됩니다.

</details>

---

## 챕터 5. LLM 이중화 패턴

### 개념 설명

프로덕션에서 LLM 호출은 **항상 실패할 수 있습니다**. 네트워크 오류, 키 만료, 쿼터 초과 등.
1순위 API → 2순위 로컬 모델 순서로 폴백하는 패턴이 표준입니다.

```
OpenAI API (빠름, 유료)
    │ 실패 시
    ▼
Ollama 로컬 (느리지만 오프라인 가능)
    │ 실패 시
    ▼
하드코딩 폴백 메시지 반환
```

---

### 도전 과제 5-1

아래 `_call_llm()` 함수를 완성하세요. OpenAI API → Ollama 순으로 폴백합니다.

```python
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:14b"

def _call_llm(prompt: str) -> str:
    # 1. OpenAI 시도
    # 2. 실패 시 Ollama 시도
    # 3. 둘 다 실패 시 빈 문자열 반환
    ...
```

> **힌트:**
> - OpenAI: `POST https://api.openai.com/v1/chat/completions`
> - Ollama: `POST {OLLAMA_BASE_URL}/api/generate` + `"stream": False`

<details>
<summary>해설 보기</summary>

```python
import os, requests
from loguru import logger

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5:14b"

def _call_llm(prompt: str) -> str:
    # 1순위: OpenAI
    if OPENAI_API_KEY:
        try:
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 1024,
                },
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning(f"OpenAI 실패, Ollama 폴백: {e}")

    # 2순위: Ollama
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.7, "num_predict": 1024},
            },
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["response"]
    except Exception as e:
        logger.error(f"Ollama도 실패: {e}")
        return ""
```

</details>

---

## 정리

| 챕터 | 핵심 개념 | 실무 적용 |
|---|---|---|
| 1 | 체크포인트 구조 | `checkpoint["model_state_dict"]` + `class_to_idx` |
| 2 | PIL로 이미지 로드 | 한글 경로 대응 |
| 3 | Pydantic 스키마 | FastAPI 응답 타입 안전성 |
| 4 | Streamlit 탭 + 세션 | 멀티탭 UI + 상태 유지 |
| 5 | LLM 폴백 패턴 | OpenAI → Ollama → 하드코딩 |
