# Boonz 최종 수정 가이드 (Claude Code 자동 실행용)

이 파일의 수정 사항을 1번부터 순서대로 적용해줘.
각 수정 후 테스트 코드를 실행해서 확인하고, 성공하면 다음으로 넘어가.
실패하면 에러를 분석하고 수정한 뒤 다시 테스트해.
전부 끝나면 결과 요약을 RESULT.md에 저장해.

## 중요 사전 정보

### 체크포인트 로드 패턴
모든 .pth 파일은 체크포인트 전체 저장 구조:
```python
checkpoint = torch.load(path, map_location=device)
# checkpoint.keys() = ['model_state_dict', 'optimizer_state_dict', 'epoch', 'val_accuracy', 'class_to_idx', 'architecture']
model.load_state_dict(checkpoint["model_state_dict"])  # state가 아니라 checkpoint["model_state_dict"]
num_classes = len(checkpoint["class_to_idx"])  # 실제 클래스 수
```

### 실제 모델 정보
- 병변 분류: 12클래스 (7이 아님!), EfficientNet-B3
  - 함수명: create_efficientnet_b3(num_classes=12) — create_model이 아님!
  - 파일: models/disease/efficientnet_b3_disease_type_best.pth
  - 클래스: Bacterial_Spot, Early_Blight, Greening, Healthy, Late_Blight, Leaf_Curl, Leaf_Mold, Leaf_Spot, Mosaic_Virus, Powdery_Mildew, Rust, Scab_Rot
- 종 식별: 47클래스, EfficientNet-B3
  - 함수명: create_species_model(num_classes=47)
  - 파일: models/species/species_model_best.pth
- SAM: vit_b, 파일: models/sam/sam_vit_b_01ec64.pth
- config 변수명: PROJECT_ROOT (PROJECT_DIR 아님), MODELS_DIR, OLLAMA_MODEL

### 한글 경로 주의
cv2.imread는 한글 경로 못 읽음. 반드시 PIL로 읽고 numpy 변환:
```python
from PIL import Image
import numpy as np
img = np.array(Image.open(filepath).convert("RGB"))
```

### TTS 설정
Qwen3-TTS 사용:
```python
from qwen_tts.inference.qwen3_tts_model import Qwen3TTSModel
model = Qwen3TTSModel.from_pretrained("Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice")
audios, sr = model.generate_custom_voice(text=text, speaker="sohee", language="korean")
```
실패 시 gTTS 폴백.

### Whisper 설정
whisper.load_model("turbo") — large-v3이 아니라 turbo

---

## 🔴 P0: 반드시 해야 함 (Day 1)

### 수정 1: 탭1 진단 후 원터치 케어 로그 추가

파일: src/frontend/app.py

탭1의 진단 결과 + 분즈 말풍선 + 케어 가이드 아래에, except 전에 추가:

```python
            st.divider()
            st.markdown(f"**방금 {nickname}한테 뭐 해줬어?**")
            care_cols = st.columns(4)
            care_quick = {
                "💧 물줬음": "water", "☀️ 자리옮김": "move",
                "✂️ 가지치기": "prune", "💊 약줬음": "medicine",
                "🪴 분갈이": "repot", "🍃 잎닦음": "clean",
                "😊 그냥봄": "observe",
            }
            for i, (label, action) in enumerate(care_quick.items()):
                with care_cols[i % 4]:
                    if st.button(label, key=f"t1_{action}", use_container_width=True):
                        save_care_log(nickname, action)
                        boonz("happy", f"{nickname}한테 전해놨어!")
```

테스트: 탭1 사진 업로드 → 진단 결과 아래 7개 버튼 확인

---

### 수정 2: DISEASE_KOREAN 12클래스

파일: src/frontend/app.py + src/api/main.py

두 파일 모두에 이 딕셔너리 적용:
```python
DISEASE_KOREAN = {
    "Bacterial_Spot": "세균성 반점", "Early_Blight": "초기 마름병",
    "Greening": "그리닝병", "Healthy": "건강",
    "Late_Blight": "후기 마름병", "Leaf_Curl": "잎 말림",
    "Leaf_Mold": "잎 곰팡이", "Leaf_Spot": "잎 반점",
    "Mosaic_Virus": "모자이크 바이러스", "Powdery_Mildew": "흰가루병",
    "Rust": "녹병", "Scab_Rot": "딱지병/부패",
}
```

main.py /diagnose 응답에 korean 필드 추가:
```python
"disease": {"name": name, "korean": DISEASE_KOREAN.get(name, name), "confidence": conf}
```

---

### 수정 3: FastAPI URL + /consult/text

파일: src/api/main.py

- /check-medicine → /medicine
- /voice-consult → /consult/voice
- POST /consult/text 추가 (question, nickname, diagnosis_context → Ollama → 답변)
- 모든 응답에 boonz: {mood, message} 포함

분즈 메시지 규칙:
- 병변 0~10%: mood=happy, "{nickname}한테 물어봤는데, 요즘 컨디션 좋대"
- 병변 10~25%: mood=worried, "{nickname}가 좀 힘들다는데? 약 좀 사다줘"
- 병변 25%+: mood=sad, "{nickname}가 많이 아프대... 빨리 도와줘야 할 거 같아"

---

### 수정 4: 탭3 진단 없이 접근 안내

파일: src/frontend/app.py

탭3에서 진단 없이 약제 업로드 시:
boonz("worried", f"약을 보기 전에 {nickname} 사진 먼저 찍어줘")

---

### 수정 A: Whisper turbo

파일: src/inference/stt.py
whisper.load_model("large-v3") → whisper.load_model("turbo")

---

### 수정 B: TTS Qwen3-TTS

파일: src/inference/tts.py 전체 교체

Qwen3-TTS CustomVoice, speaker="sohee", language="korean"
실패 시 gTTS 폴백

---

### 수정 C: LLM 한국어 강제

파일: src/inference/llm.py

모든 프롬프트에 추가: "한국어로만 답해. 영어, 한자 섞지 마. 반말로. 짧게."

---

### 수정 D: 체크포인트 로드

파일: src/inference/ 모델 로드하는 모든 파일

```python
checkpoint = torch.load(path, map_location=device)
if isinstance(checkpoint, dict) and "model_state_dict" in checkpoint:
    model.load_state_dict(checkpoint["model_state_dict"])
else:
    model.load_state_dict(checkpoint)
```

---

### 수정 E: 한글 경로 PIL

파일: src/inference/ 이미지 읽는 모든 파일

cv2.imread → PIL + numpy로 교체

---

## 🟡 P1: 시연 품질 향상 (Day 2)

### 수정 5: 재방문 동적 메시지

파일: src/frontend/app.py

시간별 + 돌봄 공백별 인사 메시지. 고정 문구 교체.

---

### 수정 6: 관계 성장 단계

파일: src/frontend/app.py

식물 카드에 관계 단계(🌱→🌿→🪴→🌳) + 연속 기록 카운트 + 이정표

---

### 수정 7: 채팅 이력

파일: src/frontend/app.py

탭2 텍스트 탭에 session_state 대화 리스트. 유저 말풍선 + 분즈 말풍선 교차 표시.

---

### 수정 8: 단계별 로딩

현재 구조 유지. 시간 부족하면 스킵 가능.

---

### 수정 9: 진단 맥락 참조

파일: src/frontend/app.py + src/api/main.py

탭2에서 session_state.last_diagnosis를 FastAPI에 diagnosis_context로 전달.

---

## 🟢 P2: 있으면 좋음 (Day 3)

### 수정 10: 음성 입력 개선

st.audio_input 시도. 안 되면 file_uploader 유지.

---

### 수정 11: 탭4 레이아웃

순서: 태그 버튼 → 프로그레스 → 타임라인(5개+더보기) → 추세선 → 패턴 분석 → 식물 관리(expander)

---

## 🔵 시연 데이터 (Day 3)

scripts/generate_demo_data.py 생성 및 실행.
마리 30일치 데이터: 병변 15% → 12% → 8% → 5% → 2%

---

## 완료 후 RESULT.md

| # | 수정 | 상태 |
|---|------|------|
| 1 | 탭1 원터치 | |
| 2 | 12클래스 | |
| 3 | API URL | |
| 4 | 탭3 안내 | |
| 5 | 동적 메시지 | |
| 6 | 관계 성장 | |
| 7 | 채팅 이력 | |
| 8 | 단계별 로딩 | |
| 9 | 맥락 참조 | |
| 10 | 음성 개선 | |
| 11 | 탭4 레이아웃 | |
| A | Whisper turbo | |
| B | Qwen3-TTS | |
| C | LLM 한국어 | |
| D | 체크포인트 | |
| E | 한글 경로 | |
| SIM | 시뮬레이션 | |
