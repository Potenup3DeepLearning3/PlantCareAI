# 코딩 순서 v2

## Step 1~8: 변경 없음 (완료)
## Step 9: src/inference/llm.py (프롬프트 v2 반영 필요)
## Step 10: src/api/main.py (엔드포인트 4개 추가 필요)

---

## Step 9 업데이트: llm.py 프롬프트 v2

- "식물 건강 전문가" → "분즈" 페르소나
- 존댓말 → 반말
- 프롬프트 5종: care_guide, medicine, consult, pattern, greeting
- get_prompt(prompt_type, **kwargs) 함수
- plant_nickname 파라미터 (별명 없으면 종 이름 사용)
- recent_care_log 파라미터 (care_log.jsonl 최근 10건)
- 3자 대화: "{nickname}한테 물어봤는데", "{nickname}가 그러는데"
- 확인: 5종 프롬프트 각각 Ollama 테스트, 반말 톤 확인

## Step 10 업데이트: main.py 엔드포인트 추가

기존 3개 유지:
- POST /diagnose
- POST /consult (→ /consult/voice, /consult/text로 분리)
- POST /medicine

추가 4개:
- POST /api/plants (식물 등록)
- POST /api/care-log (원터치 케어 로그)
- GET /api/timeline/{nickname} (통합 타임라인)
- GET /api/pattern/{nickname} (돌봄 패턴 분석)

모든 응답에 boonz: {mood, message} 필드 포함.
nickname 파라미터 추가 (기존 엔드포인트에도).

---

## Step 11: src/frontend/app.py (대폭 업데이트)

### 실행 순서: 반드시 11-1부터 순서대로. 하나 끝나면 확인하고 다음.

### 11-1. 전역 CSS
- st.set_page_config 바로 다음에 삽입
- 딥포레스트+라임 전체 CSS (!important 필수)
- 메인 영역 + 사이드바 + 모든 컴포넌트
- 분즈 CSS 애니메이션 (float, shake, bounce)
- 확인: 앱 열면 어두운 배경 + 글자 전부 보임

### 11-2. 분즈 캐릭터 시스템
- animated_boonz(mood, message) 함수
- src/frontend/assets/에서 PNG 로드
- 이미지: width 100px, border-radius 20px, 라임 글로우
- 없으면 이모지 폴백
- 확인: 분즈가 둥둥 떠다니고, 말풍선 렌더링

### 11-3. 식물 등록 + 온보딩
- plants.json CRUD (load/save/delete/update_species)
- 온보딩: 식물 미등록 → 별명 입력만 → 등록 후 탭 표시
- 사이드바: 등록된 식물 목록 + 추가/삭제
- 등록 시 분즈: "초록이? 잘 부탁해" (greeting 프롬프트)
- 확인: 별명 입력 → 탭 4개 표시 → 사이드바에 식물 목록

### 11-4. 탭 1~3 분즈 메시지 + 별명 연동
- 모든 상태에서 animated_boonz 호출
- 별명이 있으면 메시지에 삽입
- 3자 대화 구조: "초록이한테 물어봤는데"
- 탭 1: 업로드 전/로딩/병변% 분기 (0~10/10~25/25+)
- 탭 1: SAM 오버레이 라임색 + 프로그레스 바 (색상 분기)
- 탭 2: 음성/텍스트 입력 전환 + 분즈 답변
- 탭 3: OCR 결과 + 적합성 분즈 메시지
- 에러 시: "앗 나 버그남. 다시 해볼게"
- 확인: 4탭 전부 클릭, 모든 상태에서 분즈 표시

### 11-5. 원터치 케어 로그
- 탭 4에 7개 태그 버튼 (💧☀️✂️💊🪴🍃😊)
- 버튼 스타일: 딥포레스트, hover시 라임 글로우
- data/care_log.jsonl에 1줄 append
- 진단 결과 있으면 disease, lesion 필드도 저장
- 버튼 후 분즈: "{nickname}한테 전해놨어!"
- 확인: 버튼 누르면 jsonl에 기록 추가

### 11-6. 통합 타임라인 + Plotly 차트
- diagnosis_history.jsonl + care_log.jsonl 합쳐서 날짜순
- 타임라인 UI: 📸💧💊😊 이모지 + 날짜 + 병변%
- Plotly 차트: 라임색 라인, 투명 배경, 그리드 #2a3a2a
- 진단 2개 이상이면 차트 표시, 1개 이하면 메시지
- 식물별 필터 (여러 식물일 때)
- 확인: 타임라인에 진단+케어 섞여서 보이고, 차트 렌더링

### 11-7. 돌봄 패턴 분석
- "돌봄 패턴 분석" 버튼
- care_log.jsonl 전체 → Ollama pattern 프롬프트
- 10개 이상: 분석 결과 분즈 말풍선
- 10개 미만: "아직 기록이 {n}개야. 조금만 더 쌓아줘"
- 확인: 10개 이상 기록 후 버튼 → 패턴 분석 결과

## Step 12: 스크래핑 + 파인튜닝 (변경 없음)
## Step 13: 통합 테스트 + Git (변경 없음)

---

## 데이터 파일 구조

```
data/
├── plants.json              ← 등록된 식물 목록
├── care_log.jsonl           ← 원터치 케어 로그
├── diagnosis_history.jsonl  ← 진단 결과 이력
├── raw/                     ← 학습 데이터 (원본)
└── processed/               ← 전처리된 데이터
```
