# 🥦 Boonz — 반려식물 케어 AI

나와 식물 사이, 분즈가 통역해줄게.

잎 사진 한 장으로 종 식별 + 병변 진단 + 맞춤 케어 가이드. 약제 체크, 음성 상담, 케어 기록까지.

---

## 주요 기능

| 탭 | 분즈가 하는 것 | 기술 |
|----|--------------|------|
| 📷 사진 진단 | "초록이한테 물어봤는데, 요즘 컨디션 좋대" | EfficientNet-B3 + SAM + Ollama |
| 🎙️ 음성 상담 | "초록이한테 물어봤어. 물은 주 2회면 돼" | Whisper turbo + Ollama + gTTS |
| 💊 약제 체크 | "초록이한테 보여줬는데, 이거 괜찮대" | EasyOCR + Ollama |
| 📊 케어 이력 | "봐봐, 초록이 점점 좋아지고 있어!" | Plotly + Ollama 패턴 분석 |

---

## 설치

### 요구 사항
- Python 3.12
- CUDA GPU 권장 (RTX 5070 기준)
- [Ollama](https://ollama.com) 설치 및 실행

### 설치 방법

```bash
# 1. 저장소 클론
git clone https://github.com/your-repo/boonz.git
cd boonz

# 2. 가상환경 + 의존성 설치 (uv 사용)
uv sync

# 3. 환경변수 설정
cp .env.example .env
# .env에서 KAGGLE_USERNAME, KAGGLE_KEY, HUGGINGFACE_API 입력

# 4. Ollama 모델 다운로드
ollama pull qwen2.5:7b

# 5. 학습 데이터 + 모델 학습
python -m src.data.download
python -m src.data.remap_labels
python -m src.data.preprocess
python -m src.models.train
```

---

## 실행

터미널 3개에서 각각 실행:

```bash
# 터미널 1: Ollama LLM
ollama serve

# 터미널 2: FastAPI 백엔드
uvicorn src.api.main:app --reload --port 8000

# 터미널 3: Streamlit 프론트엔드
streamlit run src/frontend/app.py
```

브라우저에서 `http://localhost:8501` 접속.

---

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| POST | `/diagnose` | 잎 사진 → 종 + 병변 + 케어 가이드 |
| POST | `/check-medicine` | 약제 라벨 → OCR + 적합성 |
| POST | `/voice-consult` | 음성/텍스트 → LLM 답변 |
| POST | `/api/plants` | 식물 등록 |
| POST | `/api/care-log` | 원터치 케어 로그 |
| GET | `/api/timeline/{nickname}` | 통합 타임라인 |
| GET | `/api/pattern/{nickname}` | 돌봄 패턴 분석 |

Swagger UI: `http://localhost:8000/docs`

---

## 모델 구조

```
7개 AI 모델
├── EfficientNet-B3    병변 유형 9클래스 분류 (val 99.89%)
├── EfficientNet-B3    47종 식물 종 식별 (val 90.46%)
├── SAM ViT-B          병변 세그멘테이션 + 면적 비율
├── EasyOCR            약제 라벨 한국어 성분 추출
├── Whisper turbo      음성 → 텍스트 (한국어)
├── gTTS               텍스트 → 음성
└── Ollama qwen2.5:7b  케어 가이드 + 패턴 분석 생성
```

**실제 환경 정확도 (PlantDoc)**: 목표 70%+

---

## 프로젝트 구조

```
boonz/
├── src/
│   ├── api/            FastAPI 앱 + 라우트
│   ├── data/           데이터 다운로드/전처리/스크래핑
│   ├── frontend/       Streamlit 앱 (app.py)
│   ├── inference/      진단 파이프라인 (diagnose, llm, ocr, stt, tts)
│   └── models/         모델 정의 + 학습 스크립트
├── models/             학습된 체크포인트
├── data/               학습 데이터 (gitignore)
├── docs/               스프린트 문서 + 정확도 리포트
└── tests/              단위 + E2E 테스트
```

---

## 테스트

```bash
# E2E 시나리오 테스트 (모델 없이 실행 가능한 항목 포함)
pytest tests/test_e2e.py -v

# 통합 테스트 (모델 파일 필요)
pytest tests/test_integration.py -v

# 전체
pytest tests/ -v
```

---

## 기술 스택

- **Backend**: FastAPI + Uvicorn
- **Frontend**: Streamlit
- **ML**: PyTorch + torchvision
- **Vision**: EfficientNet-B3, SAM ViT-B, EasyOCR
- **Audio**: Whisper turbo (로컬), gTTS
- **LLM**: Ollama qwen2.5:7b (로컬)
- **환경**: Windows, Python 3.12, uv

---

## 라이선스

MIT
