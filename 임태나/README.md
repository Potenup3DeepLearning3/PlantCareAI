# 🌱 Boonz — 식물한테 해주는 걸, 너한테도 해줘

> 반려식물 돌봄이 나를 돌보는 시간이 되는 AI 셀프케어 서비스

---

## 프로젝트 소개

Boonz는 반려식물을 돌보는 행위를 통해 사용자 자신을 돌보게 만드는 AI 서비스입니다.

기존 식물 앱은 "3일 후 물 주세요", "후기 마름병입니다"에서 끝납니다.
Boonz는 "물 줬구나. 근데 너는? 오늘 물 마셨어?"라고 물어봅니다.

**AI Transformation:** 같은 기술(비전 AI + LLM)인데, 정보 전달이 아니라 관계를 만드는 데 씁니다.

## 서비스 구조 — 4탭

| 탭 | 화자 | 역할 | 핵심 기능 |
|----|------|------|----------|
| 🏠 홈 | 마리 (친한 동생) | 매일 10초 | 동적 인사 + 원터치 버튼 + 셀프케어 넛지 + 마리 챗봇 |
| 📷 진단 | 분즈 🍄 (초월자) | 가끔 | 사진 진단 + SAM + 케어 가이드(출처 기반) + 분즈 챗봇 |
| 📔 일기 | 마리 | 돌아보기 | 돌봄 타임라인 + 회복 여정 (🥀→🌳) + 마리 코멘트 |
| 🌱 성장 | 마리 | 종합 | 돌봄 리포트 + 유형 분류 + 🪞 마리가 본 너 + 관계 여정 |

---

## 페르소나

### 마리 — 식물이 직접 1인칭 (탭1, 3, 4)

```
톤: 친한 동생. 반말, 짧게, 솔직.
"야 왔네. 오늘 힘들었지?"
"아 시원하다. 고마워"
"근데 너 물 마셨어?"
```

### 분즈 🍄 — 숲속 현자 (탭2)

```
톤: 초월자. 차분하고 여운 있게. 자연의 이치로 설명.
"공기가 멈춘 곳에 곰팡이가 앉는 법이야"
"식물은 원래 나을 줄 알아. 네가 길만 열어주면 돼"
"서두를 필요 없어. 하나만 해. 환기"
---

## 설치

### 요구 사항
- Python 3.12
- CUDA GPU 권장 (RTX 5070 기준)

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

### 비전 AI

| 모델 | 역할 | 정확도 | 크기 |
|------|------|--------|------|
| EfficientNet-B3 (병변) | 12클래스 병변 분류 | 97.9% | 129MB |
| EfficientNet-B3 (종) | 47종 식별 | 88.2% | 130MB |
| SAM vit_b | 세그멘테이션, 병변 면적% | - | 375MB |
| CLIP vit-base-patch32 | 저신뢰(<70%) 폴백, 환경/해충 | - | ~600MB |

### 텍스트 AI

| 모델 | 역할 | 비고 |
|------|------|------|
| OpenAI API (gpt-4o-mini) | LLM 1순위 | 마리 톤 + 분즈 톤 변환 |
| Gemma (로컬) | LLM 2순위 폴백 | 인터넷 끊겼을 때 |

### 데이터 + MCP

| 파일 | 내용 | 출처 |
|------|------|------|
| diseases.json | 12병변 (증상/치료/예방/회복) | Clemson HGIC, RHS, Purdue, Missouri BG |
| care_tips.json | 35케어팁 (8카테고리) | RHS, Clemson HGIC, Missouri BG |
| clip_conditions.json | 15환경/해충 상태 | UC Davis IPM, Connecticut CAES, Penn State Extension |
| plant_care.db | SQLite (init_db.py로 생성) | JSON → DB 로드 |

```
역할 분리:
  EfficientNet: 질병 분류 (출처: Clemson HGIC)
  CLIP: 환경/해충 추론 (출처: UC Davis IPM)
  DB: 정보의 정확성 보장
  LLM: 톤 변환만 (할루시네이션 구조적 차단)
```

### 알고리즘 (AI 아님)

| 알고리즘 | 역할 | 방식 |
|----------|------|------|
| 관계 성장 | 🌱→🌿→🪴→🌳 | 연속성(40%) × 다양성(30%) × 반응성(30%) |
| 돌봄 유형 | 관찰/케어/수집/동행 | 규칙 기반 (observe>40%→관찰형) |
| 접속 패턴 | 🪞 마리가 본 너 | 통계 (시간대/요일/연속일) |

---

## 진단 파이프라인

```
사진 업로드
  → PIL 읽기 (한글 경로 우회) → CLAHE 전처리
  → EfficientNet-B3 병변 분류
     ├── 신뢰도 ≥ 70%  → 병명 + MCP → DB 조회 → 분즈 톤 변환
     └── 신뢰도 < 70%  → CLIP 환경/해충 추론 → 분즈 톤 변환
  + SAM 세그멘테이션 → 병변 면적% → 오버레이 1장
  → 분즈 🍄 케어 가이드 (예방/치료/회복 + 출처)
```

---

## 프로젝트 구조

```
C:\PlantCareAI\임태나\
├── models/
│   ├── disease/efficientnet_b3_disease_type_best.pth  (129MB)
│   ├── species/species_model_best.pth                 (130MB)
│   └── sam/sam_vit_b_01ec64.pth                       (375MB)
├── data/
│   ├── diseases.json          ← 12병변 (Clemson/RHS 출처)
│   ├── care_tips.json         ← 35케어팁 (RHS/Missouri BG 출처)
│   ├── clip_conditions.json   ← 15환경/해충 (UC Davis 출처)
│   ├── plants.json            ← 등록 식물 (런타임)
│   ├── care_log.jsonl         ← 돌봄 기록 (런타임)
│   └── plant_care.db          ← SQLite (init_db.py로 생성)
├── src/
│   ├── frontend/app.py        ← Streamlit 4탭 UI
│   ├── api/main.py            ← FastAPI 서버
│   ├── inference/
│   │   ├── disease.py         ← EfficientNet 병변 분류
│   │   ├── species.py         ← EfficientNet 종 식별
│   │   ├── sam_segmentation.py← SAM 세그멘테이션
│   │   ├── clip_analyzer.py   ← CLIP 폴백
│   │   └── llm.py             ← LLM (OpenAI + Gemma 폴백)
│   └── mcp_client.py          ← MCP → SQLite 조회
├── mcp_server/
│   └── plant_db_server.py     ← MCP Server
├── scripts/
│   ├── init_db.py             ← JSON → SQLite 로드
│   └── generate_demo_data.py  ← 시뮬레이션 데이터 생성
├── docs/
│   └── boonz_tone_guide_v3.md ← 톤 가이드 (마리 + 분즈)
├── mockup_v3/                 ← 목업 PNG 5장
├── GUIDE_master_v2.md         ← 전체 구현 가이드
└── .env                       ← OPENAI_API_KEY
```

---

## 실행 방법

### 1. 데이터 세팅

```bash
cd C:\PlantCareAI\임태나
python scripts/init_db.py              # JSON → DB 생성
python scripts/generate_demo_data.py   # 마리 30일 시뮬레이션
```

### 2. 환경변수

```
# .env
OPENAI_API_KEY=sk-...
```

### 3. 서버 실행

```bash
# 터미널 1: FastAPI
uvicorn src.api.main:app --reload --port 8000

# 터미널 2: Streamlit
streamlit run src/frontend/app.py --server.port 8501
```

### 4. 접속

```
http://localhost:8501
```

---

## 학습 데이터

| 데이터셋 | 규모 | 용도 |
|----------|------|------|
| PlantVillage | 54,306장 (38cls → 12cls 통합) | 병변 분류 모델 학습 |
| House Plant Species | ~8,000장 (47cls) | 종 식별 모델 학습 |
## 테스트

```bash
# E2E 시나리오 테스트 (모델 없이 실행 가능한 항목 포함)
pytest tests/test_e2e.py -v

# 통합 테스트 (모델 파일 필요)
pytest tests/test_integration.py -v

# 전체
pytest tests/ -v
```
