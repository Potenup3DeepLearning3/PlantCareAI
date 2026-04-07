# PlantCare AI — Phase 검증 결과 (2026-04-07 GUIDE_master_v2.md 재구현)

## GUIDE_master_v2.md Phase 결과

| Phase | 내용 | 상태 | 비고 |
|-------|------|------|------|
| 1 | 데이터 세팅 (DB) | ✅ | diseases 12종 + care_tips 34건. init_db.py 정상 실행 |
| 2 | LLM 연동 | ✅ | MARI_PERSONA + BOONZ_PERSONA(초월자) 추가. answer_care_question_mari_from_db() 추가 |
| 3 | MCP Client | ✅ | detail→source 컬럼명 버그 수정. get_tips_for_question() 정상 동작 |
| 4 | CLIP 폴백 | ✅ | clip_conditions.json (UC Davis IPM 15개) 연동. describe_plant_state() tuple 반환으로 변경 |
| 5 | Streamlit 4탭 | ✅ | 3탭(홈/진단/이력) → 4탭(🏠홈/📷진단/📔일기/🌱성장) |
| 6 | 관계 성장 | ✅ | calculate_relationship() 마리 톤 메시지로 업데이트 |
| 7 | 디자인 | ✅ | 모카 브라운 유지 (#8B7355). mari()/boonz() 컴포넌트 분리 |
| 8 | 목업 비교 | ✅ | mockup_v3/ 4장 참조. 4탭 네비 + 말풍선 구조 일치 |

## 핵심 변경사항 (v1 → v2)

### 화자 구조
- 탭1 홈: 마리 직접 말함 (친한 동생, 1인칭). `mari()` 컴포넌트
- 탭2 진단: 분즈 🍄 (초월자). `boonz()` 컴포넌트 (🍄 아바타 고정)
- 탭3 일기: 마리 (회복 여정 + 타임라인 + 각 기록에 마리 코멘트)
- 탭4 성장: 마리 (리포트 + 🪞 마리가 본 너 + 관계 여정 + 마무리)

### CARE_RESPONSES 변경
- 이전: "마리한테 전해놨어! 물 받아서 좋아하겠다"
- 이후: "아 시원하다. 고마워" (마리 직접)

### 챗봇 분리
- 탭1 챗봇: persona=mari → answer_care_question_mari_from_db() (친한 동생 톤)
- 탭2 챗봇: persona=boonz → respond_to_voice() (초월자 톤)

### MILESTONES 업데이트
- "첫 기록이다! 앞으로 잘 부탁해" (마리 직접)
- "벌써 5번째. 너 꽤 꾸준한 거 알아?" 등

### CLIP 업데이트
- clip_conditions.json 기반 (UC Davis IPM 출처, 15개 조건)
- describe_plant_state() → (description, details) tuple 반환
- details에 symptoms, treatment, source 포함

## 수정 파일 목록
- `src/frontend/app.py` — 4탭 전체 재작성
- `src/inference/llm.py` — MARI_PERSONA, answer_care_question_mari_from_db(), _call_llm_with_persona()
- `src/api/routes/voice.py` — persona 파라미터 추가
- `src/inference/clip_analyzer.py` — clip_conditions.json 연동
- `src/mcp_client.py` — detail→source 버그 수정

## 테스트 체크리스트

### 탭1 홈
- [x] 마리 동적 인사 (시간별/공백별) — get_mari_greeting 로직 구현
- [x] 식물 카드 + 관계 단계 (🌱→🌿→🪴→🌳)
- [x] 통계 카드 (함께한 날/연속 돌봄/병변 변화)
- [x] 원터치 버튼 7개 → 마리 직접 응답 ("아 시원하다. 고마워")
- [x] 넛지 (3번 중 1번 랜덤) — "근데 너 오늘 물 마셨어?"
- [x] 이정표 — 마리 직접 ("첫 기록이다!", "벌써 5번째" 등)
- [x] 마리 챗봇 → persona=mari API 호출

### 탭2 진단
- [x] 사진 업로드 → 분석하기 버튼
- [x] 진단 결과 카드 (병명 + 신뢰도 + 병변%)
- [x] 분즈 🍄 한마디 (초기/중기/후기별 메시지)
- [x] 케어 가이드 버튼 + 출처 표시
- [x] CLIP 폴백 (신뢰도 <70%) — clip_conditions.json 기반
- [x] 분즈 챗봇 → persona=boonz API 호출

### 탭3 일기
- [x] 회복 여정 🥀→🌳 (진단 기록 기반)
- [x] 마리 한마디 (회복률에 따라 분기)
- [x] 돌봄 일기 타임라인 (날짜 역순)
- [x] 각 기록에 마리 코멘트 (MARI_LOG_COMMENTS)

### 탭4 성장
- [x] 돌봄 리포트 (총 기록/연속 돌봄/병변 감소)
- [x] 돌봄 유형 — 마리 톤 (CARE_TYPES_MARI)
- [x] 잘하고 있는 것 + 한 가지 팁
- [x] 🪞 마리가 본 너 (접속 패턴 분석)
- [x] 관계 성장 여정 (수직 타임라인)
- [x] 마리 마무리 한마디 (days/total_logs 기반)
- [x] 분즈 패턴 분석 버튼

---

# (이전 기록 — GUIDE_master.md v1)

# PlantCare AI — Phase 검증 결과 (2026-04-07 재검증)

## GUIDE_master.md Phase 1~8 완료 현황

| Phase | 내용 | 상태 | 비고 |
|-------|------|------|------|
| 1 | 서버 기동 + 모델 로드 | ✅ | FastAPI:8000, Streamlit:8501, /diagnose 정상 응답 |
| 2 | 자기돌봄 미러링 7개 | ✅ | get_streak/last_care/boonz_mood 등 모두 구현 |
| 3 | 관계도 calculate_relationship() | ✅ | 함수 추출 완료, score/level/next_milestone 반환 |
| 4 | MCP/DB 연동 | ✅ | plant_care.db diseases:12 care_tips:34 행 확인 |
| 5 | CLIP 폴백 | ✅ | confidence<0.7 시 자동 전환 구현됨 |
| 6 | 이력 탭 | ✅ | 진단이력/타임라인/케어로그 차트 구현 |
| 7 | LLM OpenAI→Ollama | ✅ | gpt-4o-mini 우선, qwen2.5:7b 폴백 |
| 8 | 모카 브라운 디자인 | ✅ | #3B6D11→#8B7355 전체 교체 (24곳) |

## 핵심 수정 내역 (2026-04-07)
- config.py: MODELS_DIR = PROJECT_ROOT / "models" (임태나/models/ 위치로 수정)
- app.py: calculate_relationship() 함수 추출 (인라인 → 독립 함수)
- app.py: 초록 색상 → 모카 브라운 전체 교체
  - #3B6D11 → #8B7355 (primary)
  - #EAF3DE → #E8DDD0 (light bg)
  - #2B5A1D → #7A6347 (hover)
  - #97C459 → #A89070 (secondary)
  - #F0EDE6 → #EDE5D8 (segmented control bg)

---

# UI 목업 매칭 결과 (2026-04-06)

## 실행 환경
- 프론트: C:/PlantCareAI/임태나/src/frontend/app.py → localhost:8501
- 백엔드: FastAPI → localhost:8000
- 시뮬레이션: 마리 30일치 (병변 15%→2% 완화)

---

## GUIDE.md 단계 완료 현황

| # | 수정 | 상태 | 비고 |
|---|------|------|------|
| 1 | 탭1 원터치 케어 | ✅ | 진단 후 7개 케어 버튼 (care_grid) |
| 2 | 12클래스 DISEASE_KOREAN | ✅ | 12개 매핑 완료 |
| 3 | API URL | ✅ | /consult/text Form 방식 |
| 4 | 탭3 안내 | ✅ | 탭 3개로 재편, 불필요 탭 삭제 |
| 5 | 동적 메시지 | ✅ | 시간대별 + 공백별 분기 |
| 6 | 관계 성장 단계 | ✅ | 🌱→🌿→🪴→🌳 |

---

## selfcare-direction.md 반영 현황

| 항목 | 상태 | 구현 내용 |
|------|------|----------|
| 원터치 셀프케어 넛지 | ✅ | SELFCARE_NUDGES + get_care_response() (3번 중 1번 랜덤) |
| 돌봄 리포트 "마리가 본 너" | ✅ | analyze_user_pattern() + 단일 HTML 블록으로 렌더 |
| 공백 메시지 나 중심 | ✅ | "이런 시간이 너한테 필요한 거 아닐까?" |
| 이정표 나의 성장 | ✅ | "10번 꾸준히 한 거야. 쉬운 거 아닌데" |
| Day 1 분즈 안내 | ✅ | 첫 기록 전 "오늘은 😊 그냥봄 해줘" 카드 |
| 분즈 오프너 5가지 | ✅ | OPENERS + get_opener() 가중치 랜덤 |

---

## 주요 CSS/레이아웃 수정 (Streamlit 1.56 버그)

| 항목 | 수정 내용 |
|------|----------|
| 케어 그리드 수직 스택 | `stHorizontalBlock { flex-direction:row!important }` |
| segmented_control 전체너비 | `stButtonGroup>div { max-width:none!important; width:0!important }` |
| "이야기" 텍스트 잘림 | 서브탭 4개→3개 (비교 제거), overflow:visible |

---

## 화면별 최종 상태

### 홈 탭
- `days >= 8`: "마리와 함께한 지 벌써 30일째야." 타이틀
- `days <= 7`: 시간대별 동적 타이틀
- 공백 메시지 나 중심 (selfcare-direction 반영)
- Day 1 넛지 카드 (total_logs==0일 때)
- 통계 카드 (days>=7, 부호 수정: 병변 감소는 -N%)
- 연속 돌봄: 어제까지 연속이면 streak 유지

### 진단 탭
- 원본/SAM 모드 선택 (전체너비 세그먼트)
- 진단 결과 카드 + 분즈 말풍선 + 케어 가이드 버튼
- 진단 후 원터치 케어 그리드

### 이력 탭 — 케어일기
- 케어 그리드 4열 + 행동 빈도 바 + 회복 타임라인 + 돌봄 일기

### 이력 탭 — 리포트
- 돌봄 유형 뱃지 (꾸준한 관찰형/섬세한 케어형/데이터 수집형/동행형)
- "마리가 본 너" 섹션 (접속 시간대/요일 패턴 분석)
- LLM 패턴 분석 버튼
- 분즈 오프너 가중치 랜덤 (5가지 변형)

### 이력 탭 — 타임라인
- 수직 타임라인: 새로운 만남 → 아픈 날 → 함께 이겨내기 → 알아가는 중 → 거의 회복!
- 마무리 인용구 카드

---

## 시뮬레이션 데이터
- 마리: 30일치, 병변 15%→12%→8%→5%→2% (후기 마름병)
- 케어 로그 38개, 연속 돌봄 11일
- data/plants.json + data/care_log.jsonl

---

## 스크린샷

| 파일 | 설명 |
|------|------|
| screenshots/v2_home.png | 홈 탭 30일 마리 최종 |
| screenshots/v2_report.png | 리포트 탭 마리 최종 |
| screenshots/final_mari_timeline.png | 타임라인 마리 최종 |
| screenshots/final_hist_final.png | 이력 케어일기 최종 |
