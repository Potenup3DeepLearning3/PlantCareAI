# Boonz 10일 스프린트 v4

## v3 → v4 변경사항
- 식물 등록 기능 추가 (별명, 종 자동 연동)
- 원터치 케어 로그 추가 (💧💊☀️ 태그 버튼)
- 통합 타임라인 (진단 + 케어 로그 합산)
- 돌봄 패턴 분석 추가 (Ollama 로그 분석)
- 분즈 캐릭터 PNG + CSS 애니메이션
- 분즈 메시지: 3자 대화 구조 ("{nickname}한테 물어봤는데")
- 딥포레스트 + 라임 디자인 시스템
- LLM 프롬프트 v2 (분즈 페르소나, 5종)

---

## Day 1~2: 환경 + 데이터 (변경 없음)
- Step 1: config.py + 폴더 구조 + .env + .gitignore
- Step 2: PlantVillage + House Plant Species + Kaggle 다운로드
- Step 3: 38클래스 → 7~8클래스 재분류

## Day 3~4: 전처리 + 학습 (변경 없음)
- Step 4: CLAHE(clipLimit=3.0) + PlantDataset + 증강 강화
- Step 5: EfficientNet-B3 / ConvNeXt-Tiny 모델 정의
- Step 6: 모델 학습 + 비교 실험 + PlantDoc 검증

## Day 5~6: 추론 모듈 (변경 없음 + 프롬프트 v2)
- Step 7: SAM 포인트 프롬프트 + 오버레이 라임색(204,255,0,100)
- Step 8: OCR(EasyOCR) + STT(Whisper large-v3) + TTS(gTTS)
- Step 9: Ollama 연동 + 프롬프트 v2 (분즈 페르소나, 5종, 별명 연동)

## Day 7: FastAPI + Streamlit 기본 (업데이트)
- Step 10: FastAPI 엔드포인트
  - 기존 3개: /diagnose, /consult, /medicine
  - 추가 4개: /api/plants, /api/care-log, /api/timeline/{nickname}, /api/pattern/{nickname}
  - 모든 응답에 boonz: {mood, message} 필드 포함
- Step 11-1: 딥포레스트+라임 전역 CSS (메인+사이드바+모든 컴포넌트)
- Step 11-2: 분즈 캐릭터 시스템 (animated_boonz 함수, 애니메이션)

## Day 8: Streamlit 기능 구현 (신규)
- Step 11-3: 식물 등록 (별명 → plants.json, 온보딩 플로우)
- Step 11-4: 탭 1~3 분즈 메시지 + 별명 연동 + 3자 대화
- Step 11-5: 원터치 케어 로그 (7개 태그 버튼 → care_log.jsonl)
- Step 11-6: 통합 타임라인 (진단+케어 합산 + Plotly 추세선)
- Step 11-7: 돌봄 패턴 분석 (Ollama 로그 분석, 10건 이상 시)

## Day 9: 데이터 보강 + 정확도 개선
- Step 12: Google 스크래핑 (icrawler, ~2000장)
- CLIP 유사도 필터링
- 파인튜닝 + PlantDoc 재검증
- TTA 적용 (원본+좌우반전+밝기변화 평균)
- 목표: 58% → 70%+

## Day 10: 통합 테스트 + 배포
- Step 13: E2E 시나리오 테스트 5개
  1. 사진 → 진단 → 분즈 메시지 → TTS
  2. 음성 → STT → LLM → TTS
  3. 약제 라벨 → OCR → 적합성
  4. 원터치 로그 → 타임라인 → Plotly 차트
  5. 패턴 분석 → 분즈 말풍선
- git init → .gitignore → 첫 커밋 → GitHub push
- README.md (설치/실행/스크린샷)
