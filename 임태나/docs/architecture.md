# PlantCare AI 아키텍처 (v3 — 최신)

> 마지막 업데이트: 2026-04-06
> 실제 구현 기준 (병변 12클래스, Whisper turbo, Qwen3-TTS, LLM 이중화, /consult/text 신규)

---

## 1. 전체 시스템 아키텍처

```mermaid
flowchart TB
  subgraph CLIENT["클라이언트 (Streamlit :8501)"]
    T1["탭1: 사진 진단\n이미지 업로드 + 케어 로그"]
    T2["탭2: 음성/텍스트 상담\n마이크 + 채팅 UI"]
    T3["탭3: 약제 체크\n라벨 업로드 + 적합성 판정"]
    T4["탭4: 진단 이력\n타임라인 + 관계 성장"]
  end

  subgraph BACKEND["FastAPI 백엔드 (:8000)"]
    EP1["POST /diagnose"]
    EP2["POST /medicine"]
    EP3["POST /consult/voice"]
    EP4["POST /consult/text"]
    STATIC["/audio/ 정적 파일 서빙"]
  end

  subgraph VISION["비전 레이어"]
    CLH["CLAHE 전처리\n(LAB L채널, clipLimit=2.0)"]
    DIS["EfficientNet-B3\n병변 분류 12클래스\n99.86% val_acc"]
    SPE["EfficientNet-B3\n종 식별 47클래스\n88.15% val_acc"]
    SAM_M["SAM vit_b\n병변 세그멘테이션\n면적 비율 → 심각도"]
    OCR_M["EasyOCR\n약제 라벨 한국어 추출"]
  end

  subgraph AUDIO["음성 레이어"]
    STT_M["Whisper turbo\n한국어 STT (RTX 5070)"]
    TTS_M["Qwen3-TTS sohee\n한국어 TTS\n↓ 폴백: gTTS"]
  end

  subgraph LLM_L["LLM 레이어"]
    GAPI["Google AI Studio\n(우선순위 1)"]
    OLL["Ollama qwen2.5:14b\nlocalhost:11434\n(우선순위 2 / 오프라인)"]
  end

  subgraph STORAGE["데이터 저장"]
    HIST["diagnosis_history.json\n진단 이력 + 케어 로그"]
    NCPMS_D["ncpms_knowledge.json\nNCPMS 병해충 도감"]
    AUDIO_F["audio/*.mp3\n생성된 TTS 파일"]
  end

  T1 -->|"HTTP multipart"| EP1
  T2 -->|"음성 파일"| EP3
  T2 -->|"텍스트 질문"| EP4
  T3 -->|"라벨 이미지"| EP2
  T4 -->|"읽기"| HIST

  EP1 --> CLH --> DIS & SPE & SAM_M
  EP2 --> OCR_M
  EP3 --> STT_M

  DIS & SPE & SAM_M -->|"진단 결과"| GAPI
  OCR_M -->|"성분 정보"| GAPI
  STT_M -->|"텍스트"| GAPI
  NCPMS_D -->|"방제 지식"| GAPI
  GAPI -->|"실패 시"| OLL

  GAPI & OLL -->|"케어 가이드 텍스트"| TTS_M
  TTS_M -->|"mp3 저장"| AUDIO_F
  STATIC -->|"서빙"| AUDIO_F

  EP1 -->|"결과 저장"| HIST
```

---

## 2. 추론 파이프라인 (런타임 상세)

```mermaid
flowchart LR
  subgraph IN["입력"]
    I1["잎 사진\n(.jpg/.png, ≤10MB)"]
    I2["약제 라벨 사진"]
    I3["음성 파일\n(.wav/.mp3/.m4a, ≤60s)"]
    I4["텍스트 질문"]
  end

  subgraph PRE["전처리"]
    PIL_R["PIL 읽기\n(한글 경로 cv2 우회)"]
    CLAHE_P["CLAHE\nLAB L채널 적용\ncv2.createCLAHE\nclipLimit=2.0"]
    RESIZE["224×224 리사이즈\n+ ImageNet 정규화"]
  end

  subgraph INF["추론"]
    SPEC["종 식별\nEfficientNet-B3\n47클래스 → softmax"]
    DISC["병변 분류\nEfficientNet-B3\n12클래스 → softmax"]
    SAM_I["SAM vit_b\n중앙 포인트 프롬프트\n→ binary mask"]
    SEV["심각도 판정\n<10%: 초기\n10-25%: 중기\n>25%: 후기"]
    OCR_I["EasyOCR\nko+en 인식\n→ 성분 리스트"]
    WHI["Whisper turbo\nbeam_size=5\n→ 한국어 텍스트"]
  end

  subgraph SYNTH["LLM 합성"]
    PROMPT["프롬프트 조립\n종+병변+면적+성분\n+음성메모+NCPMS"]
    LLM_C["_call_llm()\nGoogle AI Studio 시도\n→ 실패 시 Ollama 폴백\n→ 둘 다 실패 시 템플릿 반환"]
    BOONZ["분즈 메시지 생성\n면적 0-10%: happy\n면적 10-25%: worried\n면적 25%+: sad"]
  end

  subgraph OUT["출력"]
    RES_J["JSON 응답\nspecies/disease/lesion\n/boonz/care_guide"]
    OVL["SAM 오버레이\n반투명 초록 마스킹\nbase64 인코딩"]
    TTS_O["Qwen3-TTS sohee\n→ audio/*.mp3\n(실패 시 gTTS)"]
  end

  I1 --> PIL_R --> CLAHE_P --> RESIZE
  RESIZE --> SPEC & DISC & SAM_I
  SAM_I --> SEV --> PROMPT
  SPEC & DISC -->|"name + confidence"| PROMPT
  I2 --> OCR_I --> PROMPT
  I3 --> WHI --> PROMPT
  I4 --> PROMPT
  PROMPT --> LLM_C --> BOONZ
  LLM_C --> TTS_O
  BOONZ --> RES_J
  SAM_I --> OVL --> RES_J
  TTS_O --> RES_J
```

---

## 3. API 흐름도

```mermaid
sequenceDiagram
  participant UI as Streamlit UI
  participant API as FastAPI :8000
  participant VIS as 비전 모델
  participant LLM as LLM (GAI/Ollama)
  participant TTS as Qwen3-TTS/gTTS

  Note over UI,TTS: POST /diagnose (탭1)
  UI->>API: multipart/form-data (이미지)
  API->>VIS: CLAHE → 종식별 + 병변분류 + SAM
  VIS-->>API: species, disease(12cls), lesion{ratio, severity, overlay}
  API->>LLM: 프롬프트 (종+병변+면적+NCPMS)
  LLM-->>API: 케어 가이드 텍스트
  API->>TTS: 텍스트 → mp3
  TTS-->>API: audio/guide_xxx.mp3
  API-->>UI: {species, disease, lesion, boonz, care_guide, processing_time_ms}
  UI->>UI: 케어 로그 버튼 7개 표시

  Note over UI,TTS: POST /medicine (탭3)
  UI->>API: 라벨 이미지 + (진단 캐시 참조)
  API->>VIS: EasyOCR → 성분 추출
  API->>LLM: 성분 + 현재 진단 → 적합성 판정
  LLM-->>API: 적합 여부 + 이유
  API-->>UI: {ocr_result, compatibility, current_diagnosis}

  Note over UI,TTS: POST /consult/voice (탭2-음성)
  UI->>API: 음성 파일 (≤60s)
  API->>VIS: Whisper turbo → 텍스트
  API->>LLM: 텍스트 + 진단 컨텍스트
  LLM-->>API: 답변 텍스트
  API->>TTS: 텍스트 → mp3
  API-->>UI: {transcript, response{text, audio_url}, suggested_action}

  Note over UI,TTS: POST /consult/text (탭2-텍스트, 신규)
  UI->>API: {question, nickname, diagnosis_context}
  API->>LLM: 질문 + 컨텍스트
  LLM-->>API: 답변 (반말, 한국어)
  API-->>UI: {response{text, audio_url}, boonz{mood, message}}
```

---

## 4. 모델 학습 파이프라인

```mermaid
flowchart TB
  subgraph DATA_SRC["데이터 소스"]
    PV["PlantVillage\n54,306장 / 38클래스"]
    HPS["House Plant Species\n~8,000장 / 47종"]
    HW["Healthy/Wilted\n904장"]
    GS["Google 스크래핑\n~2,000장 (icrawler)"]
    PD["PlantDoc\n2,598장 (테스트 전용)"]
  end

  subgraph PREP["전처리 공통"]
    RC["38클래스 → 12클래스\n재라벨링"]
    CL2["CLAHE + 224×224\n+ ImageNet 정규화"]
    AUG["학습 증강\nHFlip + Rotate15\n+ ColorJitter"]
    SPLIT["8:1:1 스플릿\ntrain/val/test"]
  end

  subgraph EXP["모델 비교 실험 (Day 1)"]
    EFN["EfficientNet-B3\n12M params"]
    CNX["ConvNeXt-Tiny\n28.6M params"]
    CMP{"비교\nval_acc / 크기 / 속도"}
    WIN["✅ EfficientNet-B3 선택\n99.86% / 40.86MB / 19.76ms"]
  end

  subgraph TRAIN_FLOW["학습 절차"]
    PT["사전학습 (PlantVillage 12클래스)\nEpoch 30 / ES patience=5\nlr=1e-3 (새 층) + 1e-5 (backbone)"]
    FT["파인튜닝 (Day 4)\n스크래핑 데이터 추가\n마지막 fc층 교체"]
    SP_T["종 식별 학습\n(House Plant 47종)\n별도 독립 모델"]
  end

  subgraph ARTIFACT["모델 아티팩트"]
    B_DIS["models/disease/\nefficientnet_b3_disease_type_best.pth\n{model_state_dict, class_to_idx, architecture}"]
    B_SPE["models/species/\nspecies_model_best.pth"]
    SAM_W["models/sam/\nsam_vit_b_01ec64.pth (사전학습 그대로)"]
    LOG["models/disease/training_log.csv\n+ confusion_matrix.png"]
    COMP["models/comparison/\ncomparison_results.json"]
  end

  PV --> RC --> CL2 --> AUG --> SPLIT
  HPS --> CL2
  HW --> CL2
  GS --> CL2

  SPLIT --> EFN & CNX
  EFN & CNX --> CMP --> WIN
  WIN --> PT --> FT
  FT --> B_DIS
  HPS --> SP_T --> B_SPE
  PT --> LOG
  CMP --> COMP

  PD -->|"Day 9 최종 평가"| B_DIS
```

---

## 5. 폴더 구조

```mermaid
graph TD
  ROOT["c:/plantcare/"]
  ROOT --> SRC["src/"]
  ROOT --> MODELS_D["models/"]
  ROOT --> DATA_D["data/"]
  ROOT --> DOCS_D["docs/"]
  ROOT --> ENV[".env"]

  SRC --> S_API["api/\nmain.py · schemas.py\nroutes/"]
  SRC --> S_INFER["inference/\ndiagnose.py\nocr.py · stt.py\ntts.py · llm.py"]
  SRC --> S_MODELS["models/\ndisease_classifier.py\nspecies_classifier.py\ntrain.py"]
  SRC --> S_DATA["data/\ndownload.py · reclassify.py\npreprocess.py · dataset.py\nscrape_images.py"]
  SRC --> S_FRONT["frontend/\napp.py"]
  SRC --> S_CONFIG["config.py"]

  MODELS_D --> M_DIS["disease/\nefficientnet_b3_disease_type_best.pth\ntraining_log.csv"]
  MODELS_D --> M_SPE["species/\nspecies_model_best.pth"]
  MODELS_D --> M_SAM["sam/\nsam_vit_b_01ec64.pth"]
  MODELS_D --> M_CMP["comparison/\ncomparison_results.json"]

  DATA_D --> D_RAW["raw/\nplantvillage/ · house_plant_species/\nhealthy_wilted/ · ncpms_knowledge/"]
  DATA_D --> D_PROC["processed/\ndisease_type/ (12클래스)"]
  DATA_D --> D_SPLIT["splits/\ntrain/ · val/ · test/"]
```

---

## 병변 12클래스 매핑

| 클래스명 | 한국어 |
|---------|--------|
| Bacterial_Spot | 세균성 반점 |
| Early_Blight | 초기 마름병 |
| Greening | 그리닝병 |
| Healthy | 건강 |
| Late_Blight | 후기 마름병 |
| Leaf_Curl | 잎 말림 |
| Leaf_Mold | 잎 곰팡이 |
| Leaf_Spot | 잎 반점 |
| Mosaic_Virus | 모자이크 바이러스 |
| Powdery_Mildew | 흰가루병 |
| Rust | 녹병 |
| Scab_Rot | 딱지병/부패 |
