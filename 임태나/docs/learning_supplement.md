# PlantCare 학습 가이드 보완본

> 이 파일은 `reverse_engineering_guide.md`의 부족한 부분을 채웁니다.
> 두 파일을 함께 보세요.

---

## 보완 1: 학습자 수준별 진입점

학습자의 배경에 따라 시작점이 다릅니다.

---

### Path A — 코딩 처음 시작 (Python 기초만 알면)

```
Stage 1 (환경 + 설정)
    ↓
Stage 4 (FastAPI 기초)  ← ML 건너뛰고 먼저 API 작동 원리 파악
    ↓
Stage 5 (Streamlit UI)
    ↓
Stage 2 (이미지 전처리) ← 그 다음 ML 진입
    ↓
Stage 3 (모델 학습)
    ↓
Stage 6 (세션 상태)
```
> **추천 이유**: FastAPI로 "내가 만든 서버에 요청 보내기"를 먼저 체험하면, ML 파이프라인이 왜 필요한지 동기가 생깁니다.

---

### Path B — 백엔드 개발자 (API는 알지만 ML 모름)

```
Stage 1 (환경 + 설정)   ← 30분
    ↓
Stage 4 (FastAPI)        ← 이미 아는 영역, 빠르게 구조 파악
    ↓
Stage 2 (이미지 전처리)  ← ML 진입점
    ↓
Stage 3 (Transfer Learning)
    ↓
Stage 5 (Streamlit)
    ↓
Stage 6 (세션 상태)
```
> **주의점**: Stage 3에서 `optimizer.zero_grad()` → `loss.backward()` → `optimizer.step()` 순서가 가장 낯설 것입니다. 이 3줄이 "한 번의 gradient 업데이트"입니다.

---

### Path C — ML 연구자 (PyTorch는 알지만 서빙 경험 없음)

```
Stage 1 (환경 + 설정)    ← 15분
    ↓
Stage 3 (모델 학습)       ← 이미 아는 영역
    ↓
Stage 2 (CLAHE 전처리)    ← 의료/식물 이미지 특화 전처리
    ↓
Stage 4 (FastAPI 서빙)    ← 새로운 영역
    ↓
Stage 5 (Streamlit)
    ↓
Stage 6 (세션 상태)
```
> **주의점**: `DiagnosisPipeline` 싱글턴 패턴 — 모델을 한 번만 로드하는 이유를 Stage 4에서 이해하세요.

---

## 보완 2: 추가 코드 해설

---

### 해설 D: `segment_lesion()` — `src/inference/diagnose.py:289`
#### SAM 2단계 파이프라인

**이 함수가 하는 일 (한 줄)**
> "잎 사진에서 병든 부분만 초록색으로 표시하기 위해, 먼저 잎 전체를 찾고, 그 안에서 이상한 색깔 부분을 병변으로 골라낸다"

---

**버전 1 — 가장 단순한 세그멘테이션**

```python
def segment_lesion_v1(predictor, image_rgb):
    predictor.set_image(image_rgb)
    h, w = image_rgb.shape[:2]
    # 이미지 중앙이 잎이라고 가정하고 포인트 하나만 찍음
    masks, scores, _ = predictor.predict(
        point_coords=np.array([[w//2, h//2]]),
        point_labels=np.array([1]),  # 1 = 이 점은 내가 원하는 곳
        multimask_output=True,
    )
    return masks[np.argmax(scores)]  # 가장 점수 높은 마스크 반환
```

이걸 쓰면 어떻게 되나요?
→ 중앙이 잎이 아닌 사진(화분이 중앙에 있는 경우)이면 화분이 마스크에 포함됩니다.
→ 배경과 잎 구분이 안 됩니다.

---

**버전 2 — negative 포인트로 배경 제거**

```python
def segment_lesion_v2(predictor, image_rgb):
    predictor.set_image(image_rgb)
    h, w = image_rgb.shape[:2]
    # positive: 중앙(잎)
    # negative: 4 모서리(배경) — "이 점들은 내가 원하지 않는 곳"
    point_coords = np.array([
        [w//2, h//2],        # 중앙 (positive)
        [10, 10],            # 좌상단 (negative)
        [w-10, 10],          # 우상단 (negative)
        [10, h-10],          # 좌하단 (negative)
        [w-10, h-10],        # 우하단 (negative)
    ])
    point_labels = np.array([1, 0, 0, 0, 0])  # 1=positive, 0=negative
    masks, scores, _ = predictor.predict(
        point_coords=point_coords,
        point_labels=point_labels,
        multimask_output=True,
    )
    return masks[np.argmax(scores)]
```

이걸 쓰면 어떻게 되나요?
→ 잎/배경 분리는 잘 됩니다. 하지만 잎 전체가 마스크에 포함 — 병변만 골라내지 못합니다.

---

**버전 3 — 2단계: 잎 마스크 → 그 안에서 병변 검출**

```python
def segment_lesion_v3(predictor, image_rgb):
    # 1단계: 잎 전체 마스크
    leaf_mask = 위의 v2 방식으로 잎 마스크 생성

    # 2단계: 잎 내부의 색상 이상치를 병변으로 판정
    lab = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2LAB)
    a_ch = lab[:, :, 1]  # 초록↔빨강 채널
    b_ch = lab[:, :, 2]  # 파랑↔노랑 채널

    leaf_a = a_ch[leaf_mask]
    a_mean, a_std = leaf_a.mean(), leaf_a.std()
    # 잎 평균 색에서 1.5 표준편차 이상 벗어난 픽셀 = 이상 (병변 후보)
    lesion_mask = (np.abs(a_ch - a_mean) > 1.5 * a_std) & leaf_mask

    return lesion_mask, leaf_mask
```

---

**현재 버전 — SAM 마스크 + 색상 분석 교집합**

```python
# 자동 모드: 3×3 그리드 포인트로 SAM 추론 + LAB 색상 이상치
# → 둘 다 병변이라고 판단한 교집합 사용 (교집합이 1% 미만이면 색상 단독)
# 비녹색/무늬 잎 감지 → 텍스처 기반 검출로 자동 전환
# 후처리: opening(노이즈 제거) → closing(구멍 메우기) → 소형 성분 제거
```

**왜 교집합인가요?**
> SAM 단독이면 배경 픽셀이 병변에 포함될 수 있습니다.
> 색상 분석 단독이면 무늬 잎(칼라디아 등)에서 무늬를 병변으로 오판합니다.
> 둘 다 병변이라고 동의한 부분만 믿는 것이 가장 정확합니다.

---

### 해설 E: `_call_llm()` — `src/inference/llm.py:231`
#### LLM 폴백 체인

**이 함수가 하는 일 (한 줄)**
> "Google API → Ollama 순서로 시도하고, 둘 다 실패하면 빈 문자열 반환"

---

**버전 1 — Ollama만**

```python
def _call_llm_v1(prompt: str) -> str:
    resp = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "qwen2.5:7b", "prompt": prompt, "stream": False},
        timeout=60,
    )
    return resp.json()["response"]
```

이걸 쓰면 어떻게 되나요?
→ Ollama가 꺼져 있으면 앱이 멈춥니다 (`ConnectionError`).
→ 모델이 느리면 사용자가 60초 동안 기다립니다.

---

**버전 2 — try/except 추가**

```python
def _call_llm_v2(prompt: str) -> str:
    try:
        resp = requests.post(..., timeout=60)
        resp.raise_for_status()  # 4xx/5xx → HTTPError
        return resp.json()["response"]
    except requests.exceptions.ConnectionError:
        return ""   # Ollama 미실행
    except requests.exceptions.Timeout:
        return ""   # 60초 초과
    except Exception:
        return ""   # 기타 오류
```

이걸 쓰면 어떻게 되나요?
→ 오류 시 앱이 죽지 않습니다. 하지만 빈 문자열만 반환 — 사용자에게 아무것도 안 보입니다.
→ 항상 Ollama 응답을 기다리는 비용은 해결 안 됩니다.

---

**버전 3 — Google AI 우선 + Ollama 폴백**

```python
def _call_llm_v3(prompt: str) -> str:
    # 1순위: Google AI Studio (빠름, 1~3초)
    if GOOGLE_API_KEY:
        try:
            resp = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/"
                f"gemma-4-27b-it:generateContent?key={GOOGLE_API_KEY}",
                json={"contents": [{"parts": [{"text": prompt}]}]},
                timeout=30,
            )
            if resp.status_code == 200:
                return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            logger.warning(f"Google API 실패, Ollama 폴백: {e}")
    
    # 2순위: Ollama 로컬
    try:
        resp = requests.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={"model": OLLAMA_MODEL, "system": "한국어로. 반말로. 짧게.",
                  "prompt": prompt, "stream": False,
                  "options": {"temperature": 0.7, "num_predict": 1024}},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.json()["response"]
    except Exception as e:
        logger.error(f"Ollama도 실패: {e}")
        return ""
```

**왜 Google API가 1순위인가요?**
> Ollama는 qwen2.5:7b 기준 RTX 5070에서도 응답에 5~15초 소요됩니다.
> Google AI Studio의 gemma-4-27b는 1~3초이고 무료 할당량이 넉넉합니다.
> 인터넷이 안 되는 환경에서는 GOOGLE_API_KEY를 설정하지 않으면 Ollama로 자동 전환됩니다.

---

### 해설 F: `train_model()` — `src/models/train.py:179`
#### 학습 루프 전체 구조

**이 함수가 하는 일 (한 줄)**
> "모델을 N번 반복 학습시키면서, 검증 정확도가 가장 높을 때의 가중치만 저장하고, 개선이 없으면 조기 종료한다"

---

**버전 1 — 단순 학습 루프**

```python
def train_v1(model, dataloader, epochs=10):
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
    
    for epoch in range(epochs):
        for images, labels in dataloader:
            optimizer.zero_grad()     # 이전 gradient 초기화
            outputs = model(images)   # 순전파
            loss = criterion(outputs, labels)
            loss.backward()           # 역전파
            optimizer.step()          # 가중치 업데이트
        print(f"Epoch {epoch+1} 완료")
```

이걸 쓰면 어떻게 되나요?
→ 마지막 epoch의 가중치가 저장됩니다. 하지만 마지막이 최선이라는 보장이 없습니다.
→ 검증 없이 학습하면 과적합을 발견 못합니다.
→ 학습이 끝나면 결과를 알 수 없습니다 (로그 없음).

---

**버전 2 — 검증 + best 모델 저장 추가**

```python
def train_v2(model, train_loader, val_loader, epochs=20):
    best_val_acc = 0.0
    
    for epoch in range(epochs):
        # 학습
        model.train()
        for images, labels in train_loader:
            ...  # 위와 동일
        
        # 검증
        model.eval()
        correct = 0
        with torch.no_grad():  # gradient 계산 안 함 (메모리, 속도)
            for images, labels in val_loader:
                outputs = model(images)
                correct += (outputs.argmax(1) == labels).sum().item()
        val_acc = correct / len(val_loader.dataset)
        
        # best 저장
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), "best_model.pth")
```

이걸 쓰면 어떻게 되나요?
→ 검증 정확도가 최고일 때만 저장합니다.
→ 하지만 학습이 느려져도 계속 진행합니다 (시간 낭비).
→ 나중에 로드할 때 모델 구조, 클래스 매핑을 별도로 알아야 합니다.

---

**현재 버전 — Early Stopping + CSV 로그 + 완전한 체크포인트**

```python
def train_model(model, dataloaders, optimizer, scheduler, num_epochs,
                save_dir, model_name, architecture, class_to_idx, patience=5):
    criterion = nn.CrossEntropyLoss()
    best_val_acc = 0.0
    epochs_no_improve = 0  # Early Stopping 카운터

    for epoch in range(1, num_epochs + 1):
        # [1] 학습
        train_loss, train_acc = train_one_epoch(model, dataloaders["train"], ...)
        
        # [2] 검증
        val_loss, val_acc, val_preds, val_labels = validate(model, dataloaders["val"], ...)
        
        # [3] 스케줄러 step (CosineAnnealingLR: lr을 코사인 곡선으로 감소)
        scheduler.step()
        
        # [4] CSV 로그 기록 (epoch, train_loss, val_loss, train_acc, val_acc, lr)
        append_csv_log(log_path, {epoch, train_loss, val_loss, train_acc, val_acc, lr})
        
        # [5] Best 체크포인트 저장 또는 Early Stopping
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            epochs_no_improve = 0
            torch.save({
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "epoch": epoch,
                "val_accuracy": val_acc,
                "class_to_idx": class_to_idx,   # ← 나중에 로드 시 필요
                "architecture": architecture,    # ← "efficientnet_b3" 등
            }, best_path)
        else:
            epochs_no_improve += 1
            if epochs_no_improve >= patience:  # 5번 연속 개선 없으면 중단
                logger.info("Early stopping!")
                break
    
    # [6] 학습 완료 후 confusion matrix 생성
    generate_confusion_matrix(val_labels, val_preds, class_names, save_path)
    
    return {"best_val_accuracy": best_val_acc, "val_f1": f1_score(...), ...}
```

**`optimizer_state_dict`도 저장하는 이유는?**
> 학습을 이어서 재개(resume)할 수 있습니다. Adam 같은 adaptive optimizer는 내부에 각 파라미터별 momentum 값을 갖고 있습니다. 이것 없이 resume하면 처음부터 다시 수렴해야 합니다.

**`CosineAnnealingLR`을 쓰는 이유는?**
> 고정 lr보다 마지막에 lr이 낮아져 fine한 수렴이 가능합니다. `T_max=epochs`로 설정하면 전체 학습 기간 동안 1번 코사인 사이클을 돕니다.

---

## 보완 3: 설계 의도 ("왜 이렇게 설계했는가")

---

### 왜 TTA(Test Time Augmentation)를 쓰는가?

**상황**: 사용자가 잎 사진을 찍을 때 카메라 방향이 제각각입니다.

```
학습 이미지: 대부분 정방향
사용자 사진: 90도 기울어진 것, 역광인 것, 클로즈업인 것 등
```

**TTA 없이 추론**
```python
output = model(tensor)
# 기울어진 사진 → 학습 분포와 달라 정확도 하락
```

**TTA 적용 (3가지 변환 평균)**
```python
augmentations = [원본, 좌우반전, 밝기×1.3]
probs = [softmax(model(t)) for t in augmentations]
avg_prob = mean(probs)  # 3가지 관점의 평균
```

> 단순하지만 실제로 회전/조명 변화가 있는 이미지에서 10~15% 정확도 개선 효과가 있습니다.
> 추론 시간은 3배 늘지만 (RTX 5070에서 약 50ms → 150ms), 정확도 trade-off가 유리합니다.

---

### 왜 care_log를 JSON이 아닌 JSONL로 저장하는가?

**JSON으로 저장했다면**
```python
# 기존 파일 전체를 읽고 → 추가 → 전체를 다시 씀
logs = json.loads(file.read_text())
logs.append(new_entry)
file.write_text(json.dumps(logs))  # 파일 전체 재작성
```
> 케어 기록이 1000개가 되면 버튼 한 번 누를 때마다 1000개를 읽고 씁니다.

**JSONL로 저장 (현재)**
```python
# 파일 끝에 한 줄만 추가 (append 모드)
with open(file, "a", encoding="utf-8") as f:
    f.write(json.dumps(entry) + "\n")
```
> 기존 데이터를 읽지 않고 새 줄만 추가합니다. 기록이 10만 개여도 동일한 속도.

---

### 왜 DiagnosisPipeline을 싱글턴으로 관리하는가?

```python
# routes/diagnose.py
_pipeline: DiagnosisPipeline | None = None

def _get_pipeline() -> DiagnosisPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = DiagnosisPipeline()  # 첫 요청 시만 생성
    return _pipeline
```

**싱글턴 없이 매 요청마다 생성했다면?**

| 모델 | 로드 시간 (RTX 5070 기준) |
|------|--------------------------|
| EfficientNet-B3 | ~1초 |
| SAM ViT-B | ~3초 |
| Species Model | ~1초 |
| **합계** | **~5초/요청** |

> 첫 요청만 5초 걸리고, 이후 요청은 즉시 처리됩니다.

---

### 왜 CLAHE를 추론(inference) 시에도 적용하는가?

**학습 시**: CLAHE 전처리된 이미지로 학습
**추론 시**: CLAHE 없이 원본 이미지 입력 → 분포 불일치 → 정확도 저하

> 학습과 추론의 전처리 파이프라인은 반드시 동일해야 합니다. 학습할 때 CLAHE를 썼으면 추론 때도 써야 합니다. 이를 "train-test consistency"라고 합니다.

---

### 왜 종-질병 블랙리스트 방식인가?

**모든 조합을 화이트리스트로 만든다면?**
> 47종 × 14질병 = 658가지 조합을 전부 정의해야 합니다. 유지 보수 불가능.

**블랙리스트 방식 (현재)**
> "이 종에 절대 발생 안 하는 질병" 목록만 관리합니다.
> 선인장에 녹병 불가능, 몬스테라에 황룡병 불가능 — 이런 것만 명시합니다.
> 나머지는 모두 가능한 것으로 간주합니다.

---

### 왜 second_model.pth가 있을 때만 앙상블인가?

```python
def _ensure_disease(self):
    best_path = DISEASE_MODEL_DIR / "best_model.pth"
    if best_path.exists():
        self._disease_models.append(load(best_path))
    
    second_path = DISEASE_MODEL_DIR / "second_model.pth"
    if second_path.exists():
        self._disease_models.append(load(second_path))   # 있으면 앙상블
    # 없으면 단일 모델로 동작
```

> `second_model.pth`는 EfficientNet vs ConvNeXt 비교 실험에서 2등 모델이 자동 복사됩니다.
> 앙상블은 항상 더 좋지만, 메모리를 2배 사용합니다. 파일 존재 여부로 메모리-성능 trade-off를 사용자가 선택하게 합니다.

---

### 왜 케어 로그를 FastAPI와 Streamlit 양쪽에서 직접 관리하는가?

```
Streamlit app.py     → data/care_log.jsonl 직접 읽기/쓰기 (파일 I/O)
FastAPI routes/plants.py → data/care_log.jsonl 직접 읽기/쓰기 (파일 I/O)
```

**API를 통해서만 접근하게 했다면?**
> `POST /api/care-log` 엔드포인트 → 추가 HTTP 요청 → 네트워크 지연
> 버튼 클릭 → 요청 → 응답 → `st.rerun()` 의 왕복 시간

**직접 파일 I/O (현재)**
> Streamlit에서 버튼 클릭 → 즉시 파일에 기록 → `st.rerun()`
> FastAPI는 패턴 분석(`/api/pattern`) 같이 LLM 호출이 필요한 경우에만 사용

> **주의**: 프로덕션 환경(서버 배포)에서는 이 방식이 위험합니다. 여러 서버 인스턴스가 같은 파일을 동시에 쓰면 충돌합니다. 이 프로젝트는 로컬 1인 사용을 전제로 합니다.

---

## 보완 4: 도전 과제별 검증 방법

---

### Stage 1 — 설정 관리 검증

```python
# 이렇게 실행해보세요
python -c "
from src.config import (
    PROJECT_ROOT, MODELS_DIR, DATA_DIR, 
    OLLAMA_BASE_URL, OLLAMA_MODEL, get_device, set_seed
)
print('PROJECT_ROOT:', PROJECT_ROOT)
print('MODELS_DIR exists:', MODELS_DIR.exists())
print('OLLAMA_MODEL:', OLLAMA_MODEL)
print('device:', get_device())
set_seed()
print('seed: OK')
"
```

**예상 출력**
```
PROJECT_ROOT: C:\plantcare
MODELS_DIR exists: True
OLLAMA_MODEL: qwen2.5:7b
device: cuda  (GPU 있으면) 또는 cpu
seed: OK
```

**이게 나오면 맞습니다**: `PROJECT_ROOT`가 프로젝트 루트를 가리키고, `MODELS_DIR`가 존재

---

### Stage 2 — CLAHE 전처리 검증

```python
import cv2
import numpy as np
from src.data.preprocess import apply_clahe

# 밝기 불균일한 테스트 이미지 생성
test_img = np.zeros((224, 224, 3), dtype=np.uint8)
test_img[:112, :, :] = 50   # 위쪽 어두움
test_img[112:, :, :] = 200  # 아래쪽 밝음

result = apply_clahe(test_img)

# 검증: 위/아래 밝기 차이가 줄어들었는지
top_brightness = result[:112].mean()
bottom_brightness = result[112:].mean()
diff_before = abs(50 - 200)       # 150
diff_after = abs(top_brightness - bottom_brightness)

print(f"밝기 차이: {diff_before:.0f} → {diff_after:.0f}")
assert diff_after < diff_before, "CLAHE가 효과 없음"
print("OK: CLAHE가 밝기 차이를 줄였습니다")
```

**예상 출력**
```
밝기 차이: 150 → 40~60  (구체적인 값은 달라도 됨, 줄어들면 OK)
OK: CLAHE가 밝기 차이를 줄였습니다
```

---

### Stage 3 — 모델 정의 검증

```python
from src.models.disease_classifier import create_efficientnet_b3, get_parameter_groups

model = create_efficientnet_b3(num_classes=14, pretrained=False)

# 1. 출력 차원 확인
import torch
dummy = torch.randn(2, 3, 224, 224)   # 배치 2개
output = model(dummy)
assert output.shape == (2, 14), f"예상 (2, 14), 실제 {output.shape}"

# 2. 차등 학습률 그룹 확인
groups = get_parameter_groups(model, "efficientnet_b3")
assert len(groups) == 2
assert groups[0]["lr"] == 1e-5   # backbone
assert groups[1]["lr"] == 1e-3   # fc
print("OK: 모델 정의 및 차등 lr 파라미터 그룹 정상")

# 3. 체크포인트 저장/로드 확인
torch.save({
    "model_state_dict": model.state_dict(),
    "architecture": "efficientnet_b3",
    "class_to_idx": {"Healthy": 0, "Rust": 1},  # 예시
    "val_accuracy": 0.0,
    "epoch": 0,
}, "/tmp/test_ckpt.pth")

ckpt = torch.load("/tmp/test_ckpt.pth", weights_only=True)
assert "architecture" in ckpt
assert "class_to_idx" in ckpt
print("OK: 체크포인트 저장/로드 정상")
```

**예상 출력**
```
OK: 모델 정의 및 차등 lr 파라미터 그룹 정상
OK: 체크포인트 저장/로드 정상
```

---

### Stage 4 — LLM 폴백 검증

```python
import os
from src.inference.llm import _call_llm

# 테스트 1: Ollama 미실행 시에도 앱이 죽지 않는지
# (Ollama가 실제로 꺼져 있어야 함)
result = _call_llm("테스트 프롬프트")
# 빈 문자열이 나와야 함 (오류 없이)
print(f"결과 타입: {type(result)}")  # <class 'str'>
print(f"빈 문자열인가: {result == ''}")  # True (Ollama 꺼져 있을 때)

# 테스트 2: generate_care_guide 폴백 확인
from src.inference.llm import generate_care_guide, FALLBACK_GUIDE

result = generate_care_guide(
    species_name="Monstera",
    disease_korean_name="흰가루병",
    confidence=0.87,
    lesion_ratio=0.23,
    severity="중기",
    plant_nickname="마리",
)
# Ollama 꺼져 있어도 FALLBACK_GUIDE가 반환되어야 함
assert len(result) > 0, "결과가 비어있음"
print("OK: LLM 실패 시 폴백 정상 작동")
```

**예상 출력 (Ollama 꺼진 상태)**
```
결과 타입: <class 'str'>
빈 문자열인가: True
OK: LLM 실패 시 폴백 정상 작동
```

---

### Stage 5 — FastAPI 엔드포인트 검증

서버 실행 후 curl 또는 Python으로 확인합니다.

```bash
# 서버 실행
uvicorn src.api.main:app --reload --port 8000

# 별도 터미널에서 헬스체크
curl http://localhost:8000/health
# 예상 출력: {"status":"ok"}
```

```python
import requests

# /diagnose 엔드포인트 테스트
with open("테스트이미지.jpeg", "rb") as f:
    resp = requests.post(
        "http://localhost:8000/diagnose",
        files={"file": ("test.jpg", f, "image/jpeg")},
        data={"nickname": "마리"},
    )

assert resp.status_code == 200, f"상태 코드: {resp.status_code}"
data = resp.json()

# 필수 키 확인
assert "species" in data
assert "disease" in data
assert "lesion" in data
assert "care_guide" in data
assert "boonz" in data
assert "processing_time_ms" in data

print(f"종: {data['species']['name']}")
print(f"병명: {data['disease']['korean']}")
print(f"병변: {data['lesion']['ratio']:.1%}")
print(f"분즈 mood: {data['boonz']['mood']}")
print("OK: /diagnose 엔드포인트 정상")
```

**예상 출력**
```
종: Monstera Deliciosa  (이미지에 따라 다름)
병명: 흰가루병          (이미지에 따라 다름)
병변: 23.4%
분즈 mood: worried
OK: /diagnose 엔드포인트 정상
```

---

### Stage 6 — Streamlit 세션 상태 검증

```python
# 이건 코드로 테스트하기 어렵습니다 — 브라우저에서 직접 확인하세요

# 체크리스트:
# □ Tab1에서 사진 업로드 후 진단이 나오는가?
# □ 진단 후 Tab3(약제)으로 이동하면 "뭐 사왔어? 보여줘" 메시지가 나오는가?
#   (진단 전 Tab3이면 "먼저 사진을 찍어줘" 메시지)
# □ Tab4에서 케어 버튼 클릭 후 이력에 기록이 추가되는가?
# □ 식물 별명 없이 실행하면 온보딩 화면이 나오는가?
# □ 앱을 새로고침해도 plants.json에 저장된 식물 정보가 유지되는가?
```

---

## 보완 5: 자주 막히는 지점과 해결책

---

### 막히는 지점 1: SAM 체크포인트가 없을 때

```
FileNotFoundError: models/sam/sam_vit_b_01ec64.pth
```

**해결**: `src/inference/diagnose.py`의 `download_sam_checkpoint()`가 자동 다운로드합니다. 약 375MB이므로 처음 실행 시 시간이 걸립니다.

```python
from src.inference.diagnose import download_sam_checkpoint
download_sam_checkpoint()  # 직접 호출 가능
```

---

### 막히는 지점 2: EasyOCR 첫 실행 시 느림

```
Downloading detection model...  (약 30초)
```

**이유**: EasyOCR은 첫 호출 시 모델을 다운로드합니다. 이후 캐시됩니다.
`_get_reader()` 싱글턴이 로드 완료 후 재사용하므로 두 번째 호출부터 빠릅니다.

---

### 막히는 지점 3: Windows에서 DataLoader num_workers 오류

```
RuntimeError: An attempt has been made to start a new process before the current process
```

**원인**: Windows에서 `num_workers > 0`이면 multiprocessing 문제 발생.

**해결**: `create_dataloaders(splits_dir, num_workers=0)`으로 설정. `src/config.py`의 `DATALOADER_NUM_WORKERS = 4`가 있지만 Windows 환경에서는 0으로 오버라이드 필요.

---

### 막히는 지점 4: TTS에서 소리가 나오지 않음

```
Qwen3-TTS 로드 실패, 폴백 사용
ElevenLabs API 키 없음
gTTS 완료: audio/guide_xxxx.mp3
```

**이유**: Qwen3-TTS 로드 실패 → ElevenLabs 키 없음 → gTTS로 폴백. 정상적인 동작입니다.
Streamlit의 `st.audio(audio_url)` — `audio_url`은 `/audio/guide_xxxx.mp3` 형식이고 FastAPI의 StaticFiles로 서빙됩니다. `http://localhost:8000/audio/guide_xxxx.mp3`로 직접 접근해서 파일이 있는지 확인하세요.

---

### 막히는 지점 5: 분즈 메시지에 중국어가 섞임

```
分즈: 지금 상태를 보니...
```

**원인**: Ollama의 qwen2.5 모델이 중국어로 응답하는 경향이 있습니다.

**해결**: `src/inference/llm.py`의 `BOONZ_PERSONA` 첫 줄에 이미 강제 규칙이 있습니다.
```python
BOONZ_PERSONA = """[필수 규칙] 반드시 한국어로만 답해. 중국어(한자), 영어, 일본어 한 글자도 쓰지 마."""
```
그래도 나오면 `system` 파라미터에도 같은 규칙 추가:
```python
"system": "반드시 한국어로만. 중국어 절대 금지. 반말로. 짧게."
```

---

## 요약: 두 문서의 관계

| 내용 | 파일 |
|------|------|
| 기술 스택 Why + 선수 지식 | `reverse_engineering_guide.md` |
| 학습 단계 (도전 과제 형식) | `reverse_engineering_guide.md` |
| 코드 해설 A/B/C | `reverse_engineering_guide.md` |
| 전체 아키텍처 맵 + 의존 관계 | `reverse_engineering_guide.md` |
| 구현 순서 로드맵 | `reverse_engineering_guide.md` |
| 파일별 전체 코드 + 섹션 주석 | `reverse_engineering_guide.md` |
| **학습자 수준별 진입점 (3경로)** | **이 파일** |
| **코드 해설 D/E/F (SAM, LLM, 학습루프)** | **이 파일** |
| **설계 의도 (왜 이렇게 만들었나)** | **이 파일** |
| **도전 과제별 검증 방법 + 예상 출력** | **이 파일** |
| **자주 막히는 지점 5가지** | **이 파일** |
